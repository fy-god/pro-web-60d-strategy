from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12


def add_market_session_id(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out['date'] = pd.to_datetime(out['date'], errors='raise')
    cal = pd.DatetimeIndex(sorted(out['date'].drop_duplicates()))
    pos = pd.Series(np.arange(len(cal), dtype='int64'), index=cal)
    out['market_session_id'] = out['date'].map(pos).astype('int64')
    return out


def _rolling(g: pd.Series, w: int, how: str='mean') -> pd.Series:
    r = g.rolling(w, min_periods=max(2, w//2))
    return getattr(r, how)()


def build_minimal_snapshot_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Causal fallback snapshot features for the research runner.

    The installed repository should prefer the richer existing build_matrix feature
    functions. This fallback exists so the candidate can be smoke-tested standalone
    and so a local run never silently invents future information.
    """
    req = {'code','date','open','high','low','close','volume'}
    missing = req - set(panel.columns)
    if missing:
        raise KeyError(f'missing OHLCV columns: {sorted(missing)}')
    f = add_market_session_id(panel).sort_values(['code','market_session_id']).reset_index(drop=True)
    out = f[['code','date','market_session_id']].copy()
    groups = f.groupby('code', sort=False)
    prev_close = groups['close'].shift(1)
    ret1 = f['close'] / prev_close - 1.0
    out['ret1'] = ret1.astype('float32')
    for lag in (2,5,10,20,60,120,250):
        prev = groups['close'].shift(lag)
        out[f'ret{lag}'] = (f['close']/prev - 1.0).astype('float32')
    tmp = f.copy(); tmp['_ret1'] = ret1
    for w in (5,10,20,60):
        out[f'vol{w}'] = tmp.groupby('code', sort=False)['_ret1'].transform(lambda s: _rolling(s,w,'std')).astype('float32')
    tr = pd.concat([
        f['high']-f['low'], (f['high']-prev_close).abs(), (f['low']-prev_close).abs()
    ], axis=1).max(axis=1)
    tmp['_tr'] = tr
    atr14 = tmp.groupby('code', sort=False)['_tr'].transform(lambda s: _rolling(s,14,'mean'))
    out['atr14_pct'] = (atr14/(f['close'].abs()+EPS)).astype('float32')
    for w in (5,20,60):
        ma = groups['volume'].transform(lambda s: _rolling(s,w,'mean'))
        out[f'vol_ma{w}'] = ma.astype('float32')
    out['vol_ratio_1_5'] = (f['volume']/(out['vol_ma5']+EPS)).astype('float32')
    out['vol_ratio_5_20'] = (out['vol_ma5']/(out['vol_ma20']+EPS)).astype('float32')
    out['vol_ratio_20_60'] = (out['vol_ma20']/(out['vol_ma60']+EPS)).astype('float32')
    for w in (60,120,250):
        hi = groups['high'].transform(lambda s: _rolling(s,w,'max'))
        lo = groups['low'].transform(lambda s: _rolling(s,w,'min'))
        out[f'pos_{w}'] = ((f['close']-lo)/(hi-lo+EPS)).astype('float32')
        out[f'dd_{w}'] = (f['close']/(hi+EPS)-1.0).astype('float32')
    low9 = groups['low'].transform(lambda s: s.rolling(9,min_periods=9).min())
    high9 = groups['high'].transform(lambda s: s.rolling(9,min_periods=9).max())
    rsv = 100*(f['close']-low9)/(high9-low9+EPS)
    k = rsv.groupby(f['code']).transform(lambda s: s.ewm(alpha=1/3, adjust=False).mean())
    d = k.groupby(f['code']).transform(lambda s: s.ewm(alpha=1/3, adjust=False).mean())
    j = 3*k-2*d
    out['kdj_k'] = k.astype('float32'); out['kdj_d'] = d.astype('float32'); out['kdj_j'] = j.astype('float32')
    out['kdj_k_minus_d'] = (k-d).astype('float32')
    out['kdj_k_chg5'] = k.groupby(f['code']).diff(5).astype('float32')
    return out


def build_snapshot_features(panel: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Use the repository's richer causal 82-feature builder when available."""
    try:
        from src.ml import build_matrix as bm
        frame = panel.sort_values(['code','date']).reset_index(drop=True).copy()
        bm.assert_sorted(frame)
        price = bm.add_price_features(frame)
        market = bm.add_market_features(frame)
        cross = bm.add_cross_sectional(frame, {**price, **market})
        out = add_market_session_id(frame)[['code','date','market_session_id']].copy()
        for part in (price, market, cross):
            for name, values in part.items():
                out[name] = np.asarray(values, dtype='float32')
        return out, 'repository_build_matrix_raw_features'
    except (ImportError, AttributeError):
        return build_minimal_snapshot_features(panel), 'minimal_fallback_features'


def add_volume_pressure(panel: pd.DataFrame, features: pd.DataFrame, windows=(5,20)) -> pd.DataFrame:
    p = add_market_session_id(panel).sort_values(['code','market_session_id']).reset_index(drop=True)
    out = features.copy()
    prev = p.groupby('code',sort=False)['close'].shift(1)
    ret = p['close']/prev - 1.0
    for w in windows:
        down_v = p['volume'].where(ret<0,0.0)
        up_v = p['volume'].where(ret>0,0.0)
        flat_v = p['volume'].where(ret==0,0.0)
        for name, s in [('down',down_v),('up',up_v),('flat',flat_v)]:
            x = s.groupby(p['code']).transform(lambda z: z.rolling(w,min_periods=w).sum())
            out[f'vp_{name}_vol_{w}'] = x.astype('float32')
        den = out[f'vp_down_vol_{w}'] + out[f'vp_up_vol_{w}']
        out[f'vp_pressure_{w}'] = ((out[f'vp_down_vol_{w}']-out[f'vp_up_vol_{w}'])/den.where(den>0)).astype('float32')
        n_down=(ret<0).astype(float).groupby(p['code']).transform(lambda z:z.rolling(w,min_periods=w).sum())
        n_up=(ret>0).astype(float).groupby(p['code']).transform(lambda z:z.rolling(w,min_periods=w).sum())
        out[f'vp_n_down_{w}']=n_down.astype('float32'); out[f'vp_n_up_{w}']=n_up.astype('float32')
        out[f'vp_one_sided_{w}']=(((n_down==0)|(n_up==0)) & den.notna()).astype('float32')
    return out


def add_kdj_path_features(features: pd.DataFrame) -> pd.DataFrame:
    out = features.sort_values(['code','market_session_id']).reset_index(drop=True).copy()
    low = ((out['kdj_k']<20)&(out['kdj_d']<20)).astype(float)
    for w in (21,63):
        out[f'kdj_low_occ_{w}'] = low.groupby(out['code']).transform(lambda s:s.rolling(w,min_periods=w).mean()).astype('float32')
    # consecutive low-zone streak ending at t
    streak=np.zeros(len(out),dtype='float32')
    for _, idx in out.groupby('code', sort=False).groups.items():
        c=0
        for i in idx:
            c=c+1 if low.iloc[i]>0 else 0
            streak[i]=c
    out['kdj_low_streak']=streak
    return out
