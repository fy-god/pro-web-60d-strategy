import importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from src.ml.research_h504.data_io import prepare_panel, read_table
from src.ml.research_h504.task_spec import label_h504_candidates, H504TaskSpec
from src.ml.research_h504.run import main


def panel(n=80):
    dates=pd.bdate_range('2020-01-01',periods=n)
    return pd.DataFrame({'code':'000001','date':dates,'open':10.,'high':11.,'low':9.,'close':10.,'volume':1000.})


def test_csv_preserves_leading_zero_code(tmp_path):
    p=tmp_path/'p.csv'; panel(8).to_csv(p,index=False)
    assert read_table(p).code.iloc[0]=='000001'


def test_independent_calendar_inserts_missing_all_stock_day():
    p=panel(); day=p.date.iloc[1]
    aligned,cal=prepare_panel(p.drop(index=1),p.date)
    assert pd.isna(aligned.loc[aligned.date.eq(day),'open']).all()
    result=label_h504_candidates(aligned,p.iloc[[0]][['code','date']],calendar=cal)
    assert result.iloc[0].outcome_class=='no_entry'


def test_future_calendar_is_not_followup_evidence():
    p=panel(30)
    _,cal=prepare_panel(p,pd.bdate_range(p.date.min(),periods=600))
    assert len(cal)==30


def test_real_cli_requires_calendar(tmp_path):
    p=tmp_path/'p.csv'; panel().to_csv(p,index=False)
    with pytest.raises(SystemExit,match='BLOCKED_CALENDAR'):
        main(['--stage','all','--panel',str(p),'--out',str(tmp_path/'out'),'--evidence-type','REAL_MARKET'])


def test_oracle_preserves_versioned_candidate_ids():
    p=panel(); c=p.iloc[[0]][['code','date']].copy();c['candidate_id']='frozen-versioned-id'
    r=label_h504_candidates(p,c,spec=H504TaskSpec(horizon_market_sessions=5))
    assert r.candidate_id.tolist()==['frozen-versioned-id']


def test_h504_prediction_keeps_unknown_candidates(tmp_path,monkeypatch):
    from src.ml.research_h504 import train_h504 as trainer
    blocks=[]
    for k in range(8):
        p=panel();p.code=f'{k:06}'
        if k%2==0:
            p.loc[p.index%7==3,['close','high']]=[41.,42.]
        blocks.append(p)
    p=pd.concat(blocks,ignore_index=True); cal=pd.DatetimeIndex(sorted(p.date.unique()))
    p.loc[p.code.eq('000001')&p.date.eq(cal[26]),'open']=np.nan
    c=p[['code','date']].copy();c['candidate_id']=['id'+str(i) for i in range(len(c))]
    f=c[['code','date']].copy(); f['x']=np.arange(len(f))%9
    monkeypatch.setattr(trainer,'first_legal_split',lambda *a,**k:{'dev_start':cal[20],'dev_end':cal[30]})
    r=trainer.run_h504_hgb(p,f,c,['x'],tmp_path/'fit',horizon=5,min_samples_leaf=20,calendar=cal)
    assert r['status']=='COMPLETE_H504_DEV'
    pred=pd.read_csv(tmp_path/'fit'/'dev_predictions.csv',dtype={'code':str})
    assert len(pred)==8*11 and r['n_dev_unknown']>=1
    assert pred.score.notna().all() and set(pred.candidate_id).issubset(set(c.candidate_id))
    assert r['reload_max_abs_error']==0


def load_runner():
    path=Path(__file__).resolve().parents[2]/'scripts'/'run_fixup.py'
    # tests/research_h504 -> tests -> repository
    path=Path(__file__).resolve().parents[2]/'scripts'/'run_fixup.py'
    spec=importlib.util.spec_from_file_location('delivery_runner',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def test_runner_dry_run_does_not_sync_or_create_logs(tmp_path,monkeypatch):
    m=load_runner();prompt=tmp_path/'prompt';prompt.write_text('test')
    monkeypatch.setattr(m,'PROMPT_FILE',prompt);monkeypatch.setattr(m,'LOG_DIR',tmp_path/'logs')
    monkeypatch.setattr(m,'find_dsh',lambda:(Path('/dummy'),'test'))
    monkeypatch.setattr(m,'sync_before_agent',lambda log:pytest.fail('dry-run synced'))
    assert m.main(['--dry-run'])==0
    assert not (tmp_path/'logs').exists()
    assert m.AGENT_TIMEOUT_SECONDS==13200


def test_runner_fetch_failure_does_not_merge_or_start(monkeypatch):
    import io
    m=load_runner();calls=[]
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=''))
    def fail(args,log):
        calls.append(args);return 1
    monkeypatch.setattr(m,'run_git',fail)
    assert m.sync_before_agent(io.StringIO()) is False
    assert calls==[['fetch','origin','main']]


def test_runner_dirty_worktree_is_not_autostashed(monkeypatch):
    import io
    m=load_runner()
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=' M x.py'))
    monkeypatch.setattr(m,'run_git',lambda *a:pytest.fail('dirty worktree was mutated'))
    assert m.sync_before_agent(io.StringIO()) is False


def test_new_command_flags_parse():
    from src.ml.research_h504.run import build_parser
    a=build_parser().parse_args(['--stage','all','--resume','--offline','--calendar','calendar.csv'])
    assert a.resume and a.offline
