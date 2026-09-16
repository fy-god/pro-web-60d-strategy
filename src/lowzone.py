"""The 60-day low-zone strategy family (V00-V08 lineage).

Re-implements the documented causal layer stack from the project's own
``09_bull_lowzone_model/v1_bull_lowzone_60d.py`` and exposes each numbered
version as a separately named, separately scored strategy.

The five nested layers are **causal**: every term reads the current bar's OHLCV
and prior bars only. ``anchor_date``, ``future_*`` and any forward high/low are
labels or audit columns and never appear here.

Nested tiers (each strictly implies the one below)
--------------------------------------------------
L1 ``base``          low zone, deep drawdown, close off the low
L2 ``+stabilization`` range contracting, 5-day return not collapsing
L3 ``+reversal``     up close, higher close, lower wick, strong close location
L4 ``+volume_ok``    volume not expanding into the low, current volume present
L5 ``+trend_turn``   EMA20 not still falling, close back above EMA5

Version roster (each is a frozen, named configuration — not a re-tune)
---------------------------------------------------------------------
V00  all-tier baseline: any tier >= 1, no model
V01  L3 rule gate only
V02  L5 rule gate only
V03  gain/loss score model, tier >= 1
V06  competitive score (gain - alpha*loss), tier >= 3
V07  V06 with each year's own threshold (in-sample fit, labelled as such)
V08  first chronological signal per stock/year (the documented PASS variant)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

LOOKBACK = 60
EPS = 1e-12


def _safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    b = np.asarray(b, dtype="float64")
    return np.asarray(a, dtype="float64") / np.where(np.abs(b) < EPS, np.nan, b)


def _lagged(values: np.ndarray, lag: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype="float64")
    if lag < len(values):
        out[lag:] = values[: len(values) - lag]
    return out


def _adx(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14
) -> tuple[np.ndarray, np.ndarray]:
    """Wilder ADX and the DI spread, matching the source implementation."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    prior = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prior).abs(), (low - prior).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    plus_di = 100 * pd.Series(plus_dm, index=high.index).ewm(
        alpha=1 / window, adjust=False, min_periods=window
    ).mean() / atr.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=high.index).ewm(
        alpha=1 / window, adjust=False, min_periods=window
    ).mean() / atr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return adx.to_numpy("float64"), (plus_di - minus_di).to_numpy("float64")


FEATURE_COLUMNS = [
    "ret1", "ret3", "ret5", "ret10", "ret20", "ret60",
    "low_gap60", "close_gap60", "drawdown60",
    "close_position", "lower_wick", "body_ratio", "range_pct",
    "range_contract5", "range_contract20", "atr_pct",
    "vol_ratio20", "vol_contract5", "vol_contract10", "vol_expand", "down_vol_ratio5",
    "obv_slope10", "ema5_gap", "ema10_gap", "ema20_gap", "ema60_gap",
    "ema20_slope10", "ema60_slope20", "rsi2", "rsi14", "adx14", "di_spread",
]


def build_layers(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute the causal layer features and nested L1-L5 tier per stock."""
    frames = []
    for code, group in panel.sort_values(["code", "date"]).groupby("code", sort=False):
        g = group.reset_index(drop=True)
        close = g["close"].to_numpy("float64")
        low = g["low"].to_numpy("float64")
        high = g["high"].to_numpy("float64")
        open_ = g["open"].to_numpy("float64")
        volume = g["volume"].to_numpy("float64")
        prior = _lagged(close, 1)
        day_range = np.maximum(high - low, 1e-12)

        roll_low = pd.Series(low).rolling(LOOKBACK, min_periods=LOOKBACK).min().to_numpy("float64")
        roll_high = pd.Series(high).rolling(LOOKBACK, min_periods=LOOKBACK).max().to_numpy("float64")
        close_position = (close - low) / day_range
        lower_wick = (np.minimum(open_, close) - low) / day_range
        range_pct = day_range / np.maximum(close, EPS)

        vol20 = pd.Series(volume).rolling(20, min_periods=20).mean().to_numpy("float64")
        vol5 = pd.Series(volume).rolling(5, min_periods=5).mean().to_numpy("float64")
        vol10 = pd.Series(volume).rolling(10, min_periods=10).mean().to_numpy("float64")
        range5 = pd.Series(range_pct).rolling(5, min_periods=5).mean().to_numpy("float64")
        range20 = pd.Series(range_pct).rolling(20, min_periods=20).mean().to_numpy("float64")
        range60 = pd.Series(range_pct).rolling(60, min_periods=60).mean().to_numpy("float64")

        tr = np.maximum.reduce([high - low, np.abs(high - prior), np.abs(low - prior)])
        atr14 = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy("float64")
        ema = {
            w: pd.Series(close).ewm(span=w, adjust=False, min_periods=w).mean().to_numpy("float64")
            for w in (5, 10, 20, 60)
        }

        signed = np.nan_to_num(np.sign(close - prior), nan=0.0)
        obv = np.cumsum(signed * volume)
        obv_prev = _lagged(obv, 10)
        down = np.where(close < prior, volume, np.nan)
        up = np.where(close >= prior, volume, np.nan)
        down5 = pd.Series(down).rolling(5, min_periods=3).mean().to_numpy("float64")
        up5 = pd.Series(up).rolling(5, min_periods=3).mean().to_numpy("float64")

        delta = np.diff(close, prepend=np.nan)
        gains = np.maximum(delta, 0.0)
        losses = np.maximum(-delta, 0.0)
        rsi2 = 100.0 - 100.0 / (1.0 + _safe_div(
            pd.Series(gains).rolling(2, min_periods=2).mean().to_numpy("float64"),
            pd.Series(losses).rolling(2, min_periods=2).mean().to_numpy("float64")))
        rsi14 = 100.0 - 100.0 / (1.0 + _safe_div(
            pd.Series(gains).rolling(14, min_periods=14).mean().to_numpy("float64"),
            pd.Series(losses).rolling(14, min_periods=14).mean().to_numpy("float64")))
        adx14, di_spread = _adx(g["high"], g["low"], g["close"], 14)

        low_gap = _safe_div(low, roll_low) - 1.0
        close_gap = _safe_div(close, roll_low) - 1.0
        drawdown = _safe_div(close, roll_high) - 1.0

        base = (low_gap <= 0.15) & (close_gap <= 0.28) & (drawdown <= -0.15) & (close_position >= 0.30)
        stabilization = (pd.Series(close).pct_change(5).to_numpy("float64") > -0.12) & (range5 <= range20 * 1.25)
        reversal = (close >= open_) & (close > prior) & (lower_wick >= 0.12) & (close_position >= 0.45)
        volume_ok = (_safe_div(vol5, vol20) <= 1.35) & (_safe_div(volume, vol5) >= 0.85)
        trend_turn = (_safe_div(ema[20], _lagged(ema[20], 10)) - 1.0 >= -0.03) & (close >= ema[5])

        tier = np.zeros(len(g), dtype=int)
        tier[base] = 1
        tier[base & stabilization] = 2
        tier[base & stabilization & reversal] = 3
        tier[base & stabilization & reversal & volume_ok] = 4
        tier[base & stabilization & reversal & volume_ok & trend_turn] = 5

        frames.append(pd.DataFrame({
            "code": code, "date": g["date"].to_numpy(),
            "open": open_, "high": high, "low": low, "close": close, "volume": volume,
            "ret1": _safe_div(close, prior) - 1.0,
            "ret3": _safe_div(close, _lagged(close, 3)) - 1.0,
            "ret5": _safe_div(close, _lagged(close, 5)) - 1.0,
            "ret10": _safe_div(close, _lagged(close, 10)) - 1.0,
            "ret20": _safe_div(close, _lagged(close, 20)) - 1.0,
            "ret60": _safe_div(close, _lagged(close, 60)) - 1.0,
            "low_gap60": low_gap, "close_gap60": close_gap, "drawdown60": drawdown,
            "close_position": close_position, "lower_wick": lower_wick,
            "body_ratio": np.abs(close - open_) / day_range, "range_pct": range_pct,
            "range_contract5": _safe_div(range5, range20),
            "range_contract20": _safe_div(range20, range60),
            "atr_pct": _safe_div(atr14, close), "vol_ratio20": _safe_div(volume, vol20),
            "vol_contract5": _safe_div(vol5, vol20), "vol_contract10": _safe_div(vol10, vol20),
            "vol_expand": _safe_div(volume, vol5), "down_vol_ratio5": _safe_div(down5, up5),
            "obv_slope10": _safe_div(obv - obv_prev, np.maximum(np.abs(obv_prev), 1.0)),
            "ema5_gap": _safe_div(close, ema[5]) - 1.0,
            "ema10_gap": _safe_div(close, ema[10]) - 1.0,
            "ema20_gap": _safe_div(close, ema[20]) - 1.0,
            "ema60_gap": _safe_div(close, ema[60]) - 1.0,
            "ema20_slope10": _safe_div(ema[20], _lagged(ema[20], 10)) - 1.0,
            "ema60_slope20": _safe_div(ema[60], _lagged(ema[60], 20)) - 1.0,
            "rsi2": rsi2, "rsi14": rsi14, "adx14": adx14, "di_spread": di_spread,
            "stabilization": stabilization.astype(int), "recall_tier": tier,
        }))
    out = pd.concat(frames, ignore_index=True)
    out["year"] = out["date"].dt.year
    return out.sort_values(["code", "date"]).reset_index(drop=True)


@dataclass(frozen=True)
class LowZoneVersion:
    """One frozen, named configuration of the 60-day low-zone family."""

    version: str
    display_name: str
    min_tier: int
    model: str                    # "rule" | "gain" | "competitive"
    per_year_threshold: bool = False
    first_signal_per_year: bool = False
    threshold: float = 0.5
    alpha: float = 1.0
    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)


VERSIONS: tuple[LowZoneVersion, ...] = (
    LowZoneVersion(
        "V00", "V00 Low-Zone Base (any tier)", min_tier=1, model="rule",
        notes="Any causal low-zone candidate, no model and no score. This is the "
              "family's natural baseline: it measures how often a stock merely "
              "sitting in a 60-day low zone goes on to 4x.",
    ),
    LowZoneVersion(
        "V01", "V01 L3 Reversal Rule", min_tier=3, model="rule",
        notes="Requires the reversal layer: up close, higher close, lower wick.",
    ),
    LowZoneVersion(
        "V02", "V02 L5 Full Stack Rule", min_tier=5, model="rule",
        notes="Requires all five causal layers including volume and trend turn.",
    ),
    LowZoneVersion(
        "V03", "V03 Gain Model (tier>=1)", min_tier=1, model="gain",
        notes="Gain-probability model only, no loss model to subtract.",
    ),
    LowZoneVersion(
        "V06", "V06 Competitive Gain-minus-Loss", min_tier=3, model="competitive",
        alpha=1.0,
        notes="Separate gain and loss models; score = gain - alpha*loss, as in "
              "the V06 round record.",
    ),
    LowZoneVersion(
        "V07", "V07 Competitive, per-year threshold", min_tier=3, model="competitive",
        alpha=1.0, per_year_threshold=True,
        notes="Each year selects its own threshold on that year's labels. This is "
              "an in-sample research fit and is labelled as such, never as a "
              "cross-year prediction.",
    ),
    LowZoneVersion(
        "V08", "V08 First Signal per Stock-Year", min_tier=3, model="competitive",
        alpha=1.0, per_year_threshold=True, first_signal_per_year=True,
        notes="Adds the first-chronological-signal-per-stock-year policy. This is "
              "the variant the project's own record marks PASS_YEARWISE_IN_SAMPLE, "
              "and the record itself warns it is not a frozen cross-year model.",
    ),
)


def make_gain_model(seed: int = 20260916) -> Any:
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.06, max_leaf_nodes=15,
        l2_regularization=1.0, random_state=seed,
    )


def make_loss_model(seed: int = 20260917) -> Any:
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        max_iter=180, learning_rate=0.06, max_leaf_nodes=15,
        l2_regularization=1.0, random_state=seed,
    )
