from __future__ import annotations

import json, pickle, time
from pathlib import Path
import numpy as np
import pandas as pd

from .feature_spec import FeatureSpec
from .fold_support import enumerate_mature_splits
from .task_spec import H504TaskSpec, label_h504_candidates, market_calendar


def _safe_impute(train: pd.DataFrame, dev: pd.DataFrame):
    med=train.median(axis=0,skipna=True).fillna(0.0)
    return train.fillna(med).replace([np.inf,-np.inf],np.nan).fillna(med), dev.fillna(med).replace([np.inf,-np.inf],np.nan).fillna(med), med


def first_legal_split(calendar, candidate_dates, horizon=504, dev_block_sessions=63, min_train_candidates=600, min_dev_candidates=50):
    s=enumerate_mature_splits(calendar,candidate_dates,horizon=horizon,min_train_candidates=min_train_candidates,min_dev_candidates=min_dev_candidates,dev_block_sessions=dev_block_sessions)
    if s.empty: return None
    return s.iloc[0].to_dict()


def run_h504_hgb(panel: pd.DataFrame, feature_frame: pd.DataFrame, candidates: pd.DataFrame,
                 feature_cols: list[str], out_dir: Path, *, model_id='T0', horizon=504,
                 seed=17, dev_block_sessions=63, min_samples_leaf=300, calendar=None) -> dict:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.metrics import log_loss, brier_score_loss, average_precision_score
    cal=market_calendar(panel) if calendar is None else pd.DatetimeIndex(calendar); spec=H504TaskSpec(horizon_market_sessions=horizon)
    labels=label_h504_candidates(panel,candidates,spec=spec,calendar=cal)
    # join features at signal date
    ff=feature_frame.copy(); ff['date']=pd.to_datetime(ff['date']); ff['code']=ff['code'].astype(str)
    labels['date']=pd.to_datetime(labels['signal_date']); labels['code']=labels['code'].astype(str)
    data=labels.merge(ff,on=['code','date'],how='left',validate='many_to_one')
    min_train_candidates=max(100, 2*int(min_samples_leaf))
    split=first_legal_split(cal,data['date'],horizon=horizon,dev_block_sessions=dev_block_sessions,min_train_candidates=min_train_candidates,min_dev_candidates=50)
    if split is None:
        return {'task_scope':'H504_JOINT','status':'BLOCKED_PROTOCOL_H504','reason':'no legal mature train->dev split for supplied candidate/calendar support','model_id':model_id,'resolved':int(data.label_resolved.sum()),'training_eligible':int(data.training_eligible.sum())}
    dev_start=pd.Timestamp(split['dev_start']); dev_end=pd.Timestamp(split['dev_end'])
    train=(data.training_eligible)&data.label_joint.notna()&(pd.to_datetime(data.training_eligible_at)<dev_start)
    dev=data['date'].between(dev_start,dev_end)
    resolved=dev & data.label_joint.notna()
    if train.sum()<min_train_candidates or dev.sum()<50:
        return {'task_scope':'H504_JOINT','status':'BLOCKED_PROTOCOL_H504','reason':f'actual merged support too small train={train.sum()} dev={dev.sum()}','model_id':model_id}
    specf=FeatureSpec.from_names(feature_cols); Xtr=specf.select(data.loc[train]); Xdv=specf.select(data.loc[dev]); Xtr,Xdv,med=_safe_impute(Xtr,Xdv)
    ytr=data.loc[train,'label_joint'].astype(int).to_numpy(); ydv=data.loc[resolved,'label_joint'].astype(int).to_numpy()
    if np.unique(ytr).size != 2:
        return {'task_scope':'H504_JOINT','status':'BLOCKED_CLASS_SUPPORT','model_id':model_id,'n_train':int(train.sum())}
    start=time.time(); model=HistGradientBoostingClassifier(max_leaf_nodes=7,min_samples_leaf=min_samples_leaf,l2_regularization=10,learning_rate=.03,max_iter=100,early_stopping=False,random_state=seed).fit(Xtr,ytr)
    p=model.predict_proba(Xdv)[:,1]; measured=p[data.loc[dev,'label_joint'].notna().to_numpy()]; eps=1e-8
    ll=float(log_loss(ydv,np.clip(measured,eps,1-eps),labels=[0,1])) if len(ydv) else None
    br=float(brier_score_loss(ydv,measured)) if len(ydv) else None
    ap=float(average_precision_score(ydv,measured)) if ydv.sum()>0 else None
    out_dir.mkdir(parents=True,exist_ok=True)
    with (out_dir/'model.pkl').open('wb') as fh: pickle.dump({'model':model,'feature_cols':feature_cols,'median':med,'split':split},fh)
    pred=data.loc[dev,['candidate_id','code','date','label_joint','outcome_class','label_known_at','training_eligible_at']].copy(); pred['model_id']=model_id; pred['score']=p; pred.to_csv(out_dir/'dev_predictions.csv',index=False)
    with (out_dir/'model.pkl').open('rb') as fh: restored=pickle.load(fh)
    reload_error=float(np.max(np.abs(restored['model'].predict_proba(Xdv)[:,1]-p)))
    metrics={'reload_max_abs_error':reload_error,'task_scope':'H504_JOINT','status':'COMPLETE_H504_DEV','model_id':model_id,'seed':seed,'n_train':int(train.sum()),'n_dev':int(dev.sum()),'dev_positives':int(ydv.sum()),'n_dev_resolved':int(len(ydv)),'n_dev_unknown':int(dev.sum()-len(ydv)),'base_rate':float(ydv.mean()) if len(ydv) else None,'min_train_candidates':int(min_train_candidates),'min_samples_leaf':int(min_samples_leaf),'logloss':ll,'brier':br,'average_precision':ap,'elapsed_sec':time.time()-start,'split':{k:str(v) for k,v in split.items()}}
    (out_dir/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8'); return metrics
