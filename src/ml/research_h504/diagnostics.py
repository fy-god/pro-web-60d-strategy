from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd


def feature_health(frame: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    rows=[]
    n=len(frame)
    for c in feature_cols:
        x=pd.to_numeric(frame[c],errors='coerce')
        finite=np.isfinite(x.to_numpy(float))
        vals=x.to_numpy(float)[finite]
        rows.append({
            'feature':c,'rows':n,'finite':int(finite.sum()),'coverage':float(finite.mean()) if n else np.nan,
            'nunique':int(pd.Series(vals).nunique()) if len(vals) else 0,
            'mean':float(np.mean(vals)) if len(vals) else np.nan,'std':float(np.std(vals)) if len(vals) else np.nan,
            'p01':float(np.quantile(vals,.01)) if len(vals) else np.nan,'p50':float(np.quantile(vals,.5)) if len(vals) else np.nan,
            'p99':float(np.quantile(vals,.99)) if len(vals) else np.nan,
            'constant':bool(len(vals)>0 and np.nanmax(vals)==np.nanmin(vals)),
        })
    return pd.DataFrame(rows)


def write_factor_diagnostics(frame: pd.DataFrame, feature_cols: list[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True,exist_ok=True)
    health=feature_health(frame, feature_cols)
    health.to_csv(out_dir/'feature_health.csv',index=False)
    numeric=frame[feature_cols].apply(pd.to_numeric,errors='coerce')
    corr=numeric.corr(method='spearman', min_periods=50)
    corr.to_csv(out_dir/'feature_spearman.csv')
    payload={
        'n_rows':int(len(frame)),'n_features':len(feature_cols),
        'features_coverage_lt_0_8':health.loc[health.coverage<.8,'feature'].tolist(),
        'constant_features':health.loc[health.constant,'feature'].tolist(),
    }
    (out_dir/'factor_diagnostics.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
