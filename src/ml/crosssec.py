"""Cross-sectional (per-session) ranking and selection primitives.

The harness in :mod:`src.ml.walkforward` evaluates a model by picking ONE global
probability threshold on the training scores and publishing every test row above
it. That answers "is this row's probability high?" but it does not answer the
question a portfolio actually asks: **"within this session, which names are the
best?"**  A model whose probabilities are badly calibrated across time -- high in
2024, low in 2025 -- can have a useless global threshold and still rank names
correctly inside each day.

This module adds the missing object:

* :func:`per_session_rank` -- 0-based within-session rank, best score = 0.
* :func:`topk_mask` -- the per-session top-K selection rule, the strategy-form
  analogue of a global threshold.
* :func:`session_percentile` -- the within-session percentile score, so a
  threshold can be applied to *relative* rather than absolute standing.
* :func:`date_clustered_bootstrap` -- resamples **dates**, not rows. Signals
  emitted on the same session share a market factor, so a naive row bootstrap
  would report a confidence interval several times too narrow.
* :func:`concentration` -- Herfindahl index across dates, distinct dates and
  stocks, and the precision after deleting the busiest date. A headline number
  that lives on one market day is not a result.

Nothing here chooses a hyper-parameter on the evaluation block. Where a choice
is needed (the top-K ``K`` itself) the caller must supply it from training data;
:func:`select_k_on_train` and the nested protocol in ``search_crosssec`` exist
so that this is possible without peeking.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

FINAL_HOLDOUT_START = "2026-01-01"
TOP_K_GRID = (1, 3, 5, 10, 20, 50)
PERCENTILE_GRID = (0.995, 0.999, 0.9995, 0.9999)


# ---------------------------------------------------------------------------
# folds / scoring, wire-compatible with src.ml.walkforward
# ---------------------------------------------------------------------------
def load() -> pd.DataFrame:
    """The shared feature matrix. Thin alias so callers import one module."""
    return wf.load_matrix()


def build_folds(
    frame: pd.DataFrame,
    n_folds: int = 5,
    horizon: int = 10,
    embargo: int = 2,
    min_train_sessions: int = 150,
):
    """Identical fold construction to ``src.ml.search`` -- same arguments, same
    order, same final-holdout exclusion. Divergence here would invalidate every
    comparison against the published 15.98% baseline."""
    sessions = np.sort(frame["date"].unique())
    return wf.folds(
        sessions,
        n_folds=n_folds,
        horizon=horizon,
        embargo=embargo,
        min_train_sessions=min_train_sessions,
        final_holdout_start=FINAL_HOLDOUT_START,
    )


def fit_scores(
    train: pd.DataFrame,
    test: pd.DataFrame,
    cfg: wf.Config,
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit one model on ``train`` and return scored train/test frames.

    Row filtering reproduces ``wf.evaluate_fold`` exactly: train keeps only
    resolved, labelled rows; test keeps every labelled row (the harness does not
    require ``resolved`` on the test side either). Returns frames carrying
    ``code``, ``date``, the label column and ``score`` so every downstream
    statistic can be recomputed without refitting.
    """
    cols = wf.select_features(wf.feature_columns(train), cfg.feature_groups)
    y_col = cfg.label
    tr = train[train[y_col].notna() & train["resolved"].fillna(0).astype(bool)]
    te = test[test[y_col].notna()]
    if len(tr) < 5000 or len(te) < 200:
        raise ValueError(f"insufficient rows: train={len(tr)} test={len(te)}")

    model = wf.make_model(cfg, seed)
    model.fit(tr[cols].to_numpy("float32"), tr[y_col].to_numpy("float64"))
    s_tr = model.predict_proba(tr[cols].to_numpy("float32"))[:, 1]
    s_te = model.predict_proba(te[cols].to_numpy("float32"))[:, 1]

    keep = ["code", "date", y_col]
    out_tr = tr[keep].copy()
    out_tr["score"] = s_tr
    out_te = te[keep].copy()
    out_te["score"] = s_te
    return out_tr, out_te


# ---------------------------------------------------------------------------
# cross-sectional selection rules
# ---------------------------------------------------------------------------
def per_session_rank(frame: pd.DataFrame, score_col: str = "score") -> np.ndarray:
    """0-based rank of every row within its own session; best score gets 0."""
    r = frame.groupby("date", sort=False)[score_col].rank(
        ascending=False, method="first"
    )
    return r.to_numpy() - 1.0


def topk_mask(frame: pd.DataFrame, k: int, score_col: str = "score") -> np.ndarray:
    """Boolean mask of the top-``k`` scores in each session.

    Sessions with fewer than ``k`` rows publish everything they have; with 887
    stride-5 sessions of ~600 names this never binds, but the rule is stated so
    the signal count is not silently short.
    """
    return per_session_rank(frame, score_col) < k


def session_percentile(frame: pd.DataFrame, score_col: str = "score") -> np.ndarray:
    """Within-session percentile of the score in [0, 1]; 1.0 is the best name.

    This is the cross-sectional normalisation of the raw probability: it strips
    whatever day-level shift the model's calibration carries and keeps only the
    ordering inside the day.
    """
    return frame.groupby("date", sort=False)[score_col].rank(pct=True).to_numpy()


def percentile_mask(
    frame: pd.DataFrame, q: float, score_col: str = "score"
) -> np.ndarray:
    """Publish the top ``1 - q`` share of each session by within-day percentile."""
    return session_percentile(frame, score_col) > q


def session_zscore(frame: pd.DataFrame, score_col: str = "score") -> np.ndarray:
    """Within-session z-score of the model score (mean/SD inside each day)."""
    g = frame.groupby("date", sort=False)[score_col]
    mu = g.transform("mean").to_numpy("float64")
    sd = g.transform("std").to_numpy("float64")
    return (frame[score_col].to_numpy("float64") - mu) / (sd + 1e-12)


# ---------------------------------------------------------------------------
# scoring statistics
# ---------------------------------------------------------------------------
def precision(y: np.ndarray, mask: np.ndarray) -> float:
    y = np.asarray(y, dtype="float64")
    mask = np.asarray(mask, dtype=bool)
    if mask.sum() == 0:
        return float("nan")
    return float(y[mask].mean())


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Valid at the small counts this task produces,
    where the normal approximation is not."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return float(max(0.0, c - h)), float(min(1.0, c + h))


def _date_stats(
    hits: np.ndarray, dates: np.ndarray, universe_dates: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Per-universe-date hit totals and signal counts."""
    idx = pd.Index(universe_dates).get_indexer(np.asarray(dates))
    if (idx < 0).any():
        raise ValueError("signal date missing from the universe date index")
    n = len(universe_dates)
    counts = np.bincount(idx, minlength=n).astype("float64")
    sums = np.bincount(idx, weights=np.asarray(hits, dtype="float64"), minlength=n)
    return sums, counts


def date_clustered_bootstrap(
    hits: np.ndarray,
    dates: np.ndarray,
    universe_dates: np.ndarray | None = None,
    n_boot: int = 4000,
    seed: int = 0,
    level: float = 0.95,
    block: int = 1,
) -> dict:
    """Bootstrap CI for precision by resampling **dates**, not rows.

    ``block`` joins ``block`` consecutive sessions in the universe date order
    into one resampling unit (cyclically). Block 1 is the plain date-clustered
    bootstrap. Blocks > 1 are the honest choice for a stride-5 matrix: two
    adjacent stride-5 sessions are 5 trading days apart while the label window
    is 10 sessions, so consecutive dates share part of their forward window and
    are not independent clusters.

    Resampling is over ``universe_dates`` (default: every date present in the
    signals). Passing the full test-date calendar is the conservative choice --
    it admits that days carrying no signal could have behaved differently.
    """
    hits = np.asarray(hits, dtype="float64")
    dates = np.asarray(dates)
    if universe_dates is None:
        universe_dates = np.unique(dates)
    universe_dates = np.sort(np.asarray(universe_dates))
    n_days = len(universe_dates)
    sums, counts = _date_stats(hits, dates, universe_dates)

    rng = np.random.default_rng(seed)
    if block <= 1:
        idx = rng.integers(0, n_days, size=(n_boot, n_days))
    else:
        n_blocks = int(np.ceil(n_days / block))
        starts = rng.integers(0, n_days, size=(n_boot, n_blocks))
        offs = np.arange(block)
        idx = (starts[:, :, None] + offs[None, None, :]) % n_days
        idx = idx.reshape(n_boot, -1)

    h = sums[idx].sum(axis=1)
    c = counts[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(c > 0, h / np.maximum(c, 1e-12), np.nan)
    p = p[np.isfinite(p)]

    point_h = hits.sum()
    point_n = len(hits)
    alpha = (1.0 - level) / 2.0
    return {
        "n_signals": int(point_n),
        "n_dates": int(n_days),
        "precision": float(point_h / point_n) if point_n else float("nan"),
        "ci_low": float(np.quantile(p, alpha)),
        "ci_high": float(np.quantile(p, 1 - alpha)),
        "boot_mean": float(p.mean()),
        "boot_sd": float(p.std()),
        "block": int(block),
        "n_boot": int(n_boot),
        "level": float(level),
    }


# ---------------------------------------------------------------------------
# concentration diagnostics
# ---------------------------------------------------------------------------
def concentration(
    hits: np.ndarray,
    dates: np.ndarray,
    codes: np.ndarray,
) -> dict:
    """How clustered are the signals, and does the result survive de-clustering?

    ``herfindahl_dates`` is ``sum_i (n_i / N)^2`` over sessions; its reciprocal
    is the effective number of sessions the result rests on. ``precision_drop_
    busiest_date`` deletes every signal on the single most-populated session --
    the cheapest way to check whether one market day is carrying the headline.
    """
    hits = np.asarray(hits, dtype="float64")
    dates = np.asarray(dates)
    codes = np.asarray(codes)
    n = len(hits)
    if n == 0:
        return {"n_signals": 0}

    _, counts = np.unique(dates, return_counts=True)
    share = counts / counts.sum()
    herf = float((share**2).sum())
    order = np.argsort(counts)[::-1]

    # Leave-one-date-out precision: the worst single-date deletion is the
    # strongest statement of fragility.
    uniq, inv = np.unique(dates, return_inverse=True)
    tot_h = np.bincount(inv, weights=hits, minlength=len(uniq))
    tot_n = np.bincount(inv, minlength=len(uniq)).astype("float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        loo = np.where(tot_n > 0, (hits.sum() - tot_h) / np.maximum(n - tot_n, 1e-12), np.nan)

    busiest = uniq[order[0]]
    drop_busiest = dates != busiest
    busiest_h = float(tot_h[order[0]])
    busiest_n = float(tot_n[order[0]])

    # Median per-date precision: equal weight per day instead of per signal, so
    # a single busy day cannot dominate the average.
    with np.errstate(invalid="ignore", divide="ignore"):
        per_date = np.where(tot_n > 0, tot_h / np.maximum(tot_n, 1e-12), np.nan)
    per_date = per_date[np.isfinite(per_date)]

    return {
        "n_signals": int(n),
        "n_distinct_dates": int(len(uniq)),
        "n_distinct_stocks": int(pd.Index(codes).nunique()),
        "herfindahl_dates": herf,
        "effective_dates": float(1.0 / herf) if herf > 0 else float("nan"),
        "max_date_share": float(share.max()),
        "busiest_date": str(pd.Timestamp(busiest).date()),
        "busiest_date_signals": int(busiest_n),
        "busiest_date_precision": float(busiest_h / busiest_n) if busiest_n else float("nan"),
        "precision_drop_busiest_date": (
            float(hits[drop_busiest].mean()) if drop_busiest.sum() else float("nan")
        ),
        "precision_drop_busiest_n": int(drop_busiest.sum()),
        "precision_drop_worst_date": float(np.nanmin(loo)),
        "precision_drop_best_date": float(np.nanmax(loo)),
        "median_daily_precision": float(np.median(per_date)),
        "mean_daily_precision": float(np.mean(per_date)),
        "share_dates_above_base": float(
            np.mean(per_date > float(hits.mean())) if len(per_date) else float("nan")
        ),
    }


# ---------------------------------------------------------------------------
# the baselines a cross-sectional rule has to beat
# ---------------------------------------------------------------------------
def global_threshold_mask(
    s_tr: np.ndarray, s_te: np.ndarray, target_rate: float
) -> tuple[float, np.ndarray]:
    """The harness rule: one threshold from TRAINING scores, applied to test."""
    thr = wf.pick_threshold(np.asarray(s_tr, dtype="float64"),
                            np.zeros(len(s_tr)), target_rate)
    return thr, np.asarray(s_te, dtype="float64") >= thr


def matched_rate_for_topk(k: int, n_train_rows: int, n_train_sessions: int) -> float:
    """Publication rate a global threshold needs to emit ``k`` signals a day.

    Used only to give the global baseline the *same budget* as top-K. Derived
    from training-set geometry, never from the test block.
    """
    per_session = n_train_rows / max(1, n_train_sessions)
    return float(min(1.0, k / per_session))


def oracle_global_precision(y: np.ndarray, s: np.ndarray, n_publish: int) -> float:
    """Precision of the BEST POSSIBLE global threshold at ``n_publish`` signals.

    This ranks the test scores themselves, so it is not a legitimate result --
    it is the upper bound any single global threshold could reach at that
    budget. Beating it is the only unambiguous win for a cross-sectional rule;
    losing to it is expected, and the honest comparison is against the
    training-chosen threshold.
    """
    y = np.asarray(y, dtype="float64")
    s = np.asarray(s, dtype="float64")
    n_publish = int(min(n_publish, len(s)))
    if n_publish <= 0:
        return float("nan")
    idx = np.argpartition(-s, n_publish - 1)[:n_publish]
    return float(y[idx].mean())


def oracle_global_mask(s: np.ndarray, n_publish: int) -> np.ndarray:
    """Mask of the ``n_publish`` highest scores in the block (oracle global rule).

    The oracle counterpart of :func:`topk_mask` at an equal signal budget: one
    global threshold, tuned on the block itself. Not a legitimate strategy --
    the yardstick a real cross-sectional rule must beat.
    """
    s = np.asarray(s, dtype="float64")
    n_publish = int(min(max(n_publish, 0), len(s)))
    mask = np.zeros(len(s), dtype=bool)
    if n_publish <= 0:
        return mask
    idx = np.argpartition(-s, n_publish - 1)[:n_publish]
    mask[idx] = True
    return mask


def paired_date_bootstrap(
    y: np.ndarray,
    dates: np.ndarray,
    mask_a: np.ndarray,
    mask_b: np.ndarray,
    universe_dates: np.ndarray | None = None,
    n_boot: int = 4000,
    seed: int = 0,
    block: int = 1,
    level: float = 0.95,
) -> dict:
    """Date-clustered CI for the DIFFERENCE in precision between two rules.

    ``mask_a`` and ``mask_b`` select overlapping rows from the same evaluated
    block, so the two precisions are strongly correlated: the marginal
    intervals of :func:`date_clustered_bootstrap` overlap even when A really is
    better. Resampling the SAME dates for both arms preserves that correlation
    and yields the paired interval, which is the correct test of "does rule A
    beat rule B?".

    Returns the point difference and the share of draws in which A beats B.
    """
    y = np.asarray(y, dtype="float64")
    dates = np.asarray(dates)
    mask_a = np.asarray(mask_a, dtype=bool)
    mask_b = np.asarray(mask_b, dtype=bool)
    if universe_dates is None:
        universe_dates = np.unique(dates)
    universe_dates = np.sort(np.asarray(universe_dates))
    n_days = len(universe_dates)

    ha, ca = _date_stats(y[mask_a], dates[mask_a], universe_dates)
    hb, cb = _date_stats(y[mask_b], dates[mask_b], universe_dates)

    rng = np.random.default_rng(seed)
    if block <= 1:
        idx = rng.integers(0, n_days, size=(n_boot, n_days))
    else:
        n_blocks = int(np.ceil(n_days / block))
        starts = rng.integers(0, n_days, size=(n_boot, n_blocks))
        offs = np.arange(block)
        idx = (starts[:, :, None] + offs[None, None, :]) % n_days
        idx = idx.reshape(n_boot, -1)

    CA = ca[idx].sum(axis=1)
    CB = cb[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        pa = np.where(CA > 0, ha[idx].sum(axis=1) / np.maximum(CA, 1e-12), np.nan)
        pb = np.where(CB > 0, hb[idx].sum(axis=1) / np.maximum(CB, 1e-12), np.nan)
    delta = pa - pb
    ok = np.isfinite(delta)
    delta = delta[ok]

    point_a = float(y[mask_a].mean()) if mask_a.any() else float("nan")
    point_b = float(y[mask_b].mean()) if mask_b.any() else float("nan")
    alpha = (1.0 - level) / 2.0
    return {
        "n_signals_a": int(mask_a.sum()),
        "n_signals_b": int(mask_b.sum()),
        "precision_a": point_a,
        "precision_b": point_b,
        "delta": (
            point_a - point_b
            if np.isfinite(point_a) and np.isfinite(point_b) else float("nan")
        ),
        "ci_low": float(np.quantile(delta, alpha)) if len(delta) else float("nan"),
        "ci_high": float(np.quantile(delta, 1 - alpha)) if len(delta) else float("nan"),
        "boot_mean": float(delta.mean()) if len(delta) else float("nan"),
        "boot_sd": float(delta.std()) if len(delta) else float("nan"),
        "share_draws_a_better": float((delta > 0).mean()) if len(delta) else float("nan"),
        "excludes_zero": bool(
            len(delta) and (np.quantile(delta, alpha) > 0 or np.quantile(delta, 1 - alpha) < 0)
        ),
        "n_dates": int(n_days),
        "n_boot": int(n_boot),
        "block": int(block),
        "level": float(level),
    }


def rate_curve(
    y: np.ndarray,
    s: np.ndarray,
    counts: list[int] | np.ndarray,
) -> list[dict]:
    """Oracle global-threshold precision at a series of signal budgets."""
    y = np.asarray(y, dtype="float64")
    s = np.asarray(s, dtype="float64")
    out = []
    n = len(y)
    order = np.argsort(-s)
    ys = y[order]
    csum = np.cumsum(ys)
    for c in counts:
        c = int(min(max(c, 1), n))
        out.append({"n_signals": c, "precision": float(csum[c - 1] / c)})
    return out


# ---------------------------------------------------------------------------
# top-K pooling helpers
# ---------------------------------------------------------------------------
def pool_folds(per_fold: list[dict], key: str = "n_signals", pkey: str = "precision") -> dict:
    """Signal-weighted pooling across folds, matching ``wf.summarise``."""
    ok = [r for r in per_fold if r.get(key, 0) > 0 and np.isfinite(r.get(pkey, np.nan))]
    if not ok:
        return {"n_signals": 0, "precision": float("nan")}
    n = sum(r[key] for r in ok)
    hits = sum(r[pkey] * r[key] for r in ok)
    return {
        "n_signals": int(n),
        "precision": float(hits / n),
        "n_folds": len(ok),
        "per_fold": [r[pkey] for r in ok],
        "per_fold_signals": [r[key] for r in ok],
    }
