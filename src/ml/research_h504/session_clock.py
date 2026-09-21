from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def normalize_calendar(calendar: Iterable) -> pd.DatetimeIndex:
    if isinstance(calendar, pd.DataFrame):
        if "date" not in calendar.columns:
            raise KeyError("calendar dataframe requires date column")
        values = calendar["date"]
    else:
        values = list(calendar)
    cal = pd.DatetimeIndex(pd.to_datetime(values, errors="raise"))
    if cal.hasnans:
        raise ValueError("calendar contains NaT")
    if cal.duplicated().any():
        # A market-session clock is one position per market date; duplicate
        # dates usually mean a panel was passed instead of a calendar.
        cal = pd.DatetimeIndex(cal.drop_duplicates())
    cal = pd.DatetimeIndex(sorted(cal))
    if len(cal) == 0:
        raise ValueError("calendar is empty")
    return cal


def dedupe_signals_market_calendar(
    signals: pd.DataFrame,
    *,
    calendar: Iterable,
    cooldown: int = 60,
) -> pd.DataFrame:
    """Collapse same-stock events using an independent market-session clock.

    Unlike the product ``labels.dedupe_signals`` this function does NOT build the
    clock from sparse signal dates. A signal date absent from the supplied market
    calendar is a contract error and fails closed instead of silently falling
    back to row rank.
    """
    if cooldown < 0:
        raise ValueError("cooldown must be >= 0")
    if signals.empty:
        return signals.copy()
    missing = {"code", "date"} - set(signals.columns)
    if missing:
        raise KeyError(f"signals missing columns: {sorted(missing)}")

    cal = normalize_calendar(calendar)
    pos = {pd.Timestamp(d): i for i, d in enumerate(cal)}
    out = signals.copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise")
    unknown = sorted(set(out["date"]) - set(pos))
    if unknown:
        raise ValueError(f"signal dates absent from market calendar; first={unknown[:3]}")

    out = out.sort_values(["code", "date"], kind="mergesort").copy()
    positions = out["date"].map(pos).to_numpy(dtype=np.int64)
    codes = out["code"].astype(str).to_numpy()
    keep = np.zeros(len(out), dtype=bool)

    start = 0
    for i in range(1, len(out) + 1):
        if i == len(out) or codes[i] != codes[start]:
            last = None
            for j in range(start, i):
                if last is None or positions[j] - last >= cooldown:
                    keep[j] = True
                    last = positions[j]
            start = i
    return out.loc[keep].copy()
