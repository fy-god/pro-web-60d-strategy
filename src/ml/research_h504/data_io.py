"""Explicit local inputs: no downloads, no inferred calendar for real runs."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from .task_spec import normalize_calendar


def read_table(path: Path) -> pd.DataFrame:
    path=Path(path)
    if path.suffix.lower() in {'.parquet','.pq'}:
        return pd.read_parquet(path)
    if path.suffix.lower() in {'.csv','.txt','.gz'}:
        return pd.read_csv(path,dtype={'code':'string'})
    raise ValueError(f'unsupported table format: {path}')


def prepare_panel(panel: pd.DataFrame, calendar=None):
    p=panel.copy()
    required={'code','date','open','high','low','close','volume'}
    if not required.issubset(p):
        raise ValueError(f'missing OHLCV columns: {sorted(required-set(p))}')
    if p.empty or p[['code','date']].isna().any().any():
        raise ValueError('panel is empty or contains null keys')
    p['date']=pd.to_datetime(p['date'],errors='raise')
    p['code']=p['code'].astype(str)
    if p.duplicated(['code','date']).any():
        raise ValueError('duplicate panel keys')
    if calendar is None:
        return p.sort_values(['code','date']).reset_index(drop=True), normalize_calendar(p.date)
    cal=normalize_calendar(calendar)
    if not p.date.isin(cal).all():
        raise ValueError('panel dates are outside the supplied calendar')
    # Future scheduled sessions are not evidence of observed H504 follow-up.
    cal=cal[(cal>=p.date.min())&(cal<=p.date.max())]
    groups=[]
    for code,g in p.groupby('code',sort=False):
        span=cal[(cal>=g.date.min())&(cal<=g.date.max())]
        h=g.set_index('date').reindex(span)
        h.index.name='date'; h['code']=code
        groups.append(h.reset_index())
    out=pd.concat(groups,ignore_index=True)
    # Missing sessions remain NaN; never ffill prices or shift entry to reopening.
    return out.drop(columns=['market_session_id'],errors='ignore'),cal
