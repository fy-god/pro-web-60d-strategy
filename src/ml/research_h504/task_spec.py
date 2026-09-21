"""Session-clock outcome oracle, isolated from the legacy High/bar-clock task."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class H504TaskSpec:
    horizon_market_sessions: int = 504
    target_multiple: float = 4.0
    risk_floor_multiple: float = 0.8
    entry_field: str = 'open'
    target_field: str = 'close'
    risk_field: str = 'low'
    missing_post_entry_policy: str = 'unknown'
    price_basis: str = 'same_basis_required'
    risk_priority_same_session: bool = True
    training_queue: str = 'fixed_full_followup_deadline'

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_calendar(calendar: Iterable[pd.Timestamp]) -> pd.DatetimeIndex:
    cal = pd.DatetimeIndex(pd.to_datetime(list(calendar), errors='raise'))
    if cal.hasnans or not len(cal):
        raise ValueError('calendar must be nonempty and contain no NaT')
    return pd.DatetimeIndex(sorted(cal.drop_duplicates()))


def market_calendar(frame: pd.DataFrame) -> pd.DatetimeIndex:
    """Observed-union fallback for synthetic tests; real CLI requires --calendar."""
    return normalize_calendar(frame['date'])


def label_h504_candidates(panel: pd.DataFrame, candidates: pd.DataFrame | None = None,
                          *, spec: H504TaskSpec | None = None,
                          calendar: Iterable[pd.Timestamp] | None = None) -> pd.DataFrame:
    """Risk-first prices on t+1..t+H. Missing t+1 open never rolls forward.

    label_known_at is the actual event time. Conservative BCE training waits for
    the full registered deadline even after an early resolved success or risk.
    Supply an independently versioned calendar limited to the observed as-of date.
    Array alignment is done once per stock; no label-dependent candidate filtering.
    """
    spec = spec or H504TaskSpec()
    H = spec.horizon_market_sessions
    if H < 1 or spec.target_multiple <= 1 or not 0 < spec.risk_floor_multiple <= 1:
        raise ValueError('invalid horizon/target/risk parameters')
    if not spec.risk_priority_same_session or spec.missing_post_entry_policy != 'unknown':
        raise ValueError('unsupported TaskSpec policy')
    required = {'code','date',spec.entry_field,spec.target_field,spec.risk_field}
    if not required.issubset(panel):
        raise KeyError(f'missing price columns: {sorted(required-set(panel))}')
    p = panel.copy(); p['code'] = p['code'].astype(str); p['date'] = pd.to_datetime(p['date'])
    if p[['code','date']].isna().any().any() or p.duplicated(['code','date']).any():
        raise ValueError('null or duplicate panel keys')
    cal = normalize_calendar(calendar) if calendar is not None else market_calendar(p)
    positions = {d:i for i,d in enumerate(cal)}
    c = (p[['code','date']] if candidates is None else candidates).copy()
    if not {'code','date'}.issubset(c):
        raise KeyError('candidates require code/date')
    c['code'] = c['code'].astype(str); c['date'] = pd.to_datetime(c['date'])
    if c.duplicated(['code','date']).any():
        raise ValueError('duplicate candidate keys')
    if 'candidate_id' in c and (c.candidate_id.isna().any() or c.candidate_id.duplicated().any()):
        raise ValueError('null or duplicate candidate_id')
    arrays = {}
    for code, group in p.groupby('code', sort=False):
        g = group.set_index('date')
        aligned = g.reindex(cal)
        values = aligned[[spec.entry_field,spec.risk_field,spec.target_field]].apply(pd.to_numeric,errors='coerce').to_numpy(float)
        arrays[code] = (values, cal.isin(g.index))
    rows = []
    for rec in c.to_dict('records'):
        code, date = rec['code'], pd.Timestamp(rec['date'])
        r = dict(candidate_id=rec.get('candidate_id',f'{code}|{date.date().isoformat()}'),
                 code=code, signal_date=date, entry_session=pd.NaT, deadline=pd.NaT,
                 label_end=pd.NaT, entry_open=np.nan, target_price=np.nan, risk_floor=np.nan,
                 terminal_session=pd.NaT, label_known_at=pd.NaT, training_eligible_at=pd.NaT,
                 training_eligible=False, outcome_class='invalid_candidate', label_joint=np.nan,
                 label_resolved=False, bars_scanned=0, first_missing_session=pd.NaT)
        rows.append(r)
        if date not in positions:
            continue
        i = positions[date]
        if i+1 >= len(cal):
            r['outcome_class'] = 'pending_entry_calendar'; continue
        entry_day = cal[i+1]; r['entry_session'] = entry_day
        mature = i+H < len(cal)
        if mature:
            r['deadline'] = r['training_eligible_at'] = cal[i+H]
        stock = arrays.get(code)
        entry = stock[0][i+1,0] if stock is not None else np.nan
        if not np.isfinite(entry) or entry <= 0:
            r.update(outcome_class='no_entry',label_known_at=entry_day,label_end=entry_day); continue
        target, floor = float(entry*spec.target_multiple), float(entry*spec.risk_floor_multiple)
        r.update(entry_open=float(entry),target_price=target,risk_floor=floor)
        stop = min(i+H+1,len(cal))
        prices, present = stock
        low, close = prices[i+1:stop,1],prices[i+1:stop,2]
        valid = np.isfinite(low)&(low>0)&np.isfinite(close)&(close>0)
        risk, goal = valid&(low<floor), valid&(close>target)
        event = np.flatnonzero((~valid)|risk|goal)
        if len(event):
            j = int(event[0]); day = cal[i+1+j]
            r['bars_scanned'] = j + int(valid[j])
            r['label_known_at'] = r['label_end'] = day
            if not valid[j]:
                r['first_missing_session'] = day
                r['outcome_class'] = 'unknown_missing_price' if present[i+1+j] else 'unknown_missing_bar'
            else:
                r.update(terminal_session=day,outcome_class='risk' if risk[j] else 'success',
                         label_joint=0.0 if risk[j] else 1.0,label_resolved=True,training_eligible=bool(mature))
        elif mature:
            day = cal[i+H]
            r.update(terminal_session=day,label_known_at=day,label_end=day,outcome_class='timeout',
                     label_joint=0.0,label_resolved=True,training_eligible=True,bars_scanned=H)
        else:
            r.update(outcome_class='pending_maturity',bars_scanned=len(low))
    return pd.DataFrame(rows)
