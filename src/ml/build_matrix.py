"""Build a rich, unsaturated feature matrix for the joint 10-session / +30% task.

The source expert library projects every mechanism through `clip(x, 0, 1)` and
then takes a fixed linear combination. Section 2.4 and 4.3 of the review plan
identify the consequence: 8%, 15% and 25% recent gains all become exactly 1.0, so
a model built on those scores cannot distinguish confirmation from acceleration
from overheating. This module rebuilds the same information as **raw continuous
features**, and adds the market and cross-sectional context the experts never
had.

Every feature is causal: it is computable from bars up to and including the
signal bar's close. Nothing reads forward. Cross-sectional features are computed
within a single session, which is legitimate because the whole cross-section is
observable at that session's close — the same moment the signal is knowable.

Targets
-------
Two definitions are produced side by side, because they are not the same event
and the review plan (§7.3) requires them to be named rather than conflated:

``label_high``  forward maximum **high** > entry x (1 + target). This is the
                contract the original 70-80% claims were measured under, and it
                is what `src.labels` already implements, so results stay
                comparable to the 19.17% figure.
``label_close`` forward maximum **close** > entry x (1 + target). The stricter
                daily-order convention the review plan adopts as its main spec.

Entry is the next session's open in both cases, matching `src.labels`.

Usage
-----
    python -m src.ml.build_matrix --stride 1 --horizon 10 --target 0.30
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import data_pipeline

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "outputs" / "ml"
EPS = 1e-12


def assert_sorted(frame: pd.DataFrame) -> None:
    """Fail loudly unless the frame is sorted by (code, date).

    Every grouped-rolling helper below relies on row order matching group-key
    order, because ``groupby(...).rolling(...).reset_index(level=0, drop=True)``
    returns results in group-key order. Audit measured that on an UNSORTED frame
    the same expression mismatches 2,679,396 of 2,680,715 rows — silent,
    total corruption with no error raised. ``build()`` always sorts, so this is
    currently harmless, but the guard turns a future silent failure into a
    loud one.
    """
    ordered = frame.sort_values(["code", "date"])
    if not frame[["code", "date"]].reset_index(drop=True).equals(
        ordered[["code", "date"]].reset_index(drop=True)
    ):
        raise ValueError(
            "frame must be sorted by ['code', 'date'] before grouped rolling; "
            "row order must match group-key order or the rolling results "
            "misalign silently"
        )


# --------------------------------------------------------------------------
# rolling / shift helpers, all within stock, all backward-looking
# --------------------------------------------------------------------------
def _groll(frame: pd.DataFrame, col: str, window: int, how: str = "mean") -> np.ndarray:
    """Backward rolling statistic within each stock, returned as float32."""
    grouped = frame.groupby("code", sort=False)[col].rolling(
        window, min_periods=max(2, window // 2)
    )
    if how == "mean":
        out = grouped.mean()
    elif how == "std":
        out = grouped.std()
    elif how == "max":
        out = grouped.max()
    elif how == "min":
        out = grouped.min()
    elif how == "sum":
        out = grouped.sum()
    else:
        raise ValueError(how)
    return out.reset_index(level=0, drop=True).to_numpy(dtype="float32")


def _gshift(frame: pd.DataFrame, col: str, n: int) -> np.ndarray:
    """Value n sessions ago within each stock (n>0 is the past)."""
    return (
        frame.groupby("code", sort=False)[col]
        .shift(n)
        .to_numpy(dtype="float32")
    )


def add_price_features(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Raw momentum, volatility, position, candle and limit-up structure."""
    close = frame["close"].to_numpy("float64")
    high = frame["high"].to_numpy("float64")
    low = frame["low"].to_numpy("float64")
    open_ = frame["open"].to_numpy("float64")
    volume = frame["volume"].to_numpy("float64")
    f: dict[str, np.ndarray] = {}

    # --- returns at many scales. Raw, never clipped: the whole point is that
    # 8% and 25% must remain distinguishable.
    for lag in (1, 2, 3, 5, 10, 20, 60, 120, 250):
        prev = _gshift(frame, "close", lag).astype("float64")
        f[f"ret{lag}"] = (close / (prev + EPS) - 1.0).astype("float32")

    # --- realised volatility of daily returns
    frame["_ret1"] = f["ret1"]
    for window in (5, 10, 20, 60):
        f[f"vol{window}"] = _groll(frame, "_ret1", window, "std")
    # NB: `vol_ratio_5_20`/`vol_ratio_20_60` are defined further down from the
    # volume moving averages, not from these return volatilities. A duplicate
    # definition here (return-vol ratio) was overwritten before anything read it,
    # so it was dead code that read as the live definition and would mislead the
    # next editor about which quantity the feature holds. Removed: no numeric
    # effect, the surviving volume-based version is unchanged.

    # --- true range and ATR, expressed as a fraction of price so it is
    # comparable across stocks and across time.
    prev_close = _gshift(frame, "close", 1).astype("float64")
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    frame["_tr"] = tr
    atr14 = _groll(frame, "_tr", 14, "mean").astype("float64")
    f["atr14_pct"] = (atr14 / (close + EPS)).astype("float32")

    # --- volume / turnover structure. `turnover` is the volume proxy that
    # §3.1 flags; it is kept explicit and separately named so a model can be
    # ablated against it rather than silently trusting it.
    for window in (5, 20, 60):
        f[f"vol_ma{window}"] = _groll(frame, "volume", window, "mean")
    f["vol_ratio_1_5"] = (volume / (f["vol_ma5"].astype("float64") + EPS)).astype("float32")
    f["vol_ratio_5_20"] = (f["vol_ma5"] / (f["vol_ma20"] + EPS)).astype("float32")
    f["vol_ratio_20_60"] = (f["vol_ma20"] / (f["vol_ma60"] + EPS)).astype("float32")
    f["vol_stability_20"] = (
        _groll(frame, "volume", 20, "std") / (f["vol_ma20"] + EPS)
    ).astype("float32")

    # --- moving-average distances (raw, signed, unbounded above)
    for window in (5, 10, 20, 60, 120, 250):
        ma = _groll(frame, "close", window, "mean").astype("float64")
        f[f"dist_ma{window}"] = (close / (ma + EPS) - 1.0).astype("float32")
        # slope of the MA itself, normalised by price
        ma_prev = _gshift(frame, "close", window).astype("float64")
        f[f"ma{window}_slope"] = ((ma - ma_prev) / (close + EPS)).astype("float32")

    # --- position within the recent range, and drawdown from the recent high
    for window in (60, 120, 250):
        hi = _groll(frame, "high", window, "max").astype("float64")
        lo = _groll(frame, "low", window, "min").astype("float64")
        f[f"pos_{window}"] = ((close - lo) / (hi - lo + EPS)).astype("float32")
        f[f"dd_{window}"] = (close / (hi + EPS) - 1.0).astype("float32")
        f[f"to_high_{window}"] = (hi / (close + EPS) - 1.0).astype("float32")

    # --- range contraction: §13's volatility-squeeze mechanism
    rng = high - low
    frame["_rng"] = rng
    r5 = _groll(frame, "_rng", 5, "mean").astype("float64")
    r20 = _groll(frame, "_rng", 20, "mean").astype("float64")
    r60 = _groll(frame, "_rng", 60, "mean").astype("float64")
    f["range_5_20"] = (r5 / (r20 + EPS)).astype("float32")
    f["range_20_60"] = (r20 / (r60 + EPS)).astype("float32")
    f["range_pct"] = (rng / (close + EPS)).astype("float32")

    # --- candle anatomy. close_loc is the close's position inside the day's
    # range; wicks are normalised by the range, so they are scale-free.
    span = high - low
    f["close_loc"] = ((close - low) / (span + EPS)).astype("float32")
    f["upper_wick"] = ((high - np.maximum(open_, close)) / (span + EPS)).astype("float32")
    f["lower_wick"] = ((np.minimum(open_, close) - low) / (span + EPS)).astype("float32")
    f["body_pct"] = ((close - open_) / (open_ + EPS)).astype("float32")
    f["gap_open"] = ((open_ - prev_close) / (prev_close + EPS)).astype("float32")

    # --- limit-up structure. A +30% move in 10 sessions on a 10%-limit board is
    # nearly always a chain of limit boards, so this is the most task-relevant
    # structure in the whole feature set.
    limit_up = (f["ret1"] >= 0.095).astype("float32")
    frame["_lu"] = limit_up
    for window in (5, 10, 20):
        f[f"limitup_{window}"] = _groll(frame, "_lu", window, "sum")
    f["limitup_yesterday"] = _gshift(frame, "_lu", 1)
    # consecutive up / down sessions
    up = (f["ret1"] > 0).astype("float32")
    frame["_up"] = up
    f["up_rate_20"] = _groll(frame, "_up", 20, "mean")

    # --- KDJ as a continuous causal series (never resets at a year boundary).
    # `kdj` returns the frame with kdj_k/kdj_d/kdj_j appended, not a tuple.
    from src.features import kdj

    kdj_frame = kdj(frame)
    f["kdj_k"] = kdj_frame["kdj_k"].to_numpy("float32")
    f["kdj_d"] = kdj_frame["kdj_d"].to_numpy("float32")
    f["kdj_j"] = kdj_frame["kdj_j"].to_numpy("float32")
    frame["_k"] = f["kdj_k"]
    frame["_j"] = f["kdj_j"]
    f["kdj_k_chg5"] = (f["kdj_k"] - _gshift(frame, "_k", 5)).astype("float32")
    f["kdj_j_chg5"] = (f["kdj_j"] - _gshift(frame, "_j", 5)).astype("float32")
    f["kdj_k_minus_d"] = (f["kdj_k"] - f["kdj_d"]).astype("float32")
    return f


def add_market_features(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    """Equal-weighted market context, computed from the panel itself.

    There is no index file in the source data, so the market is proxied by the
    equal-weighted cross-sectional mean of each session. This is observable at
    that session's close, so it is causal.
    """
    f: dict[str, np.ndarray] = {}
    by_date = frame.groupby("date", sort=False)
    f["mkt_ret1"] = by_date["_ret1"].transform("mean").to_numpy("float32")
    f["mkt_breadth"] = by_date["_up"].transform("mean").to_numpy("float32")
    f["mkt_dispersion"] = by_date["_ret1"].transform("std").to_numpy("float32")

    # Market momentum over several windows, from the daily market series.
    daily = frame.groupby("date", sort=False)["_ret1"].mean().sort_index()
    market = pd.DataFrame({"mkt": daily})
    for window in (5, 20, 60):
        market[f"mkt_ret{window}"] = market["mkt"].rolling(window, min_periods=2).sum()
    market["mkt_vol20"] = market["mkt"].rolling(20, min_periods=2).std()
    merged = frame[["date"]].merge(market.reset_index(), on="date", how="left")
    for col in ("mkt_ret5", "mkt_ret20", "mkt_ret60", "mkt_vol20"):
        f[col] = merged[col].to_numpy("float32")

    # Stock-level beta to the equal-weighted market, using only past data.
    # Computed as cov/var via rolling means rather than groupby.apply, which on
    # 3,193 groups is orders of magnitude slower: cov(x,y) = E[xy] - E[x]E[y].
    frame["_mkt1"] = f["mkt_ret1"].astype("float64")
    frame["_xy"] = frame["_ret1"].astype("float64") * frame["_mkt1"]
    frame["_yy"] = frame["_mkt1"] ** 2
    grouped = frame.groupby("code", sort=False)

    def _roll(col: str) -> np.ndarray:
        return (
            grouped[col]
            .rolling(60, min_periods=20)
            .mean()
            .reset_index(level=0, drop=True)
            .to_numpy("float64")
        )

    mean_x = _roll("_ret1")
    mean_y = _roll("_mkt1")
    mean_xy = _roll("_xy")
    mean_yy = _roll("_yy")
    cov = mean_xy - mean_x * mean_y
    var = mean_yy - mean_y**2
    beta = cov / (var + EPS)
    f["beta_60"] = np.clip(beta, -5.0, 5.0).astype("float32")
    # Idiosyncratic return: what is left after removing market beta exposure.
    f["resid_ret1"] = (
        frame["_ret1"].to_numpy("float64")
        - f["beta_60"].astype("float64") * f["mkt_ret1"].astype("float64")
    ).astype("float32")
    del frame["_xy"], frame["_yy"]
    return f


def add_cross_sectional(frame: pd.DataFrame, base: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Same-session percentile ranks and z-scores.

    The review plan (§2.4) notes that `relative_strength_rank` has no relative
    object at all. These provide the real cross-sectional context, computed
    within one session so they are available at that session's close.

    ``base`` holds the features built so far; they are attached to a scratch
    frame because groupby needs real columns to rank.
    """
    f: dict[str, np.ndarray] = {}
    scratch = frame[["code", "date"]].copy()
    for col in ("ret5", "ret20", "ret60", "vol_ratio_5_20", "atr14_pct", "pos_60"):
        scratch[col] = np.asarray(base[col], dtype="float64")
    by_date = scratch.groupby("date", sort=False)
    for col, name in (
        ("ret5", "cs_ret5"),
        ("ret20", "cs_ret20"),
        ("ret60", "cs_ret60"),
        ("vol_ratio_5_20", "cs_volratio"),
        ("atr14_pct", "cs_atr"),
        ("pos_60", "cs_pos60"),
    ):
        f[f"{name}_rank"] = by_date[col].rank(pct=True).to_numpy("float32")
        mu = by_date[col].transform("mean")
        sd = by_date[col].transform("std")
        f[f"{name}_z"] = ((scratch[col] - mu) / (sd + EPS)).to_numpy("float32")
    return f


def build(
    panel: pd.DataFrame,
    horizon: int,
    target: float,
    stride: int,
    stride_mode: str = "row",
) -> pd.DataFrame:
    """Assemble the full feature matrix and both label definitions."""
    from src import labels as label_mod

    frame = panel.sort_values(["code", "date"]).reset_index(drop=True)
    assert_sorted(frame)

    price = add_price_features(frame)
    market = add_market_features(frame)
    # Cross-sectional features need the price features as real columns, so they
    # are built after and receive them explicitly.
    cross = add_cross_sectional(frame, {**price, **market})
    features: dict[str, np.ndarray] = {}
    for part in (price, market, cross):
        features.update(part)

    out = pd.DataFrame({"code": frame["code"], "date": frame["date"]})
    for name, values in features.items():
        out[name] = np.asarray(values, dtype="float32")

    # --- labels. Reuse src.labels so the definition is bit-identical to the one
    # behind the published 19.17%, then add the close-based variant.
    labelled = label_mod.forward_outcomes(
        frame[["code", "date", "open", "high", "low", "close", "volume"]].assign(
            turnover=frame["volume"], turnover_is_proxy=True
        ),
        horizon=horizon,
        target_return=target,
    )
    out["entry_open"] = labelled["entry_open"].to_numpy("float32")
    out["fwd_max_high"] = labelled["forward_max_return"].to_numpy("float32")
    out["fwd_min_low"] = labelled["forward_min_return"].to_numpy("float32")
    out["label_high"] = labelled["label_bull"].to_numpy("float32")
    out["resolved"] = labelled["label_resolved"].to_numpy("float32")

    # Keep the true float64 entry price for label arithmetic. `entry_open` above
    # is deliberately float32 because it is a feature-layer convenience column,
    # but casting it back to float64 downstream does NOT recover the lost
    # precision: float32(9.99) is 9.989999771118164. A review correctly identified
    # that the close-label comparison below was doing exactly that round trip, so a
    # price ratio sitting exactly on the target boundary could flip. Label
    # decisions now use this full-precision vector and never touch `entry_open`.
    entry_f64 = labelled["entry_open"].to_numpy("float64")

    # forward maximum close, same entry and window.
    #
    # The label must be censored on the SAME condition as `resolved` (a full
    # `horizon`-bar window existing), not merely on having seen one future bar.
    # Censoring on `seen` was a real defect found by audit: 5,747 rows at the end
    # of the panel (2026-08-10..2026-08-28) received a `label_close` computed
    # from a 1-to-9-bar partial window, which biases the base rate of any
    # close-labelled experiment. Those rows fall outside every walk-forward fold,
    # so the 15.98% headline was unaffected, but any 2026 close-label evaluation
    # would have been silently wrong.
    close = frame["close"].to_numpy("float64")
    codes = frame["code"].to_numpy()
    n = len(frame)
    run = np.full(n, -np.inf)
    bars_seen = np.zeros(n, dtype="int32")
    for d in range(1, horizon + 1):
        same = np.zeros(n, dtype=bool)
        if d < n:
            same[: n - d] = codes[d:] == codes[: n - d]
        val = np.full(n, np.nan)
        if d < n:
            val[: n - d] = close[d:]
        ok = same & np.isfinite(val)
        run = np.where(ok, np.maximum(run, np.where(ok, val, -np.inf)), run)
        bars_seen += ok.astype("int32")

    mature = bars_seen >= horizon

    # A non-positive entry price is a data error, not something to paper over with
    # an epsilon: adding EPS to the denominator silently shifts EVERY boundary to
    # protect against a case that should simply be reported. Flag it instead.
    #
    # `entry_open` is the NEXT bar's open, so the final bar of every stock has no
    # entry price and is legitimately NaN. A first version of this check used
    # `~(entry > 0)`, which is True for NaN and so reported one "bad" row per
    # stock (3,193 of them) that were not bad at all. Non-finite and non-positive
    # are now counted separately, and only the latter is a data error.
    not_finite = ~np.isfinite(entry_f64)
    non_positive = np.isfinite(entry_f64) & (entry_f64 <= 0)
    n_bad = int(non_positive.sum())
    if n_bad:
        print(f"  WARNING {n_bad} row(s) have a finite non-positive entry price; "
              f"their labels are censored rather than computed")
    n_open_end = int(not_finite.sum())
    if n_open_end:
        print(f"  note: {n_open_end} row(s) have no entry price (final bar of a "
              f"stock); labels censored as unresolved")
    usable = mature & ~not_finite & ~non_positive & np.isfinite(run)

    # Direct price comparison: `future_high > entry * (1 + target)`. This is the
    # definition stated in the module docstring, evaluated in float64 on the raw
    # prices, so no ratio is formed and no epsilon is needed.
    threshold_price = entry_f64 * (1.0 + target)
    out["fwd_max_close"] = np.where(
        usable, run / entry_f64 - 1.0, np.nan
    ).astype("float32")
    with np.errstate(invalid="ignore"):
        # The high-based label comes from src.labels (bit-identical to the
        # published definition); the close-based one is computed here the same
        # way, by comparing prices rather than a rounded ratio.
        out["label_close"] = np.where(
            usable, (run > threshold_price).astype("float32"), np.nan
        ).astype("float32")

    if stride > 1:
        # Two subsampling modes, and the difference matters enough to be explicit.
        #
        # `row` (default) reproduces every published number in this repository.
        # It takes every stride-th ROW of the (code, date)-sorted frame. Because
        # stocks have unequal row counts, each stock lands on a different date
        # phase: measured on the full panel at stride 5 this keeps all 887
        # sessions but only ~604 of ~3,022 stocks per session, with 660 distinct
        # per-stock date sets.
        #
        # That phase spread is worth being honest about. It is NOT a label or
        # feature bias: every feature and both labels are computed on the full
        # panel *before* subsampling, so the retained rows are a plain thinning
        # of correctly-computed data and the label distribution is essentially
        # unchanged (base_rate_high 0.030916 subsampled vs 0.030893 full, a
        # 0.07% relative difference). What it does do is make any *per-session
        # cross-sectional* statement weaker, because "top-1 that day" is the best
        # of ~604 sampled names rather than of the full ~3,022. Results of that
        # kind should be re-run at `--stride 1` before being relied on.
        #
        # `session` instead keeps every stride-th SESSION, so each retained day
        # carries a complete cross-section and every stock shares one date set.
        # It is the cleaner sample for cross-sectional work, but it costs
        # coverage: at stride 5 it keeps only 178 of 887 sessions, which is below
        # the 150-session warm-up plus purge/embargo that
        # `walkforward.folds` needs, so the walk-forward raises rather than
        # silently producing fewer folds.
        if stride_mode == "session":
            sessions = np.sort(out["date"].unique())
            keep_sessions = set(sessions[::stride])
            n_before = len(out)
            out = out[out["date"].isin(keep_sessions)].reset_index(drop=True)
            print(f"  stride {stride} (session grid): kept {len(keep_sessions):,} "
                  f"of {len(sessions):,} sessions ({n_before:,} -> {len(out):,} "
                  f"rows); every stock shares the same retained dates")
        else:
            n_before = len(out)
            n_sess_before = out["date"].nunique()
            out = out.iloc[::stride].reset_index(drop=True)
            per_sess = out.groupby("date").size()
            print(f"  stride {stride} (row grid): {n_before:,} -> {len(out):,} "
                  f"rows, {out['date'].nunique():,} of {n_sess_before:,} sessions "
                  f"kept, ~{per_sess.mean():.0f} stocks per retained session "
                  f"(phases differ per stock; use --stride 1 for full "
                  f"cross-sections)")

    for tmp in ("_ret1", "_tr", "_rng", "_lu", "_up", "_k", "_j", "_mkt1"):
        if tmp in out.columns:
            del out[tmp]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--horizon", type=int, default=10)
    ap.add_argument("--target", type=float, default=0.30)
    ap.add_argument(
        "--stride-mode", choices=("row", "session"), default="row",
        help="how --stride subsamples: 'row' takes every stride-th row and "
             "reproduces every published number; 'session' keeps whole sessions "
             "with complete cross-sections but drops far more of the timeline",
    )
    args = ap.parse_args()

    panel = data_pipeline.load_panel()
    matrix = build(panel, args.horizon, args.target, args.stride,
                   stride_mode=args.stride_mode)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Stride is part of the identity: a stride-5 matrix is a different sample of
    # the same panel and must never silently overwrite the dense one. The mode is
    # part of the name too, because a session-grid stride-5 matrix is a different
    # sample again and would otherwise collide with the row-grid one under the
    # same name — which is exactly how a session-grid matrix once overwrote the
    # matrix every published report was built from.
    suffix = f"_s{args.stride}"
    if args.stride > 1 and args.stride_mode != "row":
        suffix += f"_{args.stride_mode}"
    stem = f"matrix_h{args.horizon}_t{int(args.target*100)}{suffix}"
    path = OUT_DIR / f"{stem}.parquet"
    matrix.to_parquet(path, index=False)

    feature_cols = [
        c for c in matrix.columns
        if c not in {"code", "date", "entry_open", "fwd_max_high", "fwd_min_low",
                     "label_high", "label_close", "resolved", "fwd_max_close"}
    ]
    report = {
        "path": str(path),
        "rows": int(len(matrix)),
        "stocks": int(matrix["code"].nunique()),
        "sessions": int(matrix["date"].nunique()),
        "features": len(feature_cols),
        "feature_names": feature_cols,
        "horizon": args.horizon,
        "target": args.target,
        "stride": args.stride,
        "base_rate_high": float(matrix["label_high"].mean(skipna=True)),
        "base_rate_close": float(matrix["label_close"].mean(skipna=True)),
        "resolved_share": float(matrix["resolved"].mean()),
    }
    (OUT_DIR / f"{stem}_meta.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "feature_names"}, indent=2))


if __name__ == "__main__":
    main()
