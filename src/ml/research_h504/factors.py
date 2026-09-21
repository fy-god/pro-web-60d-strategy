from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    out = num / den.where(den.abs() > EPS)
    return out.replace([np.inf, -np.inf], np.nan)


def volume_impact_recovery(
    frame: pd.DataFrame,
    *,
    block: int = 10,
    atr_window: int = 14,
    volume_window: int = 20,
    min_up: int = 2,
    min_down: int = 2,
) -> pd.DataFrame:
    """Causal Volume-Impact Recovery (VIR) candidate.

    For each stock and t, compare non-overlapping blocks [t-19,t-10] and
    [t-9,t].  Price impact is |log return| in units of *previous-session* ATR,
    divided by relative volume whose baseline excludes the current session.
    The factor is valid only when the last 20 observed stock rows are also 20
    consecutive market_session_id values; a missing session is not stitched.
    """
    req = {"code", "date", "high", "low", "close", "volume", "market_session_id"}
    missing = req - set(frame.columns)
    if missing:
        raise KeyError(f"missing VIR columns: {sorted(missing)}")
    if block <= 1:
        raise ValueError("block must be >1")

    f = frame.sort_values(["code", "market_session_id"]).copy()
    outputs = []
    for code, g in f.groupby("code", sort=False):
        g = g.copy()
        prev_close = g["close"].shift(1)
        tr = pd.concat([
            g["high"] - g["low"],
            (g["high"] - prev_close).abs(),
            (g["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        # ATR known at s-1 and volume baseline known before observing V_s.
        atr_prev = tr.rolling(atr_window, min_periods=atr_window).mean().shift(1)
        atr_pct_prev = _safe_ratio(atr_prev, prev_close)
        vol_base = g["volume"].rolling(volume_window, min_periods=volume_window).mean().shift(1)
        rel_vol = _safe_ratio(g["volume"], vol_base)
        logret = np.log(_safe_ratio(g["close"], prev_close))
        z = _safe_ratio(logret, atr_pct_prev)

        up = z.clip(lower=0)
        down = (-z).clip(lower=0)
        up_q = rel_vol.where(z > 0, 0.0)
        down_q = rel_vol.where(z < 0, 0.0)
        up_n = (z > 0).astype(float)
        down_n = (z < 0).astype(float)

        def roll_recent(s):
            return s.rolling(block, min_periods=block).sum()

        def roll_prior(s):
            return s.shift(block).rolling(block, min_periods=block).sum()

        recent_up_num, prior_up_num = roll_recent(up), roll_prior(up)
        recent_dn_num, prior_dn_num = roll_recent(down), roll_prior(down)
        recent_up_den, prior_up_den = roll_recent(up_q), roll_prior(up_q)
        recent_dn_den, prior_dn_den = roll_recent(down_q), roll_prior(down_q)
        recent_n_up, prior_n_up = roll_recent(up_n), roll_prior(up_n)
        recent_n_dn, prior_n_dn = roll_recent(down_n), roll_prior(down_n)

        recent_up = _safe_ratio(recent_up_num, recent_up_den)
        recent_dn = _safe_ratio(recent_dn_num, recent_dn_den)
        prior_up = _safe_ratio(prior_up_num, prior_up_den)
        prior_dn = _safe_ratio(prior_dn_num, prior_dn_den)

        asym_recent = np.log((recent_up + EPS) / (recent_dn + EPS))
        asym_prior = np.log((prior_up + EPS) / (prior_dn + EPS))
        vir = asym_recent - asym_prior

        # Price-only control: set each effective relative-volume weight to 1.
        recent_up_novol = _safe_ratio(recent_up_num, recent_n_up)
        recent_dn_novol = _safe_ratio(recent_dn_num, recent_n_dn)
        prior_up_novol = _safe_ratio(prior_up_num, prior_n_up)
        prior_dn_novol = _safe_ratio(prior_dn_num, prior_n_dn)
        vir_novol = (
            np.log((recent_up_novol + EPS) / (recent_dn_novol + EPS))
            - np.log((prior_up_novol + EPS) / (prior_dn_novol + EPS))
        )

        sid = g["market_session_id"].astype(float)
        # Every transition in the 20-row window must advance by exactly one
        # independent market session.  Checking only endpoint span is not enough:
        # a duplicate session plus a compensating two-session jump has the same
        # span but is still discontinuous.
        step_ok = sid.diff().eq(1.0).astype(float)
        consecutive_20 = (
            step_ok.rolling(2 * block - 1, min_periods=2 * block - 1).sum()
            .eq(2 * block - 1)
        )
        balanced = (
            (recent_n_up >= min_up) & (recent_n_dn >= min_down)
            & (prior_n_up >= min_up) & (prior_n_dn >= min_down)
        )
        valid = consecutive_20 & balanced & vir.notna()
        one_sided = consecutive_20 & ~balanced

        g["vir"] = vir.where(valid)
        g["vir_novol"] = vir_novol.where(consecutive_20 & balanced)
        g["vir_asym_recent"] = asym_recent.where(consecutive_20 & balanced)
        g["vir_asym_prior"] = asym_prior.where(consecutive_20 & balanced)
        g["vir_up_impact_recent"] = recent_up.where(consecutive_20)
        g["vir_down_impact_recent"] = recent_dn.where(consecutive_20)
        g["vir_up_impact_prior"] = prior_up.where(consecutive_20)
        g["vir_down_impact_prior"] = prior_dn.where(consecutive_20)
        g["vir_recent_n_up"] = recent_n_up
        g["vir_recent_n_down"] = recent_n_dn
        g["vir_prior_n_up"] = prior_n_up
        g["vir_prior_n_down"] = prior_n_dn
        g["vir_coverage20"] = consecutive_20.astype(float)
        g["vir_one_sided"] = one_sided.astype(float)
        outputs.append(g)
    return pd.concat(outputs, ignore_index=True).sort_values(["code", "date"]).reset_index(drop=True)
