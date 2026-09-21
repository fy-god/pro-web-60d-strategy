import json
import numpy as np
import pandas as pd
import pytest

from src.ml.research_h504 import (
    FeatureSpec, FeatureSpecError, FrozenFamilyECDF, H504TaskSpec,
    dedupe_signals_market_calendar, enumerate_mature_splits, fold_support_summary,
    label_h504_candidates, minimum_dense_sessions_for_full_maturity_split,
    volume_impact_recovery,
)


def _panel(n=510, code="000001", base=10.0):
    dates = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({
        "code": code, "date": dates,
        "open": base, "high": base * 1.01, "low": base * 0.99,
        "close": base, "volume": 1000.0,
    })


def test_h504_uses_close_strict_not_high():
    p = _panel()
    # candidate at day0 enters at day1 E=10.  High crosses but close does not.
    p.loc[10, ["high", "close", "low"]] = [41.0, 39.0, 9.0]
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    assert out.iloc[0].outcome_class == "timeout"
    assert out.iloc[0].label_joint == 0.0


def test_h504_close_equal_4e_is_not_success():
    p = _panel()
    p.loc[8, ["high", "close", "low"]] = [41.0, 40.0, 9.0]
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    assert out.iloc[0].outcome_class == "timeout"


def test_h504_close_gt_4e_success():
    p = _panel()
    p.loc[8, ["high", "close", "low"]] = [42.0, 40.01, 9.0]
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    assert out.iloc[0].outcome_class == "success"
    assert out.iloc[0].label_joint == 1.0


def test_h504_risk_priority_same_day():
    p = _panel()
    p.loc[8, ["high", "close", "low"]] = [42.0, 41.0, 7.99]
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    assert out.iloc[0].outcome_class == "risk"
    assert out.iloc[0].label_joint == 0.0


def test_no_entry_does_not_roll_to_reopen():
    p = _panel()
    # Remove t+1 for this stock. Later bars exist but must never become entry.
    entry_date = p.loc[1, "date"]
    p2 = p[p.date != entry_date]
    out = label_h504_candidates(p2, pd.DataFrame({"code":["000001"], "date":[p.loc[0,"date"]]}), calendar=p.date)
    assert out.iloc[0].outcome_class == "no_entry"
    assert np.isnan(out.iloc[0].entry_open)


def test_missing_post_entry_bar_is_unknown_not_timeout():
    p = _panel()
    missing = p.loc[20, "date"]
    p2 = p[p.date != missing]
    out = label_h504_candidates(p2, pd.DataFrame({"code":["000001"], "date":[p.loc[0,"date"]]}), calendar=p.date)
    assert out.iloc[0].outcome_class == "unknown_missing_bar"
    assert np.isnan(out.iloc[0].label_joint)


def test_early_success_is_known_but_not_admitted_early_to_full_followup_bce():
    p = _panel(n=300)
    p.loc[8, "close"] = 50.0
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    row = out.iloc[0]
    assert row.outcome_class == "success"
    assert row.label_joint == 1.0 and bool(row.label_resolved)
    assert not bool(row.training_eligible)
    assert pd.isna(row.training_eligible_at)
    assert row.label_known_at == p.loc[8, "date"]


def test_incomplete_nonterminal_candidate_remains_pending_not_negative():
    p = _panel(n=300)
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    row = out.iloc[0]
    assert row.outcome_class == "pending_maturity"
    assert np.isnan(row.label_joint)
    assert not bool(row.label_resolved)


def test_feature_spec_never_auto_accepts_metadata():
    f = pd.DataFrame({"x":[1.0], "known_at":["future"], "label_joint":[1.0], "deadline":["future"]})
    spec = FeatureSpec.from_names(["x"])
    assert list(spec.select(f).columns) == ["x"]
    with pytest.raises(FeatureSpecError):
        FeatureSpec.from_names(["x", "known_at"])


def test_feature_spec_fails_closed_when_declared_feature_missing():
    spec = FeatureSpec.from_names(["x", "y"])
    with pytest.raises(FeatureSpecError):
        spec.select(pd.DataFrame({"x":[1]}))


def test_887_sessions_have_no_mature_train_to_later_mature_dev_h504():
    cal = pd.bdate_range("2023-01-01", periods=887)
    splits = enumerate_mature_splits(cal, cal, horizon=504, min_train_candidates=1, min_dev_candidates=1)
    assert splits.empty


def test_longer_calendar_can_have_legal_h504_split():
    cal = pd.bdate_range("2018-01-01", periods=1200)
    splits = enumerate_mature_splits(cal, cal, horizon=504, min_train_candidates=1, min_dev_candidates=1)
    assert not splits.empty
    row = splits.iloc[0]
    assert row.n_train >= 1 and row.n_dev >= 1


def _vir_frame(n=90):
    dates = pd.bdate_range("2024-01-01", periods=n)
    # Alternating signs guarantee both directions in each 10-session block.
    r = np.array([0.006 if i % 2 == 0 else -0.004 for i in range(n)])
    close = 100*np.exp(np.cumsum(r))
    high = close*1.01
    low = close*0.99
    volume = 1_000_000*(1 + 0.15*np.sin(np.arange(n)/3))
    return pd.DataFrame({
        "code":"000001", "date":dates, "market_session_id":np.arange(n),
        "high":high, "low":low, "close":close, "volume":volume,
    })


def test_vir_is_price_and_volume_scale_invariant():
    f = _vir_frame()
    a = volume_impact_recovery(f)
    g = f.copy()
    g[["high","low","close"]] *= 10.0
    g["volume"] *= 7.0
    b = volume_impact_recovery(g)
    ok = a.vir.notna() & b.vir.notna()
    assert ok.any()
    np.testing.assert_allclose(a.loc[ok,"vir"], b.loc[ok,"vir"], rtol=1e-10, atol=1e-10)


def test_vir_future_perturbation_does_not_change_prefix():
    f = _vir_frame()
    a = volume_impact_recovery(f)
    cutoff = 60
    g = f.copy()
    g.loc[g.index > cutoff, ["high","low","close","volume"]] *= [3, 0.5, 2, 5]
    b = volume_impact_recovery(g)
    np.testing.assert_allclose(a.loc[:cutoff,"vir"], b.loc[:cutoff,"vir"], equal_nan=True)


def test_vir_does_not_bridge_market_session_gap():
    f = _vir_frame()
    f = f.drop(index=50).reset_index(drop=True)
    out = volume_impact_recovery(f)
    # The first row after the gap cannot have a valid 20-session consecutive window.
    after = out[out.market_session_id == 51].iloc[0]
    assert np.isnan(after.vir)



def test_vir_rejects_duplicate_plus_compensating_jump():
    f = _vir_frame()
    # Keep row count/endpoints plausible while introducing a 0-step and 2-step.
    f.loc[50, "market_session_id"] = 49
    f.loc[51, "market_session_id"] = 51
    out = volume_impact_recovery(f)
    assert np.isnan(out.loc[out.market_session_id == 51, "vir"].iloc[0])


def test_family_ecdf_is_frozen_and_clone_free_by_construction():
    train = pd.DataFrame({"base_a":[0,1,2,3], "base_b":[10,11,12,13]})
    dev = pd.DataFrame({"base_a":[100,2], "base_b":[-100,12]})
    cols = {"A":"base_a", "B":"base_b"}
    enc = FrozenFamilyECDF().fit(train, cols)
    got = enc.transform(dev, cols)
    # Values outside training range saturate by frozen train distribution; no refit.
    assert got.loc[0,"family_q__A"] == 1.0
    assert got.loc[0,"family_q__B"] == 0.0
    assert {"meb","family_coverage","family_dominance"}.issubset(got.columns)


def test_full_followup_early_success_waits_until_deadline_for_training_queue():
    p = _panel(n=510)
    p.loc[8, "close"] = 50.0
    out = label_h504_candidates(p, p.iloc[[0]][["code", "date"]])
    row = out.iloc[0]
    assert row.outcome_class == "success"
    assert bool(row.label_resolved) and bool(row.training_eligible)
    assert row.label_known_at == p.loc[8, "date"]
    assert row.training_eligible_at == p.loc[504, "date"]
    assert row.label_known_at < row.training_eligible_at


def test_market_calendar_dedupe_does_not_need_filler_rows():
    cal = pd.bdate_range("2024-01-01", periods=130)
    sig = pd.DataFrame({
        "code": ["000001", "000001"],
        "date": [cal[0], cal[108]],
        "score": [0.8, 0.9],
    })
    got = dedupe_signals_market_calendar(sig, calendar=cal, cooldown=60)
    assert len(got) == 2


def test_market_calendar_dedupe_suppresses_59_and_keeps_60_without_fillers():
    cal = pd.bdate_range("2024-01-01", periods=80)
    sig59 = pd.DataFrame({"code":["1","1"], "date":[cal[0], cal[59]]})
    sig60 = pd.DataFrame({"code":["1","1"], "date":[cal[0], cal[60]]})
    assert len(dedupe_signals_market_calendar(sig59, calendar=cal, cooldown=60)) == 1
    assert len(dedupe_signals_market_calendar(sig60, calendar=cal, cooldown=60)) == 2


def test_market_calendar_dedupe_fails_closed_if_signal_date_not_in_calendar():
    cal = pd.bdate_range("2024-01-01", periods=10)
    sig = pd.DataFrame({"code":["1"], "date":[pd.Timestamp("2024-01-06")]})
    with pytest.raises(ValueError):
        dedupe_signals_market_calendar(sig, calendar=cal, cooldown=2)


def test_full_maturity_minimum_session_formula_is_scoped_not_global_claim():
    assert minimum_dense_sessions_for_full_maturity_split(504) == 1010
    cal = pd.bdate_range("2023-01-01", periods=887)
    summary = fold_support_summary(cal, cal, horizon=504)
    assert summary["n_legal_full_followup_splits"] == 0
    assert summary["does_not_imply_repository_or_local_history_absence"] is True
    assert summary["scope"] == "full_followup_bce_on_supplied_calendar_only"


def test_cli_inspect_and_label_sample(tmp_path):
    from src.ml.research_h504.run import main
    p = _panel(n=510)
    panel_path = tmp_path / "panel.csv"
    p.to_csv(panel_path, index=False)
    out_dir = tmp_path / "inspect"
    assert main(["--stage", "inspect", "--panel", str(panel_path), "--out", str(out_dir)]) == 0
    assert (out_dir / "data_inventory.json").exists()
    assert (out_dir / "fold_support.json").exists()
    labels_path = tmp_path / "labels.csv"
    assert main(["--stage", "label-sample", "--panel", str(panel_path), "--max-candidates", "3", "--out", str(labels_path)]) == 0
    got = pd.read_csv(labels_path)
    assert len(got) == 3


def test_feature_spec_rejects_new_h504_oracle_metadata():
    for name in ["training_eligible", "target_price", "risk_floor", "candidate_id", "signal_date"]:
        with pytest.raises(FeatureSpecError):
            FeatureSpec.from_names(["x", name])


def test_tcn_receptive_field_is_253_for_six_double_conv_blocks():
    from src.ml.research_h504.aux_tcn import tcn_receptive_field
    assert tcn_receptive_field() == 253


def test_minimal_snapshot_and_path_are_prefix_invariant():
    from src.ml.research_h504.snapshot_features import build_minimal_snapshot_features, add_kdj_path_features
    p = _panel(n=300)
    a = add_kdj_path_features(build_minimal_snapshot_features(p))
    g = p.copy()
    g.loc[g.index > 200, ['open','high','low','close','volume']] *= [2,2,2,2,3]
    b = add_kdj_path_features(build_minimal_snapshot_features(g))
    cols = ['ret5','pos_60','kdj_k','kdj_low_occ_21','kdj_low_streak']
    for c in cols:
        np.testing.assert_allclose(a.loc[:200,c], b.loc[:200,c], equal_nan=True, rtol=1e-6, atol=1e-6)


def test_all_stage_runs_diagnostics_and_blocks_h504_without_candidate_manifest(tmp_path):
    from src.ml.research_h504.run import main
    p = _panel(n=220)
    panel_path = tmp_path/'panel.csv'; p.to_csv(panel_path,index=False)
    out = tmp_path/'run'
    assert main(['--stage','all','--panel',str(panel_path),'--out',str(out),'--skip-neural']) == 0
    assert (out/'data_inventory.json').exists()
    assert (out/'diagnostics'/'feature_health.csv').exists()
    summary = json.loads((out/'run_summary.json').read_text())
    assert summary['results'][0]['status'] == 'BLOCKED_CANDIDATE_MANIFEST'


def test_aux_split_has_embargo():
    from src.ml.research_h504.aux_tcn import choose_aux_split
    s = np.arange(300)
    split = choose_aux_split(s, dev_fraction=.2, embargo=5)
    assert split.dev_start_session - split.train_end_session >= 6


def test_aux_tcn_can_fit_and_save_complete_predictions(tmp_path):
    torch = pytest.importorskip('torch')
    from src.ml.research_h504.snapshot_features import build_minimal_snapshot_features
    from src.ml.research_h504.aux_tcn import run_aux_tcn
    # Multiple stocks, enough windows, very small network run (1 epoch) is an integration smoke only.
    frames=[]
    for k in range(8):
        p=_panel(n=220, code=f'{k+1:06d}', base=10+k)
        x=np.arange(len(p)); p['close'] *= np.exp(0.003*np.sin(x/5+k)); p['open']=p['close']*(1-0.001); p['high']=p['close']*1.01; p['low']=p['close']*.99
        frames.append(p)
    panel=pd.concat(frames,ignore_index=True)
    feat=build_minimal_snapshot_features(panel)
    cols=['ret1','ret5','vol20','atr14_pct','pos_60','kdj_k','kdj_k_minus_d']
    res=run_aux_tcn(feat,panel,cols,tmp_path/'aux',seed=17,window=32,max_epochs=1,patience=1,batch_size=128)
    assert res['status']=='COMPLETE_AUX'
    assert res['train_windows']>1000 and res['dev_windows']>200
    assert (tmp_path/'aux'/'best.pt').exists()
    pred=pd.read_csv(tmp_path/'aux'/'dev_predictions.csv')
    assert len(pred)==res['dev_windows']


def test_all_stage_writes_start_and_execution_receipts(tmp_path):
    from src.ml.research_h504.run import main
    p = _panel(n=220)
    panel_path = tmp_path/'panel.csv'; p.to_csv(panel_path,index=False)
    out = tmp_path/'run_receipt'
    assert main(['--stage','all','--panel',str(panel_path),'--out',str(out),'--skip-neural',
                 '--evidence-type','SYNTHETIC','--target-active-seconds','10800',
                 '--normal-wall-limit-seconds','12600','--hard-runner-timeout-seconds','13200']) == 0
    start = json.loads((out/'local_start_receipt.json').read_text())
    end = json.loads((out/'execution_receipt.json').read_text())
    assert start['target_active_seconds'] == 10800
    assert start['normal_wall_limit_seconds'] == 12600
    assert end['target_met'] is False
    assert end['evidence_type'] == 'SYNTHETIC'
    assert end['data_compute_seconds'] > 0
    assert end['real_train_seconds'] == 0
    assert any(a['path'].endswith('run_summary.json') for a in end['artifacts'])


def test_aux_checkpoint_has_matching_best_epoch_and_last(tmp_path):
    torch = pytest.importorskip('torch')
    from src.ml.research_h504.snapshot_features import build_minimal_snapshot_features
    from src.ml.research_h504.aux_tcn import run_aux_tcn
    frames=[]
    for k in range(8):
        p=_panel(n=220, code=f'{k+1:06d}', base=10+k)
        x=np.arange(len(p)); p['close'] *= np.exp(0.003*np.sin(x/5+k)); p['open']=p['close']*(1-0.001); p['high']=p['close']*1.01; p['low']=p['close']*.99
        frames.append(p)
    panel=pd.concat(frames,ignore_index=True)
    feat=build_minimal_snapshot_features(panel)
    cols=['ret1','ret5','vol20','atr14_pct','pos_60','kdj_k','kdj_k_minus_d']
    out=tmp_path/'aux_ckpt'
    res=run_aux_tcn(feat,panel,cols,out,seed=17,window=32,max_epochs=2,patience=2,batch_size=128)
    assert res['status']=='COMPLETE_AUX'
    assert (out/'last.pt').exists() and (out/'best.pt').exists()
    best=torch.load(out/'best.pt',map_location='cpu',weights_only=False)
    last=torch.load(out/'last.pt',map_location='cpu',weights_only=False)
    assert best['epoch'] == best['best_epoch'] == res['best_epoch']
    assert 'optimizer' in best and 'model' in best
    assert last['epoch'] >= best['epoch']


def test_aux_rerun_resumes_existing_last_checkpoint(tmp_path):
    pytest.importorskip('torch')
    from src.ml.research_h504.snapshot_features import build_minimal_snapshot_features
    from src.ml.research_h504.aux_tcn import run_aux_tcn
    frames=[]
    for k in range(8):
        p=_panel(n=220, code=f'{k+1:06d}', base=10+k)
        x=np.arange(len(p)); p['close'] *= np.exp(0.003*np.sin(x/7+k)); p['open']=p['close']*.999; p['high']=p['close']*1.01; p['low']=p['close']*.99
        frames.append(p)
    panel=pd.concat(frames,ignore_index=True)
    feat=build_minimal_snapshot_features(panel)
    cols=['ret1','ret5','vol20','atr14_pct','pos_60','kdj_k','kdj_k_minus_d']
    out=tmp_path/'aux_resume'
    first=run_aux_tcn(feat,panel,cols,out,seed=29,window=32,max_epochs=1,patience=5,batch_size=128)
    assert first['status']=='COMPLETE_AUX' and first['epochs']==1
    second=run_aux_tcn(feat,panel,cols,out,seed=29,window=32,max_epochs=2,patience=5,batch_size=128,resume=True)
    assert second['status']=='COMPLETE_AUX'
    assert second['resumed'] is True
    assert second['epochs'] == 2


def test_aux_resume_fails_closed_on_training_config_mismatch(tmp_path):
    pytest.importorskip('torch')
    from src.ml.research_h504.snapshot_features import build_minimal_snapshot_features
    from src.ml.research_h504.aux_tcn import run_aux_tcn
    frames=[]
    for k in range(8):
        p=_panel(n=220, code=f'{k+1:06d}', base=10+k)
        x=np.arange(len(p)); p['close'] *= np.exp(0.003*np.sin(x/7+k)); p['open']=p['close']*.999; p['high']=p['close']*1.01; p['low']=p['close']*.99
        frames.append(p)
    panel=pd.concat(frames,ignore_index=True)
    feat=build_minimal_snapshot_features(panel)
    cols=['ret1','ret5','vol20','atr14_pct','pos_60','kdj_k','kdj_k_minus_d']
    out=tmp_path/'aux_mismatch'
    first=run_aux_tcn(feat,panel,cols,out,seed=17,window=32,max_epochs=1,patience=5,batch_size=128)
    assert first['status']=='COMPLETE_AUX'
    bad=run_aux_tcn(feat,panel,cols,out,seed=17,window=32,max_epochs=2,patience=5,batch_size=64,resume=True)
    assert bad['status']=='BLOCKED_CHECKPOINT_MISMATCH'


def test_candidate_manifest_ignores_future_columns_and_is_prefix_invariant():
    from src.ml.research_h504 import CandidateSpec, build_candidate_manifest, prefix_invariant
    dates = pd.bdate_range('2024-01-01', periods=8)
    layers = pd.DataFrame({
        'code':['000001']*8,
        'date':dates,
        'recall_tier':[0,1,2,0,3,1,0,4],
        # Deliberately poisonous columns: manifest builder must not inspect them.
        'label_joint':[1,0,1,1,0,1,0,1],
        'future_max_return':[99.0]*8,
        'entry_open':[123.0]*8,
    })
    got = build_candidate_manifest(layers, CandidateSpec(min_tier=1, version='test-v1'))
    assert len(got) == 5
    assert 'label_joint' not in got.columns and 'future_max_return' not in got.columns and 'entry_open' not in got.columns
    assert prefix_invariant(layers, dates[4], CandidateSpec(min_tier=1, version='test-v1'))


def test_cli_candidates_does_not_require_panel(tmp_path):
    from src.ml.research_h504.run import main
    layers = pd.DataFrame({
        'code':['1','1','2'],
        'date':pd.bdate_range('2024-01-01', periods=3),
        'recall_tier':[1,0,3],
        'label_joint':[1,1,0],
    })
    lp=tmp_path/'layers.csv'; layers.to_csv(lp,index=False)
    out=tmp_path/'candidates.csv'
    assert main(['--stage','candidates','--layers',str(lp),'--out',str(out),'--min-tier','1']) == 0
    got=pd.read_csv(out,dtype={'code':str})
    assert len(got)==2
    assert list(got['code']) == ['000001','000002']


def _long_h504_panel_and_layers(n_sessions=1180, n_stocks=12):
    dates=pd.bdate_range('2018-01-01', periods=n_sessions)
    frames=[]; layers=[]
    for k in range(n_stocks):
        # Half the stocks rise fast enough to clear 4E inside 504 sessions; half stay flat.
        if k < n_stocks//2:
            close=10.0*np.exp(0.0033*np.arange(n_sessions))
        else:
            close=np.full(n_sessions,10.0+0.1*k)
        p=pd.DataFrame({
            'code':f'{k+1:06d}','date':dates,
            'open':close,'high':close*1.01,'low':close*0.99,'close':close,
            'volume':1_000_000.0 + 1000*k,
        })
        frames.append(p)
        # Sparse natural-candidate stand-in: every 5 sessions after warmup, no future fields needed.
        idx=np.arange(70,n_sessions,5)
        layers.append(pd.DataFrame({'code':f'{k+1:06d}','date':dates[idx],'recall_tier':1}))
    return pd.concat(frames,ignore_index=True), pd.concat(layers,ignore_index=True)


def test_all_stage_can_build_candidate_manifest_and_complete_h504_dev_fit(tmp_path):
    pytest.importorskip('sklearn')
    from src.ml.research_h504.run import main
    panel,layers=_long_h504_panel_and_layers()
    pp=tmp_path/'panel.csv'; lp=tmp_path/'layers.csv'
    panel.to_csv(pp,index=False); layers.to_csv(lp,index=False)
    out=tmp_path/'full_h504'
    assert main(['--stage','all','--panel',str(pp),'--layers',str(lp),'--out',str(out),
                 '--skip-neural','--hgb-min-samples-leaf','20','--evidence-type','SYNTHETIC','--source-sha','synthetic-test']) == 0
    manifest=pd.read_csv(out/'candidate_manifest.csv')
    assert len(manifest)==len(layers)
    summary=json.loads((out/'run_summary.json').read_text())
    fs=json.loads((out/'fold_support.json').read_text())
    upper=json.loads((out/'fold_support_calendar_structural.json').read_text())
    assert fs['candidate_basis']=='actual_manifest_model_T0' and fs['candidate_rows']==len(layers)
    assert upper['candidate_basis']=='calendar_structural_one_date_per_session_reference'
    assert any(r.get('status')=='COMPLETE_H504_DEV' for r in summary['results'])
    metrics=json.loads((out/'h504_T0'/'metrics.json').read_text())
    assert metrics['n_train'] >= 100 and metrics['n_dev'] >= 50
    assert metrics['min_samples_leaf'] == 20 and metrics['min_train_candidates'] == 100
    pred=pd.read_csv(out/'h504_T0'/'dev_predictions.csv')
    assert len(pred)==metrics['n_dev']
    assert (out/'candidate_manifest_meta.json').exists()



def test_hgb_default_support_requires_two_min_leafs():
    from src.ml.research_h504.train_h504 import first_legal_split
    cal=pd.bdate_range('2018-01-01',periods=1180)
    # one candidate per session cannot satisfy 600 train rows before a later mature dev block until enough history exists
    split=first_legal_split(cal,cal,horizon=504,dev_block_sessions=63,min_train_candidates=600,min_dev_candidates=50)
    assert split is None


def test_registry_reuses_exact_complete_signature_only(tmp_path):
    from src.ml.research_h504.registry import Registry, stable_hash
    reg=Registry(tmp_path/'registry.jsonl')
    a=stable_hash({'model':'hgb','min_samples_leaf':300})
    b=stable_hash({'model':'hgb','min_samples_leaf':20})
    reg.append({'signature':a,'status':'COMPLETE_H504_DEV','experiment_id':'A'})
    assert reg.latest_complete(a)['experiment_id']=='A'
    assert reg.latest_complete(b) is None



def test_registry_task_scopes_keep_h504_and_aux_namespaces_distinct(tmp_path):
    from src.ml.research_h504.train_h504 import run_h504_hgb
    # Structural assertion on the emitted result contract: H504 has an explicit namespace.
    p=_panel(n=220)
    # No legal H504 fold here; even the blocked result must retain its H504 scope.
    feat=p[['code','date']].copy(); feat['x']=1.0
    cand=p.iloc[[0]][['code','date']]
    res=run_h504_hgb(p,feat,cand,['x'],tmp_path/'h504',min_samples_leaf=20)
    assert res['task_scope']=='H504_JOINT'



def test_t0_baseline_excludes_research_additions_but_keeps_snapshot_kdj():
    from src.ml.research_h504.run import _baseline_feature_cols
    cols=['ret5','pos_60','kdj_k','kdj_k_minus_d','kdj_low_occ_21','kdj_low_streak','vp_pressure_20','vir','vir_novol']
    got=_baseline_feature_cols(cols)
    assert 'ret5' in got and 'pos_60' in got and 'kdj_k' in got and 'kdj_k_minus_d' in got
    assert 'kdj_low_occ_21' not in got and 'kdj_low_streak' not in got
    assert 'vp_pressure_20' not in got and 'vir' not in got and 'vir_novol' not in got
