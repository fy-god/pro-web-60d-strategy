"""Outcome labelling and hit-rate accounting.

This module is where the project's own documented evaluation defects are
avoided. Each rule below encodes a specific correction from the research
history of this strategy family.

Label definitions
-----------------
``forward_max_return``
    ``max(high[t+1 .. t+H]) / open[t+1] - 1``. Entry is the *next* session's
    open, because a signal is only actionable after the signal bar closes.

``bull_4x``
    ``forward_max_return > 3.0`` i.e. price ``> 4x`` entry. Strictly greater
    than, not ``>=``: the earlier code mixed the two and mislabelled bars that
    landed exactly on 4x.

``strict_low``
    ``min(low[t+1 .. t_hit]) / open[t+1] >= 0.80`` where ``t_hit`` is the first
    bar that reaches the target. "Minimum drawdown of at most 20% before the
    first 4x touch."

Accounting rules
----------------
* **No fabricated outcomes.** If fewer than ``H`` future bars exist, the label
  is ``NaN`` (right-censored), never 0. Right-censored rows are excluded from
  every denominator and reported separately.
* **Event deduplication.** Overlapping signals on one stock inside a cooldown
  window collapse to a single event, so a stock that scores high for 40
  consecutive days counts once, not forty times.
* **Independent-event denominators.** Alongside raw signal precision we report
  distinct-stock and distinct-market-date counts, because the earlier "13
  signals" turned out to be 3 distinct market dates and one date carried 7 of
  the 9 hits.

Implementation note
-------------------
Forward windows are computed with an explicit offset sweep rather than
``rolling``, because a rolling window looks *backward* and silently produces
NaN for the first ``H`` bars of every stock. The sweep is fully vectorised:
``H`` passes of NumPy over the panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HORIZON_DEFAULT = 60
TARGET_MULTIPLE_DEFAULT = 4.0
STRICT_LOW_RATIO_DEFAULT = 0.80
EPS = 1e-12

# The two evaluation regimes this project verifies strategies under. They come
# from the two source families and must never be mixed, because a 10-session
# +30% target and a 60-session 4x target have wildly different base rates and
# the same precision number means completely different things in each.
REGIMES = {
    # name: (horizon_sessions, target_return, strict_low_ratio)
    "webpro": (10, 0.30, 0.80),   # the Web Pro card contract
    "low60": (60, 3.00, 0.80),    # 60-day low-zone family, 4x target
    "low504": (504, 3.00, 0.80),  # the frozen spec from the research record
}


def forward_outcomes_multi(
    frame: pd.DataFrame, regimes: dict | None = None
) -> pd.DataFrame:
    """Compute labels for every regime and merge them side by side.

    Columns are suffixed with the regime name, e.g. ``label_bull__webpro``.
    Entry price and session alignment are shared, so only one pass per regime
    is needed and the columns stay directly comparable.
    """
    regimes = regimes or REGIMES
    base = frame.sort_values(["code", "date"]).reset_index(drop=True)
    out = base.copy()
    keep_shared = True

    for name, (horizon, target_return, low_ratio) in regimes.items():
        labelled = forward_outcomes(
            base,
            horizon=horizon,
            target_return=target_return,
            strict_low_ratio=low_ratio,
        )
        if keep_shared:
            # entry_open / future_bars are horizon-independent only for the
            # shortest regime, so each regime keeps its own suffixed copy.
            keep_shared = False
        for column in (
            "forward_max_return", "forward_min_return", "bars_to_target",
            "label_bull", "label_strict_low", "label_joint", "label_resolved",
            "future_bars",
        ):
            out[f"{column}__{name}"] = labelled[column].to_numpy()
        out[f"entry_open__{name}"] = labelled["entry_open"].to_numpy()
        out[f"horizon__{name}"] = horizon
    return out


def forward_outcomes(
    frame: pd.DataFrame,
    horizon: int = HORIZON_DEFAULT,
    target_multiple: float = TARGET_MULTIPLE_DEFAULT,
    strict_low_ratio: float = STRICT_LOW_RATIO_DEFAULT,
    target_return: float | None = None,
) -> pd.DataFrame:
    """Attach forward-looking label columns to a prepared feature panel.

    ``target_return`` (e.g. ``0.30`` for +30%) takes precedence over
    ``target_multiple`` when supplied, so a regime can be expressed either as a
    multiple of entry (the low-zone family) or as a percentage gain (Web Pro).
    """
    out = frame.sort_values(["code", "date"]).reset_index(drop=True)

    codes = out["code"].to_numpy()
    highs = out["high"].to_numpy(dtype="float64")
    lows = out["low"].to_numpy(dtype="float64")
    opens = out["open"].to_numpy(dtype="float64")
    n = len(out)

    # Entry price: the next session's open, but only within the same stock.
    entry = np.full(n, np.nan, dtype="float64")
    entry[:-1] = opens[1:]
    same_next = np.zeros(n, dtype=bool)
    same_next[:-1] = codes[1:] == codes[:-1]
    entry[~same_next] = np.nan

    if target_return is not None:
        target = entry * (1.0 + target_return)
        bull_expression = f"forward_max_return > {target_return}"
    else:
        target = entry * target_multiple
        bull_expression = f"forward_max_return > {target_multiple - 1.0}"
    _ = bull_expression  # documented in the returned report metadata

    # ONE comparator, used by BOTH the first-hit freeze below and the `bull` label.
    # They disagreed until now: the freeze tested `high_d >= target` while `bull`
    # tested `forward_high > target`. On a bar that only TOUCHED the threshold the
    # freeze stopped one bar early, so `path_low_to_hit` recorded the drawdown up to
    # the touch instead of up to the first strict exceed -- which made
    # `label_strict_low` and `label_joint` too optimistic on exactly those rows.
    # Reproduced: E=10, +30% (target 13), day 1 high=13.00/low=9.00, day 2
    # high=13.10/low=7.00. The old code froze at day 1 (path low 9.00 >= 8.00 gate)
    # and returned joint=1; a consistent strict-`>` rule freezes at day 2 (path low
    # 7.00 < 8.00) and returns joint=0. `>`, not `>=`, because both bull branches
    # are strict.

    forward_high = np.full(n, np.nan, dtype="float64")
    forward_low = np.full(n, np.nan, dtype="float64")
    bars_to_target = np.full(n, np.nan, dtype="float64")
    path_low_to_hit = np.full(n, np.nan, dtype="float64")
    future_bars = np.zeros(n, dtype="float64")

    run_max = np.full(n, -np.inf, dtype="float64")
    run_min = np.full(n, np.inf, dtype="float64")
    seen = np.zeros(n, dtype=bool)
    hit = np.zeros(n, dtype=bool)

    for d in range(1, horizon + 1):
        # Values d bars ahead, invalidated across a stock boundary.
        same = np.zeros(n, dtype=bool)
        if d < n:
            same[: n - d] = codes[d:] == codes[: n - d]

        high_d = np.full(n, np.nan, dtype="float64")
        low_d = np.full(n, np.nan, dtype="float64")
        if d < n:
            high_d[: n - d] = highs[d:]
            low_d[: n - d] = lows[d:]
        high_d[~same] = np.nan
        low_d[~same] = np.nan

        valid = np.isfinite(high_d)
        future_bars[valid] += 1.0
        run_max = np.where(valid, np.maximum(run_max, high_d), run_max)
        run_min = np.where(valid, np.minimum(run_min, low_d), run_min)
        seen |= valid

        # Strict `>`, matching the bull label. See the comparator note above.
        newly = (~hit) & valid & (high_d > target)
        bars_to_target[newly] = d
        path_low_to_hit[newly] = run_min[newly]
        hit |= newly

        forward_high = np.where(valid, run_max, forward_high)
        forward_low = np.where(valid, run_min, forward_low)

    out["entry_open"] = entry
    out["future_bars"] = future_bars
    out["bars_to_target"] = bars_to_target
    out["forward_max_return"] = forward_high / (entry + EPS) - 1.0
    out["forward_min_return"] = forward_low / (entry + EPS) - 1.0

    resolved = (future_bars >= horizon) & np.isfinite(entry)

    if target_return is not None:
        bull = np.where(np.isfinite(forward_high), (forward_high > entry * (1.0 + target_return)).astype(float), np.nan)
    else:
        bull = np.where(np.isfinite(forward_high), (forward_high > target).astype(float), np.nan)
    # Strict low uses the path *up to the first target touch* when there is one,
    # otherwise the full horizon minimum.
    gate_low = np.where(np.isfinite(path_low_to_hit), path_low_to_hit, forward_low)
    strict_low = np.where(
        np.isfinite(gate_low), (gate_low >= strict_low_ratio * entry).astype(float), np.nan
    )

    joint = np.where(np.isfinite(bull) & np.isfinite(strict_low), np.minimum(bull, strict_low), np.nan)

    # Censored rows are excluded from every denominator, never counted as 0.
    for arr in (bull, strict_low, joint):
        arr[~resolved] = np.nan

    out["label_bull"] = bull
    out["label_strict_low"] = strict_low
    out["label_joint"] = joint
    out["label_resolved"] = resolved
    return out


def dedupe_signals(signals: pd.DataFrame, cooldown: int = 60) -> pd.DataFrame:
    """Collapse overlapping signals per stock to the first of each cluster.

    De-duplication is by *trading-session distance*, not calendar days, so
    holidays cannot silently shorten a cooldown.
    """
    if signals.empty:
        return signals.copy()
    out = signals.sort_values(["code", "date"]).copy()
    keep = np.zeros(len(out), dtype=bool)

    session_index = {d: i for i, d in enumerate(sorted(out["date"].unique()))}
    positions = out["date"].map(session_index).to_numpy()
    codes = out["code"].to_numpy()

    start = 0
    for i in range(1, len(out) + 1):
        if i == len(out) or codes[i] != codes[start]:
            last = None
            for j in range(start, i):
                if last is None or (positions[j] - last) >= cooldown:
                    keep[j] = True
                    last = positions[j]
            start = i
    return out[keep]


def score_signals(
    signals: pd.DataFrame,
    horizon: int = HORIZON_DEFAULT,
    cooldown: int = 60,
) -> dict:
    """Compute the full hit-rate report for one strategy's signals."""
    if signals.empty:
        return _empty_report()

    live = signals[signals["label_resolved"]].copy()
    censored = int(len(signals) - len(live))
    if live.empty:
        return _empty_report(censored=censored, raw=int(len(signals)))

    deduped = dedupe_signals(live, cooldown=cooldown)

    def _block(f: pd.DataFrame) -> dict:
        n = len(f)
        if n == 0:
            return {"signals": 0, "bull_hits": 0, "joint_hits": 0,
                    "bull_precision": float("nan"), "joint_precision": float("nan"),
                    "strict_low_rate": float("nan"), "distinct_stocks": 0,
                    "distinct_dates": 0}
        bull = int(f["label_bull"].fillna(0).sum())
        joint = int(f["label_joint"].fillna(0).sum())
        low = int(f["label_strict_low"].fillna(0).sum())
        return {
            "signals": n, "bull_hits": bull, "joint_hits": joint,
            "bull_precision": bull / n, "joint_precision": joint / n,
            "strict_low_rate": low / n,
            "distinct_stocks": int(f["code"].nunique()),
            "distinct_dates": int(f["date"].nunique()),
        }

    raw, ded = _block(live), _block(deduped)
    report = {
        "signals_raw": raw["signals"],
        "signals_deduped": ded["signals"],
        "bull_hits_raw": raw["bull_hits"],
        "bull_precision_raw": raw["bull_precision"],
        "bull_hits_deduped": ded["bull_hits"],
        "bull_precision_deduped": ded["bull_precision"],
        "joint_hits_deduped": ded["joint_hits"],
        "joint_precision_deduped": ded["joint_precision"],
        "strict_low_rate_deduped": ded["strict_low_rate"],
        "distinct_stocks": ded["distinct_stocks"],
        "distinct_dates": ded["distinct_dates"],
        "censored_signals": censored,
        "cooldown": cooldown,
        "horizon": horizon,
        "hhi_date_concentration": _hhi(deduped),
    }
    report["bull_wilson_low"], report["bull_wilson_high"] = _wilson(
        ded["bull_hits"], ded["signals"]
    )
    report["joint_wilson_low"], report["joint_wilson_high"] = _wilson(
        ded["joint_hits"], ded["signals"]
    )
    return report


def _hhi(frame: pd.DataFrame) -> float:
    """Herfindahl index of signals across market dates. 1.0 = all on one day."""
    if frame.empty:
        return float("nan")
    counts = frame["date"].value_counts(normalize=True).to_numpy()
    return float((counts**2).sum())


def _wilson(hits: int, n: int) -> tuple[float, float]:
    """95% Wilson interval, the estimator the project's own gate used."""
    if n == 0:
        return float("nan"), float("nan")
    z = 1.959963984540054
    p = hits / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def _empty_report(censored: int = 0, raw: int = 0) -> dict:
    report = {
        "signals_raw": raw, "signals_deduped": 0,
        "bull_hits_raw": 0, "bull_precision_raw": float("nan"),
        "bull_hits_deduped": 0, "bull_precision_deduped": float("nan"),
        "joint_hits_deduped": 0, "joint_precision_deduped": float("nan"),
        "strict_low_rate_deduped": float("nan"),
        "distinct_stocks": 0, "distinct_dates": 0,
        "hhi_date_concentration": float("nan"),
        "bull_wilson_low": float("nan"), "bull_wilson_high": float("nan"),
        "joint_wilson_low": float("nan"), "joint_wilson_high": float("nan"),
        "censored_signals": censored, "horizon": HORIZON_DEFAULT, "cooldown": 60,
    }
    return report


# --- Baseline provenance -----------------------------------------------------
#
# TWO different code paths publish a quantity called "the natural base rate", and
# they census two different row sets. The numbers are not interchangeable:
#
#   backtest_lowzone.main          -> "panel"    every resolved bar of the layer
#                                                 table (no stride, no minimum
#                                                 history)
#   scan_all.population_baselines  -> "scanned"  only the bars a scan actually
#                                                 evaluated (_seq >= VISIBLE_BARS,
#                                                 then every stride-th bar)
#
# Measured on this panel (data/panel_daily.parquet, 2,680,715 bars, 3,193 codes,
# 2023-01-03..2026-08-31), the two row sets give:
#
#   regime    panel                          scanned
#   webpro    2,648,785 @ 3.0893%            493,246 @ 3.0348%
#   low60     2,489,247 @ 0.0725%            461,416 @ 0.0752%
#   low504    1,108,219 @ 4.2099%            187,729 @ 4.6956%
#
# so a lift computed against one baseline and a hit rate taken from the other is
# internally inconsistent. Use the "scanned" figure to divide a *scanned* signal's
# hit rate by, because a signal can only be emitted at a point the scan visited;
# the "panel" figure is a different, unconditional quantity.
#
# On this panel the `_seq >= min_history` filter is also a calendar filter: 2,853
# of 3,193 codes are present on the first session, so their 60th bar is
# 2023-04-04 and NO row satisfies `_seq >= 60 and date < 2023-04-04`. Dropping
# each stock's first 60 bars therefore drops the 2023-Q1 warm-up window, which is
# why the filter moves `low504` (a 504-session horizon, whose window endpoint is
# fixed by the observation date) far more than it moves `webpro`.
#
# NOTE: every published payload stays keyed BY REGIME at the top level. Consumers
# such as render_results.baselines() iterate `for regime, d in data.items()` and
# index `d["evaluated_points"]`, so a top-level provenance key would raise
# KeyError. Keep provenance blocks inside each regime's dict.
POPULATIONS = {
    "panel": (
        "Full resolved panel: every bar of the layer table with a resolvable "
        "forward outcome. No stride sampling and no minimum-history filter, so "
        "this includes each stock's first bars and the earliest sessions."
    ),
    "scanned": (
        "Scanned evaluation grid: only the bars a strategy was actually scored "
        "at, i.e. per-stock bar index _seq >= min_history and then _seq % stride "
        "== 0. A signal can only be emitted here, so this is the population a "
        "scanned hit rate must be divided by."
    ),
}


def population_provenance(
    population: str,
    *,
    stride: int = 1,
    min_history: int = 0,
    frame: pd.DataFrame | None = None,
    rows: int | None = None,
    date_min=None,
    date_max=None,
) -> dict:
    """Describe the row set a base rate was measured over.

    Attach the result to every published base-rate payload so a reader cannot
    mistake the scanned grid for the full panel. ``population`` is a key of
    :data:`POPULATIONS`; callers either pass ``frame`` (the exact rows that were
    censused) or the already-aggregated ``rows``/``date_min``/``date_max``.
    """
    if population not in POPULATIONS:
        raise ValueError(
            f"unknown population {population!r}; expected one of {sorted(POPULATIONS)}"
        )
    out = {
        "population": population,
        # Stable slug, so two payloads can be compared without parsing prose.
        "population_id": (
            f"{population}_stride{int(stride)}_minhist{int(min_history)}"
        ),
        "population_definition": POPULATIONS[population],
        "stride": int(stride),
        "min_history": int(min_history),
    }
    if frame is not None:
        if len(frame):
            out["rows"] = int(len(frame))
            out["date_min"] = pd.Timestamp(frame["date"].min()).strftime("%Y-%m-%d")
            out["date_max"] = pd.Timestamp(frame["date"].max()).strftime("%Y-%m-%d")
        else:
            out["rows"] = 0
    elif rows is not None:
        # `rows` is the same count the payload publishes as `candidates` /
        # `evaluated_points`; equal values prove the block describes that row set.
        out["rows"] = int(rows)
    if date_min is not None:
        out["date_min"] = pd.Timestamp(date_min).strftime("%Y-%m-%d")
    if date_max is not None:
        out["date_max"] = pd.Timestamp(date_max).strftime("%Y-%m-%d")
    return out


def baseline_rates(frame: pd.DataFrame, horizon: int = HORIZON_DEFAULT) -> dict:
    """Natural base rates across the whole resolved candidate population.

    A precision number is uninterpretable without this: 4% precision looks very
    different against a 1.6% base rate than against a 0.2% one.

    This censuses the **"panel"** population: every resolved bar passed in, with
    no stride sampling and no minimum-history filter. It is currently not called
    by any code path; ``backtest_lowzone.main`` inlines the same computation and
    ``scan_all.population_baselines`` computes the "scanned" variant. If you
    revive it, attach :func:`population_provenance` so the payload says which row
    set it counted.
    """
    live = frame[frame["label_resolved"]]
    n = len(live)
    if n == 0:
        return {"candidates": 0, "horizon": horizon}
    bull = int(live["label_bull"].fillna(0).sum())
    joint = int(live["label_joint"].fillna(0).sum())
    return {
        "candidates": n,
        "bull_rate": bull / n,
        "joint_rate": joint / n,
        "strict_low_rate": float(live["label_strict_low"].fillna(0).mean()),
        "horizon": horizon,
    }
