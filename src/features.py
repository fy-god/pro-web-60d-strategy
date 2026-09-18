"""Causal feature computation over the daily panel.

Two rules are enforced everywhere in this module, because both were identified
as defects in the project's own research history:

1. **Continuous KDJ.** The K/D recursions run over the stock's whole observed
   bar sequence, never reset on a calendar year or on a 40-bar card boundary.
   Earlier versions reset ``K = D = 50`` every 40 bars, which made an
   already-extended stock look oversold again.

2. **No fabricated bars.** Suspended sessions are simply absent from the source
   data. We never forward-fill or invent a bar for a non-trading day, because
   that previously let KDJ drift while a stock was halted and produced signals
   on days the stock could not be traded.

Every function here is *causal*: the value at bar ``t`` depends only on bars
``<= t``. Forward-looking quantities live exclusively in :mod:`src.labels`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12


def _per_code(frame: pd.DataFrame):
    """Group a panel by stock code, preserving chronological order."""
    return frame.sort_values(["code", "date"]).groupby("code", sort=False)


# ---------------------------------------------------------------------------
# KDJ
# ---------------------------------------------------------------------------
def kdj(
    frame: pd.DataFrame,
    n: int = 9,
    k_smooth: float = 1.0 / 3.0,
    d_smooth: float = 1.0 / 3.0,
) -> pd.DataFrame:
    """Continuous KDJ over each stock's full bar history.

    ``RSV`` uses the rolling ``n``-bar high/low; when a window is flat the
    denominator is zero and RSV is defined as 50 (neutral) rather than NaN.
    """
    out = frame.copy()
    grouped = _per_code(out)

    low_n = grouped["low"].transform(lambda s: s.rolling(n, min_periods=1).min())
    high_n = grouped["high"].transform(lambda s: s.rolling(n, min_periods=1).max())

    span = (high_n - low_n).to_numpy(dtype="float64")
    close = out["close"].to_numpy(dtype="float64")
    low_nv = low_n.to_numpy(dtype="float64")

    rsv = np.full(len(out), 50.0, dtype="float64")
    valid = span > EPS
    rsv[valid] = (close[valid] - low_nv[valid]) / span[valid] * 100.0

    # Recursive smoothing, restarted per stock but never within a stock.
    k = np.empty(len(out), dtype="float64")
    d = np.empty(len(out), dtype="float64")
    k_prev, d_prev = 50.0, 50.0
    codes = out["code"].to_numpy()
    for i in range(len(out)):
        if i > 0 and codes[i] != codes[i - 1]:
            k_prev, d_prev = 50.0, 50.0
        k_prev = (1.0 - k_smooth) * k_prev + k_smooth * rsv[i]
        d_prev = (1.0 - d_smooth) * d_prev + d_smooth * k_prev
        k[i], d[i] = k_prev, d_prev

    out["kdj_k"] = k
    out["kdj_d"] = d
    out["kdj_j"] = 3.0 * k - 2.0 * d
    return out


# ---------------------------------------------------------------------------
# Price / volume context
# ---------------------------------------------------------------------------
def add_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach rolling context columns used by the low-zone strategies."""
    out = frame.copy()
    g = _per_code(out)

    for window in (5, 10, 20, 60, 120, 250):
        out[f"ret_{window}"] = g["close"].transform(
            lambda s, w=window: s / s.shift(w) - 1.0
        )
        out[f"high_{window}"] = g["high"].transform(
            lambda s, w=window: s.rolling(w, min_periods=1).max()
        )
        out[f"low_{window}"] = g["low"].transform(
            lambda s, w=window: s.rolling(w, min_periods=1).min()
        )
        out[f"ma_{window}"] = g["close"].transform(
            lambda s, w=window: s.rolling(w, min_periods=1).mean()
        )
        out[f"vol_ma_{window}"] = g["volume"].transform(
            lambda s, w=window: s.rolling(w, min_periods=1).mean()
        )

    # Position of close inside its own rolling range: 0 = at the low, 1 = at the high.
    for window in (60, 120, 250):
        span = (out[f"high_{window}"] - out[f"low_{window}"]).to_numpy(dtype="float64")
        pos = np.full(len(out), 0.5, dtype="float64")
        valid = span > EPS
        pos[valid] = (
            out["close"].to_numpy(dtype="float64")[valid]
            - out[f"low_{window}"].to_numpy(dtype="float64")[valid]
        ) / span[valid]
        out[f"pos_{window}"] = pos

    # Drawdown from the rolling high, and the multi-year position that the
    # research record repeatedly flags as the missing piece for KDJ-only models.
    out["dd_120"] = out["close"] / (out["high_120"] + EPS) - 1.0
    out["dd_250"] = out["close"] / (out["high_250"] + EPS) - 1.0
    out["vol_ratio_5_20"] = out["vol_ma_5"] / (out["vol_ma_20"] + EPS)

    # ``volume_ratio`` in the Web Pro indicator contract is NOT vol_ma_5/vol_ma_20:
    # the published primitive compares the last 5 sessions against the 16
    # sessions *before* them, i.e. bars[-21:-5], leaving a deliberate gap so the
    # two windows never overlap and the ratio is not self-diluting.
    prior = g["volume"].transform(lambda s: s.shift(5).rolling(16, min_periods=1).mean())
    out["volume_ratio"] = out["vol_ma_5"] / (prior + EPS)

    out["atr_14"] = g.apply(
        lambda d: _atr(d, 14), include_groups=False
    ).reset_index(level=0, drop=True).sort_index()

    return out


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev_close = frame["close"].shift(1)
    tr = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


def prepare(panel: pd.DataFrame) -> pd.DataFrame:
    """Full causal feature build: KDJ + context + turnover proxy.

    Notes
    -----
    ``turnover`` is **not present** in any local OHLCV source: every Tencent
    daily file in ``D:/xm`` carries an empty ``amount`` column, and the
    original project explicitly refused to fabricate it ("成交额字段为空，因此
    没有把成交额伪装成换手率" — ``volume_causal_filter_search_86.py``).

    We therefore expose a documented proxy, ``turnover := volume``, and flag the
    consequence per strategy. Only ONE of the five turnover-consuming strategies
    reads the *level* of turnover (``leader_momentum``); the other four read
    scale-invariant ratios (a 5/20-session mean ratio, or a coefficient of
    variation) and are therefore unaffected by the substitution.
    ``tests/test_engine.py`` pins this.

    This paragraph said "two ... the other three", which contradicted both
    ``README.md`` and the test: the scale-invariance test enumerates exactly four
    strategies, leaving one level reader. The count matters because it is the blast
    radius of the single largest documented data limitation in the project -- an
    understated radius would suggest the ``turnover`` proxy is safer than it is.
    """
    out = add_context(kdj(panel))
    out["turnover"] = out["volume"]
    out["turnover_is_proxy"] = True
    return out
