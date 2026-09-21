from __future__ import annotations

import argparse, hashlib, json, os, platform, time
from pathlib import Path
import numpy as np
import pandas as pd

from .aux_tcn import run_aux_tcn
from .data_io import read_table, prepare_panel
from .candidate_manifest import CandidateSpec, build_candidate_manifest
from .diagnostics import write_factor_diagnostics
from .factors import volume_impact_recovery
from .fold_support import fold_support_summary
from .registry import Registry, stable_hash
from .receipts import ResearchSessionReceipt
from .session_clock import dedupe_signals_market_calendar
from .snapshot_features import add_kdj_path_features, add_market_session_id, add_volume_pressure, build_snapshot_features
from .task_spec import H504TaskSpec, label_h504_candidates, market_calendar
from .train_h504 import run_h504_hgb


_read_table = read_table

def _write_table(frame,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix.lower() in {'.parquet','.pq'}:
        try:
            frame.to_parquet(path,index=False)
            return path
        except (ImportError, ModuleNotFoundError):
            alt=path.with_suffix('.csv.gz'); frame.to_csv(alt,index=False); return alt
    frame.to_csv(path,index=False); return path

def _fingerprint_path(path: Path, block_size=1024*1024):
    h=hashlib.sha256();
    with path.open('rb') as f:
        for b in iter(lambda:f.read(block_size),b''): h.update(b)
    return h.hexdigest()

def _json(path,payload): Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')

def _feature_cols(frame): return [c for c in frame.columns if c not in {'code','date','market_session_id'} and pd.api.types.is_numeric_dtype(frame[c])]

def _baseline_feature_cols(feature_cols):
    # Snapshot baseline keeps point-in-time KDJ/position/price-volume context but excludes
    # research additions whose incremental value is supposed to be measured separately.
    return [c for c in feature_cols if not c.startswith('vir') and not c.startswith('vp_') and not c.startswith('kdj_low_')]

def build_research_features(panel:pd.DataFrame):
    feat,source=build_snapshot_features(panel)
    feat=add_volume_pressure(panel,feat)
    feat=add_kdj_path_features(feat)
    p=add_market_session_id(panel)
    vir=volume_impact_recovery(p[['code','date','market_session_id','high','low','close','volume']])
    vcols=[c for c in vir.columns if c.startswith('vir')]
    feat=feat.merge(vir[['code','date']+vcols],on=['code','date'],how='left',validate='one_to_one')
    return feat,source

def build_parser():
    p=argparse.ArgumentParser(description='Executable isolated H504 research candidate v5 with causal candidate-manifest integration and resumable checkpoints')
    p.add_argument('--stage',choices=['contract','inspect','candidates','features','label-sample','dedupe','h504-hgb','aux-tcn','all'],default='contract')
    p.add_argument('--calendar',type=Path,help='independent market calendar CSV with date column; required for real runs')
    p.add_argument('--resume',action='store_true',help='compatible completed experiments are reused; resume is always enabled')
    p.add_argument('--offline',action='store_true',help='all execution is local-only; network is never used')
    p.add_argument('--panel',type=Path); p.add_argument('--layers',type=Path); p.add_argument('--candidates',type=Path); p.add_argument('--signals',type=Path); p.add_argument('--out',type=Path)
    p.add_argument('--min-tier',type=int,default=1); p.add_argument('--candidate-version',default='lowzone-tier-v1')
    p.add_argument('--horizon',type=int,default=504); p.add_argument('--max-candidates',type=int,default=5000); p.add_argument('--cooldown',type=int,default=60)
    p.add_argument('--seeds',default='17,29,43'); p.add_argument('--hgb-min-samples-leaf',type=int,default=300); p.add_argument('--max-epochs',type=int,default=30); p.add_argument('--patience',type=int,default=5); p.add_argument('--batch-size',type=int,default=256)
    p.add_argument('--skip-neural',action='store_true'); p.add_argument('--max-aux-fits',type=int,default=6)
    p.add_argument('--target-active-seconds',type=int,default=10800); p.add_argument('--normal-wall-limit-seconds',type=int,default=12600); p.add_argument('--hard-runner-timeout-seconds',type=int,default=13200)
    p.add_argument('--registered-task-timeout-seconds',type=int); p.add_argument('--source-sha',default='UNKNOWN'); p.add_argument('--effective-prompt-sha256',default='UNKNOWN')
    p.add_argument('--evidence-type',choices=['UNSPECIFIED','REAL_MARKET','AUX_REAL_HISTORY','SYNTHETIC'],default='UNSPECIFIED')
    return p

def main(argv=None):
    args=build_parser().parse_args(argv); spec=H504TaskSpec(horizon_market_sessions=args.horizon)
    if args.stage=='contract':
        payload=spec.to_dict(); _json(args.out,payload) if args.out else print(json.dumps(payload,ensure_ascii=False,indent=2)); return 0
    if args.stage=='candidates':
        if args.layers is None: raise SystemExit('--layers required for candidate manifest stage')
        if args.out is None: raise SystemExit('--out FILE required for candidate manifest stage')
        layers=_read_table(args.layers)
        c=build_candidate_manifest(layers,CandidateSpec(min_tier=args.min_tier,version=args.candidate_version))
        written=_write_table(c,args.out)
        print(json.dumps({'status':'COMPLETE_CANDIDATE_MANIFEST','rows':len(c),'stocks':int(c.code.nunique()),'min_tier':args.min_tier,'candidate_version':args.candidate_version,'path':str(written)},ensure_ascii=False))
        return 0
    if args.panel is None: raise SystemExit('--panel is required for this stage')
    if args.evidence_type in {'REAL_MARKET','AUX_REAL_HISTORY'} and args.calendar is None:
        raise SystemExit('BLOCKED_CALENDAR: real data requires --calendar; panel union is not an exchange calendar')
    if args.evidence_type in {'REAL_MARKET','AUX_REAL_HISTORY'} and args.horizon != 504:
        raise SystemExit('real primary task requires horizon=504; AUX is a separate task scope')
    independent_cal=read_table(args.calendar)['date'] if args.calendar is not None else None
    panel,cal=prepare_panel(_read_table(args.panel),independent_cal)
    pipeline_hash=stable_hash({p.name:_fingerprint_path(p) for p in Path(__file__).parent.glob('*.py')})
    calendar_hash=stable_hash([str(d) for d in cal])
    if args.stage=='inspect':
        if args.out is None: raise SystemExit('--out DIR required')
        args.out.mkdir(parents=True,exist_ok=True); inv={'panel_path':str(args.panel),'panel_sha256':_fingerprint_path(args.panel),'rows':len(panel),'stocks':panel.code.nunique(),'sessions':len(cal),'date_min':str(cal.min().date()),'date_max':str(cal.max().date())}
        _json(args.out/'data_inventory.json',inv); _json(args.out/'task_spec.json',spec.to_dict()); _json(args.out/'fold_support.json',fold_support_summary(cal,cal,horizon=args.horizon)); print(json.dumps(inv,default=str)); return 0
    if args.stage=='label-sample':
        c=panel[['code','date']].head(args.max_candidates) if args.candidates is None else _read_table(args.candidates)[['code','date']].head(args.max_candidates); got=label_h504_candidates(panel,c,spec=spec,calendar=cal); _write_table(got,args.out); return 0
    if args.stage=='dedupe':
        got=dedupe_signals_market_calendar(_read_table(args.signals),calendar=cal,cooldown=args.cooldown); _write_table(got,args.out); return 0
    if args.stage in {'features','h504-hgb','aux-tcn','all'}:
        if args.out is None: raise SystemExit('--out DIR required')
        out=args.out; out.mkdir(parents=True,exist_ok=True); start=time.time()
        receipt=None
        if args.stage=='all':
            receipt=ResearchSessionReceipt(out,target_active_seconds=args.target_active_seconds,normal_wall_limit_seconds=args.normal_wall_limit_seconds,hard_runner_timeout_seconds=args.hard_runner_timeout_seconds,evidence_type=args.evidence_type,source_sha=args.source_sha,effective_prompt_sha256=args.effective_prompt_sha256,registered_task_timeout_seconds=args.registered_task_timeout_seconds)
            phase=receipt.begin_phase('build_features_and_diagnostics','data_compute')
        feat,feature_source=build_research_features(panel); feature_cols=_feature_cols(feat)
        _write_table(feat,out/'features.parquet'); write_factor_diagnostics(feat,feature_cols,out/'diagnostics'); _json(out/'feature_schema.json',{'source':feature_source,'features':feature_cols,'rows':len(feat)})
        if receipt: receipt.end_phase(phase,status='COMPLETE')
        if args.stage=='features': return 0
        if args.stage=='h504-hgb':
            if args.candidates is not None:
                cand=_read_table(args.candidates)
            elif args.layers is not None:
                layers=_read_table(args.layers)
                cand=build_candidate_manifest(layers,CandidateSpec(min_tier=args.min_tier,version=args.candidate_version))
                _write_table(cand,out/'candidate_manifest.csv')
            else:
                raise SystemExit('--candidates or --layers required for H504 training; candidate population must not be invented')
            t0_cols=_baseline_feature_cols(feature_cols)
            res=run_h504_hgb(panel,feat,cand,t0_cols,out/'h504_T0',model_id='T0',horizon=args.horizon,min_samples_leaf=args.hgb_min_samples_leaf,calendar=cal); print(json.dumps(res,default=str)); return 0
        if args.stage=='aux-tcn':
            seed=int(str(args.seeds).split(',')[0]); res=run_aux_tcn(feat,panel,feature_cols,out/f'aux_tcn_seed{seed}',seed=seed,max_epochs=args.max_epochs,patience=args.patience,batch_size=args.batch_size); print(json.dumps(res,default=str)); return 0
        # all: inventory + fold support + real factor diagnostics + H504 if candidate manifest is explicitly supplied + AUX fallback/continuation.
        inv={'panel_path':str(args.panel),'panel_sha256':_fingerprint_path(args.panel),'rows':len(panel),'stocks':panel.code.nunique(),'sessions':len(cal),'date_min':str(cal.min().date()),'date_max':str(cal.max().date()),'feature_source':feature_source,'feature_count':len(feature_cols),'calendar_hash':calendar_hash,'pipeline_hash':pipeline_hash}
        _json(out/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'pid':os.getpid()}); _json(out/'data_inventory.json',inv); _json(out/'task_spec.json',spec.to_dict())
        min_train_t0=max(100,2*int(args.hgb_min_samples_leaf))
        fs_struct=fold_support_summary(cal,cal,horizon=args.horizon,min_train_candidates=1,min_dev_candidates=1,dev_block_sessions=63); fs_struct['candidate_basis']='calendar_structural_one_date_per_session_reference'
        _json(out/'fold_support_calendar_structural.json',fs_struct)
        fs={'status':'BLOCKED_CANDIDATE_MANIFEST','candidate_basis':'missing','calendar_structural_reference':fs_struct}
        registry=Registry(out/'experiment_registry.jsonl'); results=[]; interrupted=False
        cand_path=args.candidates
        if cand_path is None and args.layers is not None:
            candidate_phase=receipt.begin_phase('build_candidate_manifest','data_compute') if receipt else None
            layers=_read_table(args.layers)
            cand=build_candidate_manifest(layers,CandidateSpec(min_tier=args.min_tier,version=args.candidate_version))
            cand_path=_write_table(cand,out/'candidate_manifest.csv')
            _json(out/'candidate_manifest_meta.json',{'source_layers':str(args.layers),'source_layers_sha256':_fingerprint_path(args.layers),'candidate_version':args.candidate_version,'min_tier':args.min_tier,'rows':len(cand),'stocks':int(cand.code.nunique())})
            if receipt: receipt.end_phase(candidate_phase,status='COMPLETE')
        if cand_path is not None:
            cand=_read_table(cand_path)
            fs=fold_support_summary(cal,pd.to_datetime(cand['date']),horizon=args.horizon,min_train_candidates=min_train_t0,min_dev_candidates=50,dev_block_sessions=63); fs['candidate_basis']='actual_manifest_model_T0'; fs['candidate_rows']=int(len(cand)); fs['candidate_stocks']=int(cand['code'].astype(str).nunique())
            _json(out/'fold_support.json',fs)
            t0_cols=_baseline_feature_cols(feature_cols)
            hgb_config={'max_leaf_nodes':7,'min_samples_leaf':int(args.hgb_min_samples_leaf),'l2_regularization':10.0,'learning_rate':0.03,'max_iter':100,'early_stopping':False,'seed':17}
            sig=stable_hash({'pipeline_hash':pipeline_hash,'calendar_hash':calendar_hash,'task':'h504_T0','data':inv['panel_sha256'],'cand_sha256':_fingerprint_path(Path(cand_path)),'features':t0_cols,'horizon':args.horizon,'model_config':hgb_config})
            previous=registry.latest_complete(sig)
            if previous is None:
                phase=receipt.begin_phase('h504_T0','training_h504') if receipt else None
                r=run_h504_hgb(panel,feat,cand,t0_cols,out/'h504_T0',model_id='T0',horizon=args.horizon,min_samples_leaf=args.hgb_min_samples_leaf,calendar=cal)
                registry.append({'experiment_id':'EML-EXP-KDJ-PATH-001-REAL/T0','signature':sig,'evidence_type':args.evidence_type,'task_scope':'H504_JOINT',**r}); results.append(r)
                if receipt: receipt.count_fit(r.get('status','UNKNOWN')); receipt.end_phase(phase,status=r.get('status','UNKNOWN'))
            else:
                results.append({'task_scope':'H504_JOINT','status':'REUSED_COMPLETE','model_id':'T0','source_status':previous.get('status'),'experiment_id':previous.get('experiment_id'),'signature':sig})
        else:
            _json(out/'fold_support.json',fs)
            results.append({'task_scope':'H504_JOINT','status':'BLOCKED_CANDIDATE_MANIFEST','reason':'supply --candidates or causal --layers; H504 candidate population is never inferred from all panel rows'})
        if not args.skip_neural:
            seeds=[int(x) for x in str(args.seeds).split(',') if x.strip()]
            # two representations: base excludes research additions; plus includes all candidate continuous research factors.
            base=_baseline_feature_cols(feature_cols)
            reps=[('base',base),('plus_research',feature_cols)]
            nfit=0
            for rep,cols in reps:
                for seed in seeds:
                    if nfit>=args.max_aux_fits or interrupted: break
                    if receipt and time.monotonic()>=receipt.deadline_monotonic:
                        interrupted=True; break
                    sig=stable_hash({'pipeline_hash':pipeline_hash,'calendar_hash':calendar_hash,'task':'aux_tcn','rep':rep,'seed':seed,'data':inv['panel_sha256'],'features':cols,'epochs':args.max_epochs,'patience':args.patience,'batch_size':args.batch_size})
                    previous=registry.latest_complete(sig)
                    if previous is not None:
                        results.append({'task_scope':'AUX_HISTORY','status':'REUSED_COMPLETE','model_id':f'AUX-TCN/{rep}/{seed}','source_status':previous.get('status'),'experiment_id':previous.get('experiment_id'),'signature':sig})
                        continue
                    phase=receipt.begin_phase(f'aux_tcn_{rep}_{seed}','training_aux') if receipt else None
                    r=run_aux_tcn(feat,panel,cols,out/f'aux_tcn_{rep}_seed{seed}',seed=seed,max_epochs=args.max_epochs,patience=args.patience,batch_size=args.batch_size,deadline_monotonic=receipt.deadline_monotonic if receipt else None,resume=True,data_signature=sig)
                    r={'task_scope':'AUX_HISTORY',**r}
                    registry.append({'experiment_id':f'EML-EXP-KDJ-PATH-001-REAL/AUX-TCN/{rep}/{seed}','signature':sig,'evidence_type':args.evidence_type,'task_scope':'AUX_HISTORY',**r}); results.append(r); nfit+=1
                    if receipt: receipt.count_fit(r.get('status','UNKNOWN')); receipt.end_phase(phase,status=r.get('status','UNKNOWN'))
                    if str(r.get('status','')).startswith('INTERRUPTED'): interrupted=True
        if interrupted:
            status='INTERRUPTED_WALL_BUDGET'
        elif any(str(r.get('status','')).startswith('COMPLETE') or r.get('status')=='REUSED_COMPLETE' for r in results):
            status='COMPLETED_AVAILABLE_RESEARCH_NOT_CERTIFIED'
        else:
            status='BLOCKED_NO_FIT'
        summary={'status':status,'elapsed_sec':time.time()-start,'results':results,'fold_support':fs,'feature_source':feature_source,'evidence_type':args.evidence_type}
        _json(out/'run_summary.json',summary); _json(out/'next_actions.json',{'if_h504_blocked':'supply longer authorized history and explicit candidate manifest; do not shorten H504','if_aux_complete':'compare paired base vs plus_research across seeds; inspect full predictions and error slices','if_interrupted':'rerun the identical command and registry/checkpoint resume will continue without redoing completed signatures'})
        if receipt:
            receipt.finalize(stop_reason='WALL_BUDGET_REACHED' if interrupted else 'QUEUE_DRAINED_OR_BLOCKED',result_status=status,extra={'run_summary_status':status,'registry_rows':len(registry.rows())})
        print(json.dumps(summary,ensure_ascii=False,default=str)); return 0
    raise AssertionError(args.stage)

if __name__=='__main__': raise SystemExit(main())
