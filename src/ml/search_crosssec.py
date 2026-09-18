"""Does per-session CROSS-SECTIONAL ranking beat a pooled global threshold?

The published pooled baseline on this matrix is 15.98% out-of-sample precision
(``reports/ml_search_models.json``, ``fam_hgb_0``: HGB defaults, all 82
features, ``label_high``, target_rate 0.02). That number comes from one global
probability threshold chosen on training scores. It conflates two different
abilities: the ability to say *this name is likely to move* (a level statement,
which depends on day-level calibration) and the ability to say *this name is a
better bet than the others trading today* (a ranking statement, which does not).

This script separates them. For every walk-forward fold it fits the identical
model, then evaluates:

1. **Per-session top-K.** Pick the best K names each session, K in
   (1, 3, 5, 10, 20, 50). No global threshold at all. This is the direct test of
   within-day ranking quality.
2. **Session-relative thresholds.** Convert the score to a within-session
   percentile and threshold *that*, comparing against the raw-probability
   threshold at a matched publication rate.
3. **Matched-budget global baselines.** For each K, the best global threshold
   that publishes the same NUMBER of signals on the test block (an oracle upper
   bound for any global rule), and the training-chosen global threshold at the
   same nominal rate (the honest operational rule).
4. **Date-clustered inference.** Bootstrap by resampling DATES, both plain and
   in blocks of 5 sessions, plus Wilson intervals and a Herfindahl/leave-one-
   date-out fragility report.

Nested K selection
------------------
Reporting the best K over a grid measured on the test block would be exactly the
error this repository exists to avoid. So the headline number comes from a
NESTED protocol: inside each fold's training block the last 25% of sessions
(with the usual purge) act as an inner validation block, K is chosen there, and
only then is it applied to the untouched test block. The full grid is still
printed, but it is labelled as a diagnostic, not as a result.

Nothing on or after 2026-01-01 is read: ``crosssec.build_folds`` passes the
final-holdout cut-off straight through to ``walkforward.folds``.

Usage
-----
    $env:PYTHONPATH='.'
    python -m src.ml.search_crosssec                  # primary config, full run
    python -m src.ml.search_crosssec --quick          # fewer bootstrap draws
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import crosssec as xs
from src.ml import walkforward as wf

# A PRIOR published baseline, kept only as a printed reference point.
#
# This value (15.98%) is the fam_hgb_0 pooled walk-forward precision measured on
# the STRIDE-5 matrix (281,227 out-of-sample rows). The comparisons this module
# makes do NOT use it: every delta is computed against the baseline produced by
# the run in progress (`res["global_threshold"]["precision"]`), on the same
# matrix, the same test rows and the same scores. That is the number that must be
# used, and it is what `equal_budget_vs_baseline` already reads.
#
# It is named for its population so it cannot be mistaken for a like-for-like
# figure. On the dense stride-1 grid the same config scores ~16.44%, so printing
# 15.98% beside a dense-grid run would be a silent cross-population comparison.
# `main()` now prints the difference explicitly, and the payload records the
# provenance, so the two are never confused.
PRIOR_STRIDE5_POOLED_BASELINE_OOS_PRECISION = 0.15977653631284916
PRIOR_STRIDE5_BASELINE_PROVENANCE = {
    "config": "fam_hgb_0",
    "population": "stride-5",
    "matrix": "matrix_h10_t30_s5.parquet",
    "oos_rows": 281227,
    "note": "printed for reference only; all deltas use the in-run baseline",
}
POOLED_BASELINE_CONFIG = "fam_hgb_0"
POOLED_BASELINE_TARGET_RATE = 0.02

# Configs to run. The first reproduces the published baseline exactly; the rest
# are robustness variants so a conclusion is not tied to one learner setting.
CONFIGS = {
    "fam_hgb_0": wf.Config(
        name="fam_hgb_0", model="hgb", params={},
        label="label_high", target_rate=POOLED_BASELINE_TARGET_RATE,
    ),
    "fam_hgb_1": wf.Config(
        name="fam_hgb_1", model="hgb",
        params={"max_leaf_nodes": 7, "min_samples_leaf": 100, "learning_rate": 0.05},
        label="label_high", target_rate=POOLED_BASELINE_TARGET_RATE,
    ),
}


# ---------------------------------------------------------------------------
# diagnostics that do not need the fold structure
# ---------------------------------------------------------------------------
def session_auc(frame: pd.DataFrame, y_col: str, score_col: str = "score") -> dict:
    """Mean within-session AUC and pooled AUC, to see which the model has.

    A model can have a strong pooled AUC purely by knowing which days are hot
    while ranking at chance inside a day; that pattern scores well on a global
    threshold and produces nothing on top-K. The gap between the two numbers is
    the whole question.
    """
    from sklearn.metrics import roc_auc_score

    y = frame[y_col].to_numpy("float64")
    s = frame[score_col].to_numpy("float64")
    pooled = float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else float("nan")

    aucs, weights = [], []
    for _, part in frame.groupby("date", sort=False):
        yy = part[y_col].to_numpy("float64")
        if len(np.unique(yy)) < 2:
            continue
        aucs.append(roc_auc_score(yy, part[score_col].to_numpy("float64")))
        weights.append(len(part))
    aucs = np.asarray(aucs, dtype="float64")
    weights = np.asarray(weights, dtype="float64")
    return {
        "pooled_auc": pooled,
        "mean_session_auc": float(aucs.mean()) if len(aucs) else float("nan"),
        "weighted_session_auc": (
            float((aucs * weights).sum() / weights.sum()) if len(aucs) else float("nan")
        ),
        "median_session_auc": float(np.median(aucs)) if len(aucs) else float("nan"),
        "share_sessions_auc_above_half": float(np.mean(aucs > 0.5)) if len(aucs) else float("nan"),
        "n_sessions": int(len(aucs)),
    }


# ---------------------------------------------------------------------------
# score caching (optimisation only; never changes a measured number)
# ---------------------------------------------------------------------------
def _fit_scores_cached(
    train: pd.DataFrame,
    test: pd.DataFrame,
    cfg: wf.Config,
    seed: int,
    cache_dir: Path | str | None,
    fold_key: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``xs.fit_scores`` with an optional on-disk cache of the scored frames.

    The cache key includes the fold, the label column, the model, its params and
    the seed, so scores produced by a different configuration can never be
    mistaken for these. A corrupt or unreadable cache entry is discarded rather
    than trusted.
    """
    if cache_dir is None or not fold_key:
        return xs.fit_scores(train, test, cfg, seed)

    keys = "_".join(
        f"{k}={cfg.params[k]}" for k in sorted(cfg.params)
    )
    tag = f"{fold_key}__{cfg.label}__{cfg.model}__{keys}__s{seed}"
    tag = "".join(c if (c.isalnum() or c in "-_=.") else "_" for c in tag)
    path_tr = Path(cache_dir) / f"{tag}__train.parquet"
    path_te = Path(cache_dir) / f"{tag}__test.parquet"

    if path_tr.exists() and path_te.exists():
        try:
            return pd.read_parquet(path_tr), pd.read_parquet(path_te)
        except Exception:  # noqa: BLE001 - a broken cache must not stop the run
            pass

    s_tr, s_te = xs.fit_scores(train, test, cfg, seed)
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        s_tr.to_parquet(path_tr, index=False)
        s_te.to_parquet(path_te, index=False)
    except Exception:  # noqa: BLE001 - caching is optional
        pass
    return s_tr, s_te


# ---------------------------------------------------------------------------
# nested K selection inside a training block
# ---------------------------------------------------------------------------
def select_k_on_train(
    train: pd.DataFrame,
    cfg: wf.Config,
    k_grid: tuple[int, ...],
    folds: int = 3,
    purge: int = 12,
    min_signals: int = 40,
    seed: int = 0,
    cache_dir: Path | str | None = None,
    fold_key: str = "",
) -> dict:
    """Choose K using ONLY the training block, by rolling inner validation.

    The training block is split into ``folds`` contiguous inner blocks. For each
    one the model is refit on everything before it (minus a purge) and K is
    scored on it. K is then the grid point with the best signal-weighted inner
    precision among those with at least ``min_signals``. Falls back to K=5 when
    nothing qualifies, so the rule is total and deterministic.
    """
    sessions = np.sort(train["date"].unique())
    n = len(sessions)
    if n < 200:
        return {"k": 5, "reason": "training block too short", "inner": []}
    edges = np.linspace(0, n, folds + 1).astype(int)
    totals = {k: [0.0, 0] for k in k_grid}
    inner_log = []
    for i in range(folds):
        block = sessions[edges[i]:edges[i + 1]]
        if len(block) == 0:
            continue
        first = block[0]
        boundary = int(np.searchsorted(sessions, first))
        safe_end = max(0, boundary - purge)
        tr_sessions = sessions[:safe_end]
        if len(tr_sessions) < 150:
            continue
        sub_tr = train[train["date"].isin(tr_sessions)]
        sub_te = train[train["date"].isin(block)]
        if len(sub_te) < 200:
            continue
        try:
            _, scored = _fit_scores_cached(
                sub_tr, sub_te, cfg, seed, cache_dir,
                f"{fold_key}_inner{i}" if fold_key else "",
            )
        except ValueError:
            continue
        y = scored[cfg.label].to_numpy("float64")
        hits = y
        row = {"block_start": str(pd.Timestamp(block[0]).date()),
               "n_sessions": int(len(block)), "n_rows": int(len(scored))}
        for k in k_grid:
            m = xs.topk_mask(scored, k)
            n_sig = int(m.sum())
            p = xs.precision(y, m)
            row[f"k{k}_precision"] = p
            row[f"k{k}_signals"] = n_sig
            if np.isfinite(p) and n_sig > 0:
                totals[k][0] += p * n_sig
                totals[k][1] += n_sig
        inner_log.append(row)

    scored_k = []
    for k in k_grid:
        hits_k, n_k = totals[k]
        scored_k.append({
            "k": int(k),
            "n_signals": int(n_k),
            "precision": float(hits_k / n_k) if n_k else float("nan"),
        })
    eligible = [r for r in scored_k if r["n_signals"] >= min_signals
                and np.isfinite(r["precision"])]
    if eligible:
        best = max(eligible, key=lambda r: (r["precision"], -r["k"]))
        return {"k": int(best["k"]), "reason": "best inner validation precision",
                "inner": scored_k, "inner_blocks": inner_log,
                "train_base_rate": float(
                    train.loc[train[cfg.label].notna(), cfg.label].mean()
                )}
    return {"k": 5, "reason": "no grid point reached min_signals", "inner": scored_k,
            "inner_blocks": inner_log}


# ---------------------------------------------------------------------------
# one fold, all selection rules
# ---------------------------------------------------------------------------
def evaluate_fold_xs(
    train: pd.DataFrame,
    test: pd.DataFrame,
    cfg: wf.Config,
    k_grid: tuple[int, ...],
    p_grid: tuple[float, ...],
    seed: int = 0,
    cache_dir: Path | str | None = None,
    fold_key: str = "",
) -> dict:
    """Fit once, then score every cross-sectional and global rule on the test block.

    ``cache_dir`` is an optimisation only: the train/test scored frames are
    written to ``<cache_dir>/<fold_key>.parquet`` and reused on a later run with
    the identical config, so downstream statistics can be recomputed without
    refitting. Cached frames are keyed by fold, label and model params, so a
    stale cache from a different config cannot be picked up silently.
    """
    s_tr, s_te = _fit_scores_cached(train, test, cfg, seed, cache_dir, fold_key)
    y_col = cfg.label
    y = s_te[y_col].to_numpy("float64")
    score = s_te["score"].to_numpy("float64")
    dates = s_te["date"].to_numpy()
    codes = s_te["code"].to_numpy()
    base = float(y.mean())

    out: dict = {
        "n_train": int(len(s_tr)),
        "n_test": int(len(s_te)),
        "n_test_sessions": int(s_te["date"].nunique()),
        "oos_base_rate": base,
        "insample_base_rate": float(s_tr[y_col].to_numpy("float64").mean()),
        "auc": session_auc(s_te, y_col),
    }

    # --- 0. in-sample side-by-side (the number that looks like 50% and is not
    # evidence). Top-K on the block the model was FIT on, same K grid. The model
    # has memorised these rows, so a high number here is expected and carries no
    # information about the test block.
    y_in = s_tr[y_col].to_numpy("float64")
    insample_topk = {}
    for k in k_grid:
        m = xs.topk_mask(s_tr, k)
        n_sig = int(m.sum())
        insample_topk[str(k)] = {
            "k": int(k),
            "n_signals": n_sig,
            "precision": xs.precision(y_in, m),
        }
    out["insample_topk"] = insample_topk
    thr_in = wf.pick_threshold(s_tr["score"].to_numpy("float64"), None, cfg.target_rate)
    m_in = s_tr["score"].to_numpy("float64") >= thr_in
    out["insample_global_threshold"] = {
        "n_signals": int(m_in.sum()),
        "precision": xs.precision(y_in, m_in),
        "share_of_rows": float(m_in.mean()),
    }

    # --- 1. per-session top-K -------------------------------------------
    topk = {}
    for k in k_grid:
        m = xs.topk_mask(s_te, k)
        n_sig = int(m.sum())
        p = xs.precision(y, m)
        topk[str(k)] = {
            "k": int(k),
            "n_signals": n_sig,
            "precision": p,
            "lift_vs_base": (p / base) if base > 0 and np.isfinite(p) else float("nan"),
            "wilson": xs.wilson(int(round(p * n_sig)) if np.isfinite(p) else 0, n_sig),
            "n_distinct_dates": int(pd.Index(dates[m]).nunique()) if n_sig else 0,
            "n_distinct_stocks": int(pd.Index(codes[m]).nunique()) if n_sig else 0,
        }
    out["topk"] = topk

    # --- 2. session-relative percentile thresholds -----------------------
    # Each grid point is given a head-to-head global baseline at the SAME
    # training-derived publication rate, so "does within-day normalisation
    # help?" is answered at equal budget rather than at an arbitrary rate.
    pct = xs.session_percentile(s_te)
    pct_tr = xs.session_percentile(s_tr)
    pctres = {}
    for q in p_grid:
        m = pct > q
        n_sig = int(m.sum())
        p = xs.precision(y, m)
        train_share = float((pct_tr > q).mean())
        thr_q = wf.pick_threshold(s_tr["score"].to_numpy("float64"), None, train_share)
        m_g = score >= thr_q
        pctres[str(q)] = {
            "q": float(q),
            "n_signals": n_sig,
            "precision": p,
            "share_of_rows": float(m.mean()),
            "global_same_rate": float(train_share),
            "global_signals": int(m_g.sum()),
            "global_precision": xs.precision(y, m_g),
            "delta_vs_global_same_rate": (
                p - xs.precision(y, m_g) if n_sig and m_g.sum() else float("nan")
            ),
        }
    out["session_percentile"] = pctres

    # --- 3. global baselines --------------------------------------------
    # (a) the harness rule: threshold from training scores at target_rate
    thr = wf.pick_threshold(s_tr["score"].to_numpy("float64"), None,
                            cfg.target_rate)
    m_glob = score >= thr
    n_glob = int(m_glob.sum())
    out["global_threshold"] = {
        "threshold": float(thr),
        "target_rate": cfg.target_rate,
        "n_signals": n_glob,
        "precision": xs.precision(y, m_glob),
        "wilson": xs.wilson(int(y[m_glob].sum()), n_glob),
        "n_distinct_dates": int(pd.Index(dates[m_glob]).nunique()) if n_glob else 0,
        "n_distinct_stocks": int(pd.Index(codes[m_glob]).nunique()) if n_glob else 0,
    }

    # (b) matched-budget: for every top-K budget, the BEST global threshold at
    # the same signal count (oracle) and the training-chosen threshold at the
    # same nominal rate (operational).
    matched = {}
    for k in k_grid:
        budget = topk[str(k)]["n_signals"]
        if budget <= 0:
            continue
        oracle = xs.oracle_global_precision(y, score, budget)
        rate = xs.matched_rate_for_topk(
            k, len(s_tr), max(1, int(s_tr["date"].nunique()))
        )
        thr_m = wf.pick_threshold(s_tr["score"].to_numpy("float64"), None, rate)
        m_m = score >= thr_m
        matched[str(k)] = {
            "k": int(k),
            "budget": int(budget),
            "target_rate": float(rate),
            "oracle_global_precision": oracle,
            "oracle_global_signals": int(budget),
            "train_threshold_precision": xs.precision(y, m_m),
            "train_threshold_signals": int(m_m.sum()),
            "topk_precision": topk[str(k)]["precision"],
            "topk_minus_oracle": (
                topk[str(k)]["precision"] - oracle
                if np.isfinite(oracle) else float("nan")
            ),
            "topk_minus_train_threshold": (
                topk[str(k)]["precision"] - xs.precision(y, m_m)
                if np.isfinite(xs.precision(y, m_m)) else float("nan")
            ),
        }
    out["matched_budget"] = matched

    # --- 4. scoring frames for pooled inference --------------------------
    out["_y"] = y
    out["_score"] = score
    out["_dates"] = dates
    out["_codes"] = codes
    out["_pct"] = pct
    # The harness baseline's own mask, kept so the pooled step can run a PAIRED
    # date-clustered test of a cross-sectional rule against it.
    out["_mask_global"] = m_glob
    return out


# ---------------------------------------------------------------------------
# pooling and inference
# ---------------------------------------------------------------------------
def pool_with_inference(folds: list[dict], n_boot: int, seed: int, block: int = 1) -> dict:
    """Concatenate test blocks and compute pooled statistics + clustered CIs."""
    y = np.concatenate([f["_y"] for f in folds])
    score = np.concatenate([f["_score"] for f in folds])
    dates = np.concatenate([f["_dates"] for f in folds])
    codes = np.concatenate([f["_codes"] for f in folds])
    pct = np.concatenate([f["_pct"] for f in folds])
    base = float(y.mean())
    universe_dates = np.unique(dates)

    res: dict = {"oos_base_rate": base, "n_rows": int(len(y)),
                 "n_test_sessions": int(len(universe_dates)),
                 "n_folds": len(folds)}

    # --- in-sample pooled reference --------------------------------------
    ins_p, ins_sig = _weighted([
        (f["insample_global_threshold"]["precision"],
         f["insample_global_threshold"]["n_signals"]) for f in folds
    ])
    res["insample_base_rate"] = float(
        np.mean([f["insample_base_rate"] for f in folds])
    )
    res["insample_topk"] = {}
    for k in sorted({r["k"] for f in folds for r in f["insample_topk"].values()}):
        p, n_sig = _weighted([
            (f["insample_topk"][str(k)]["precision"],
             f["insample_topk"][str(k)]["n_signals"]) for f in folds
        ])
        res["insample_topk"][str(k)] = {
            "k": int(k), "n_signals": int(n_sig), "precision": p,
        }
    res["insample_global_threshold"] = {
        "n_signals": int(ins_sig),
        "precision": ins_p,
        "share_of_rows": float(np.mean(
            [(f["insample_global_threshold"]["n_signals"] / f["n_train"]) for f in folds]
        )),
    }

    topk = {}
    for k in sorted({r["k"] for f in folds for r in f["topk"].values()}):
        m = xs.topk_mask(pd.DataFrame({"date": dates, "score": score}), k)
        n_sig = int(m.sum())
        p = xs.precision(y, m)
        h = y[m]
        ci1 = xs.date_clustered_bootstrap(h, dates[m], universe_dates,
                                          n_boot=n_boot, seed=seed, block=1)
        ci5 = xs.date_clustered_bootstrap(h, dates[m], universe_dates,
                                          n_boot=n_boot, seed=seed, block=5)
        conc = xs.concentration(h, dates[m], codes[m])
        wl, wh = xs.wilson(int(h.sum()), n_sig)
        topk[str(k)] = {
            "k": int(k),
            "n_signals": n_sig,
            "precision": p,
            "lift_vs_base": p / base if base > 0 else float("nan"),
            "wilson_low": wl, "wilson_high": wh,
            "dates_ci": ci1, "dates_ci_block5": ci5,
            "concentration": conc,
            "excludes_base_plain": bool(ci1["ci_low"] > base),
            "excludes_base_block5": bool(ci5["ci_low"] > base),
            "insample_precision": res["insample_topk"][str(k)]["precision"],
            "insample_signals": res["insample_topk"][str(k)]["n_signals"],
            "nested_selected": False,
        }
    res["topk"] = topk

    # --- session percentile pooled ---------------------------------------
    pctres = {}
    for q in sorted({r["q"] for f in folds for r in f["session_percentile"].values()}):
        m = pct > q
        n_sig = int(m.sum())
        p = xs.precision(y, m)
        h = y[m]
        ci1 = xs.date_clustered_bootstrap(h, dates[m], universe_dates,
                                          n_boot=n_boot, seed=seed, block=1)
        conc = xs.concentration(h, dates[m], codes[m])
        g_p, g_n = _weighted([
            (f["session_percentile"][str(q)]["global_precision"],
             f["session_percentile"][str(q)]["global_signals"]) for f in folds
        ])
        pctres[str(q)] = {
            "q": float(q), "n_signals": n_sig, "precision": p,
            "share_of_rows": float(m.mean()),
            "wilson": xs.wilson(int(h.sum()), n_sig),
            "dates_ci": ci1,
            "excludes_base_plain": bool(ci1["ci_low"] > base),
            "n_distinct_dates": conc.get("n_distinct_dates", 0),
            "n_distinct_stocks": conc.get("n_distinct_stocks", 0),
            "global_signals": int(g_n),
            "global_precision": g_p,
            "delta_vs_global_same_rate": (
                p - g_p if n_sig and g_n and np.isfinite(g_p) else float("nan")
            ),
        }
    res["session_percentile"] = pctres

    # --- global baselines pooled -----------------------------------------
    thr_p, thr_sig = _weighted([
        (f["global_threshold"]["precision"], f["global_threshold"]["n_signals"])
        for f in folds
    ])
    res["global_threshold"] = {
        "n_signals": int(thr_sig),
        "precision": thr_p,
        "lift_vs_base": thr_p / base if base > 0 else float("nan"),
        "wilson": xs.wilson(int(round(thr_p * thr_sig)) if thr_sig else 0, thr_sig),
    }

    matched = {}
    for k in sorted({r["k"] for f in folds for r in f["matched_budget"].values()}):
        orc, budget = _weighted([
            (f["matched_budget"][str(k)]["oracle_global_precision"],
             f["matched_budget"][str(k)]["budget"]) for f in folds
        ])
        tt_p, tt_sig = _weighted([
            (f["matched_budget"][str(k)]["train_threshold_precision"],
             f["matched_budget"][str(k)]["train_threshold_signals"]) for f in folds
        ])
        # Paired, date-clustered test against the same-budget ORACLE global rule.
        # This is the decisive comparison: if top-K does not beat a global
        # threshold that is allowed to tune itself on the test block at the same
        # signal count, then the cross-sectional rule adds no information beyond
        # choosing a stricter operating point.
        mask_k = xs.topk_mask(pd.DataFrame({"date": dates, "score": score}), k)
        mask_o = _oracle_mask_by_fold(folds, _topk_budget_by_fold(folds, k))
        paired_oracle = xs.paired_date_bootstrap(
            y, dates, mask_k, mask_o, universe_dates,
            n_boot=n_boot, seed=seed, block=1,
        )
        paired_oracle_b5 = xs.paired_date_bootstrap(
            y, dates, mask_k, mask_o, universe_dates,
            n_boot=n_boot, seed=seed, block=5,
        )
        matched[str(k)] = {
            "k": int(k),
            "budget": int(budget),
            "oracle_global_precision": orc,
            "train_threshold_precision": tt_p,
            "train_threshold_signals": int(tt_sig),
            "topk_precision": topk[str(k)]["precision"],
            "topk_minus_oracle": (
                topk[str(k)]["precision"] - orc
                if np.isfinite(orc) else float("nan")
            ),
            "topk_minus_train_threshold": (
                topk[str(k)]["precision"] - tt_p
                if np.isfinite(tt_p) else float("nan")
            ),
            "topk_vs_oracle_ratio": (
                topk[str(k)]["precision"] / orc
                if np.isfinite(orc) and orc else float("nan")
            ),
            "paired_vs_oracle": paired_oracle,
            "paired_vs_oracle_block5": paired_oracle_b5,
            "beats_oracle_same_budget": bool(
                np.isfinite(paired_oracle["delta"]) and paired_oracle["ci_low"] > 0
            ),
        }
        # Self-consistency: the paired test must centre on the same point
        # estimate as the reported per-fold oracle precision. A mismatch means
        # the two were built from different objects.
        assert abs(paired_oracle["precision_b"] - matched[str(k)]["oracle_global_precision"]) < 1e-9, (
            f"paired oracle arm ({paired_oracle['precision_b']}) disagrees with "
            f"matched_budget oracle ({matched[str(k)]['oracle_global_precision']})"
        )
    res["matched_budget"] = matched

    # Pooled rule that publishes the SAME NUMBER of signals as the harness
    # baseline, but chosen per session (K from the baseline's observed
    # signals-per-session). This is the apples-to-apples answer to "does
    # cross-sectional selection beat the 15.98% global threshold at equal signal
    # count?". top-``k_equiv`` is built per fold so each fold's budget is exact.
    n_base = res["global_threshold"]["n_signals"]
    n_sess = len(universe_dates)
    k_equiv = max(1, int(round(n_base / max(1, n_sess))))
    mask_eq_parts = [
        xs.topk_mask(pd.DataFrame({"date": f["_dates"], "score": f["_score"]}), k_equiv)
        for f in folds
    ]
    mask_eq = np.concatenate(mask_eq_parts)
    mask_base = np.concatenate([f["_mask_global"] for f in folds])
    mask_eq_orc = _oracle_mask_by_fold(
        folds,
        [int(m.sum()) for m in mask_eq_parts],
    )
    paired_base = xs.paired_date_bootstrap(
        y, dates, mask_eq, mask_base, universe_dates, n_boot=n_boot, seed=seed, block=1
    )
    paired_base_b5 = xs.paired_date_bootstrap(
        y, dates, mask_eq, mask_base, universe_dates, n_boot=n_boot, seed=seed, block=5
    )
    paired_eq_orc = xs.paired_date_bootstrap(
        y, dates, mask_eq, mask_eq_orc, universe_dates, n_boot=n_boot, seed=seed, block=1
    )
    paired_eq_orc_b5 = xs.paired_date_bootstrap(
        y, dates, mask_eq, mask_eq_orc, universe_dates, n_boot=n_boot, seed=seed, block=5
    )
    res["equal_budget_vs_baseline"] = {
        "baseline_signals": int(n_base),
        "baseline_precision": res["global_threshold"]["precision"],
        "k_equivalent": int(k_equiv),
        "topk_signals": int(mask_eq.sum()),
        "topk_precision": xs.precision(y, mask_eq),
        "topk_wilson": xs.wilson(int(y[mask_eq].sum()), int(mask_eq.sum())),
        "delta_vs_baseline": (
            xs.precision(y, mask_eq) - res["global_threshold"]["precision"]
        ),
        "paired_vs_baseline": paired_base,
        "paired_vs_baseline_block5": paired_base_b5,
        "paired_vs_oracle_same_budget": paired_eq_orc,
        "paired_vs_oracle_same_budget_block5": paired_eq_orc_b5,
        "beats_oracle_same_budget": bool(
            np.isfinite(paired_eq_orc["delta"]) and paired_eq_orc["ci_low"] > 0
        ),
        "beats_baseline": bool(
            np.isfinite(paired_base["delta"]) and paired_base["ci_low"] > 0
        ),
        "note": (
            "Paired date-clustered test of top-K against the harness baseline's "
            "OWN mask. Not a matched-budget comparison: the two masks publish "
            f"{'more' if int(mask_eq.sum()) > int(n_base) else 'fewer'} signals "
            f"at top-K ({int(mask_eq.sum()):,}) than the baseline "
            f"({int(n_base):,}), so a positive delta here reflects both ranking "
            "quality and the different operating point. The decisive equal-budget "
            "comparison is paired_vs_oracle in matched_budget."
        ),
    }
    res["equal_budget_vs_baseline"]["topk_dates_ci"] = xs.date_clustered_bootstrap(
        y[mask_eq], dates[mask_eq], universe_dates, n_boot=n_boot, seed=seed, block=1
    )
    res["equal_budget_vs_baseline"]["topk_dates_ci_block5"] = xs.date_clustered_bootstrap(
        y[mask_eq], dates[mask_eq], universe_dates, n_boot=n_boot, seed=seed, block=5
    )

    # --- oracle rate curve: best global precision at any budget ----------
    counts = sorted({int(m["budget"]) for m in matched.values()})
    res["oracle_rate_curve"] = xs.rate_curve(y, score, counts)
    res["_y"], res["_score"], res["_dates"], res["_codes"], res["_pct"] = (
        y, score, dates, codes, pct
    )
    return res


def _oracle_mask_by_fold(folds: list[dict], budgets: list[int]) -> np.ndarray:
    """Concatenated ORACLE global mask, built independently inside each fold.

    The model is refit per fold, so each fold has its own score scale; a global
    threshold is therefore also a per-fold object (``wf.pick_threshold`` is
    called per fold for the same reason). Building the oracle on a single pooled
    score vector would instead let one fold's systematically higher scores swallow
    the entire budget, which is not the rule this is meant to bound. The
    per-fold construction also makes the paired test's point estimate identical
    to the ``topk_minus_oracle`` column of ``matched_budget``.

    ``budgets`` gives the signal budget for each fold, so the caller can match a
    rule that is not in the reported grid.
    """
    if len(budgets) != len(folds):
        raise ValueError(f"{len(budgets)} budgets for {len(folds)} folds")
    return np.concatenate([
        xs.oracle_global_mask(f["_score"], int(b))
        for f, b in zip(folds, budgets)
    ])


def _topk_budget_by_fold(folds: list[dict], k: int) -> list[int]:
    """Signals top-``k`` would publish in each fold, from the recorded counters."""
    out = []
    for f in folds:
        rec = f["topk"].get(str(k))
        out.append(int(rec["n_signals"]) if rec else 0)
    return out


def strip_private(obj):
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    return obj


def _weighted(pairs: list[tuple[float, int]]) -> tuple[float, int]:
    """Signal-weighted mean of (precision, n_signals) pairs.

    Folds whose threshold published nothing carry ``nan`` precision; multiplying
    that by a zero signal count yields ``nan`` and silently poisons the whole
    pooled sum. Non-finite or empty entries are therefore dropped, which is the
    only honest treatment: they contribute no signals and no hits.
    """
    n = 0
    hits = 0.0
    for p, k in pairs:
        k = int(k)
        if k <= 0 or not np.isfinite(p):
            continue
        n += k
        hits += p * k
    return (float(hits / n) if n else float("nan")), n


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def run_config(
    frame: pd.DataFrame,
    cfg: wf.Config,
    k_grid: tuple[int, ...],
    p_grid: tuple[float, ...],
    n_boot: int,
    seed: int,
    verbose: bool = True,
    cache_dir: Path | str | None = None,
) -> dict:
    folds = xs.build_folds(frame)
    per_fold, nested = [], []
    t0 = time.time()
    for i, fold in enumerate(folds, 1):
        train = frame[frame["date"].isin(fold.train_sessions)]
        test = frame[frame["date"].isin(fold.test_sessions)]
        res = evaluate_fold_xs(train, test, cfg, k_grid, p_grid, seed,
                               cache_dir=cache_dir, fold_key=fold.name)
        per_fold.append(res)
        # Nested K, chosen on the training block only.
        sel = select_k_on_train(train, cfg, k_grid, seed=seed,
                                cache_dir=cache_dir, fold_key=fold.name)
        nested.append(sel)
        if verbose:
            kk = sel["k"]
            m = xs.topk_mask(
                pd.DataFrame({"date": res["_dates"], "score": res["_score"]}), kk
            )
            print(
                f"  fold {i}/{len(folds)} {fold.name}  "
                f"k*={kk:<3d} nested top-{kk} OOS "
                f"{xs.precision(res['_y'], m) * 100:6.2f}% ({int(m.sum())} sig)  "
                f"global {res['global_threshold']['precision'] * 100:6.2f}%  "
                f"[{time.time() - t0:5.1f}s]",
                flush=True,
            )

    pooled = pool_with_inference(per_fold, n_boot=n_boot, seed=seed)

    # Nested pooled number: apply each fold's OWN chosen K to that fold's test
    # block, then pool. This is the only headline allowed to be called a result.
    nested_parts = []
    for res, sel in zip(per_fold, nested):
        k = sel["k"]
        m = xs.topk_mask(
            pd.DataFrame({"date": res["_dates"], "score": res["_score"]}), k
        )
        nested_parts.append((k, res["_y"], m, res["_dates"], res["_codes"]))
    if nested_parts:
        ys = np.concatenate([p[1][p[2]] for p in nested_parts])
        ds = np.concatenate([p[3][p[2]] for p in nested_parts])
        cs = np.concatenate([p[4][p[2]] for p in nested_parts])
        universe = np.unique(np.concatenate([p[3] for p in nested_parts]))
        ci1 = xs.date_clustered_bootstrap(ys, ds, universe, n_boot=n_boot,
                                          seed=seed, block=1)
        ci5 = xs.date_clustered_bootstrap(ys, ds, universe, n_boot=n_boot,
                                          seed=seed, block=5)
        conc = xs.concentration(ys, ds, cs)
        # Paired tests need the FULL pooled test block, not just the selected
        # rows: pool_with_inference keeps it in its private fields.
        y_all = pooled["_y"]
        score_all = pooled["_score"]
        dates_all = pooled["_dates"]
        universe_all = np.unique(dates_all)
        # Rebuild the nested mask positionally over the concatenated pool: the
        # nested rule chose a different K per fold, so it cannot be expressed as
        # one global score threshold or a single K.
        off = 0
        mask_n = np.zeros(len(y_all), dtype=bool)
        for p in nested_parts:
            n_f = len(p[1])
            mask_n[off:off + n_f] = p[2]
            off += n_f
        mask_n_orc = _oracle_mask_by_fold(per_fold, [int(p[2].sum()) for p in nested_parts])
        paired_n_orc = xs.paired_date_bootstrap(
            y_all, dates_all, mask_n, mask_n_orc, universe_all,
            n_boot=n_boot, seed=seed, block=1,
        )
        paired_n_orc_b5 = xs.paired_date_bootstrap(
            y_all, dates_all, mask_n, mask_n_orc, universe_all,
            n_boot=n_boot, seed=seed, block=5,
        )
        mask_n_base = np.concatenate([f["_mask_global"] for f in per_fold])
        paired_n_base = xs.paired_date_bootstrap(
            y_all, dates_all, mask_n, mask_n_base, universe_all,
            n_boot=n_boot, seed=seed, block=1,
        )
        paired_n_base_b5 = xs.paired_date_bootstrap(
            y_all, dates_all, mask_n, mask_n_base, universe_all,
            n_boot=n_boot, seed=seed, block=5,
        )
        pooled["nested"] = {
            "k_per_fold": [p[0] for p in nested_parts],
            "k_selection": [s["reason"] for s in nested],
            "n_signals": int(len(ys)),
            "precision": float(ys.mean()),
            "lift_vs_base": float(ys.mean() / pooled["oos_base_rate"]),
            "wilson": xs.wilson(int(ys.sum()), len(ys)),
            "dates_ci": ci1,
            "dates_ci_block5": ci5,
            "concentration": conc,
            "excludes_base_plain": bool(ci1["ci_low"] > pooled["oos_base_rate"]),
            "excludes_base_block5": bool(ci5["ci_low"] > pooled["oos_base_rate"]),
            "paired_vs_oracle_same_budget": paired_n_orc,
            "paired_vs_oracle_same_budget_block5": paired_n_orc_b5,
            "paired_vs_baseline": paired_n_base,
            "paired_vs_baseline_block5": paired_n_base_b5,
            "beats_oracle_same_budget": bool(
                np.isfinite(paired_n_orc["delta"]) and paired_n_orc["ci_low"] > 0
            ),
            "beats_baseline": bool(
                np.isfinite(paired_n_base["delta"]) and paired_n_base["ci_low"] > 0
            ),
        }

    pooled["config"] = cfg.name
    pooled["model"] = cfg.model
    pooled["label"] = cfg.label
    pooled["params"] = cfg.params
    pooled["nested_selection"] = [
        {k: v for k, v in s.items() if k != "inner_blocks"} for s in nested
    ]
    pooled["per_fold_summary"] = [
        {
            "nested_k": s["k"],
            "oos_base_rate": r["oos_base_rate"],
            "global_threshold_precision": r["global_threshold"]["precision"],
            "global_threshold_signals": r["global_threshold"]["n_signals"],
            "auc": r["auc"],
            "topk": {k: {"n_signals": v["n_signals"], "precision": v["precision"]}
                     for k, v in r["topk"].items()},
        }
        for r, s in zip(per_fold, nested)
    ]
    return pooled


def report(res: dict, k_grid: tuple[int, ...], n_boot: int) -> None:
    base = res["oos_base_rate"]
    print(f"\n{'=' * 78}")
    print(f"config {res['config']}   pooled OOS base rate {base * 100:.2f}%   "
          f"(in-sample base rate {res['insample_base_rate'] * 100:.2f}%)")
    print(f"{'=' * 78}")
    print("\n-- per-session top-K (pooled over folds) --")
    print(f"{'K':>4} {'signals':>8} {'OOS prec':>9} {'inSample':>9} {'lift':>6} "
          f"{'dates':>6} {'stocks':>7} {'HHI':>7} {'drop1d':>8} "
          f"{'CI95_lo':>8} {'CI95_hi':>8} {'excl':>5}")
    for k in k_grid:
        r = res["topk"].get(str(k))
        if not r:
            continue
        c = r["concentration"]
        print(f"{k:>4} {r['n_signals']:>8} {r['precision'] * 100:>8.2f}% "
              f"{r['insample_precision'] * 100:>8.2f}% {r['lift_vs_base']:>5.2f}x "
              f"{c['n_distinct_dates']:>6} {c['n_distinct_stocks']:>7} "
              f"{c['herfindahl_dates']:>7.4f} "
              f"{c['precision_drop_busiest_date'] * 100:>7.2f}% "
              f"{r['dates_ci']['ci_low'] * 100:>7.2f}% "
              f"{r['dates_ci']['ci_high'] * 100:>7.2f}% "
              f"{'YES' if r['excludes_base_plain'] else 'no':>5}")
    ig = res["insample_global_threshold"]
    print(f"  reference: global threshold on the SAME rating at rate "
          f"{POOLED_BASELINE_TARGET_RATE:g} -> in-sample {ig['precision'] * 100:.2f}% "
          f"({ig['n_signals']} sig) vs OOS "
          f"{res['global_threshold']['precision'] * 100:.2f}%")

    print("\n-- session-relative percentile threshold vs global at the same rate --")
    for q, r in sorted(res["session_percentile"].items(), key=lambda kv: float(kv[0])):
        r = res["session_percentile"][q]
        print(f"  top {(1 - float(q)) * 100:7.3f}% of each day -> {r['n_signals']:>6} sig, "
              f"precision {r['precision'] * 100:6.2f}%  "
              f"CI95 [{r['dates_ci']['ci_low'] * 100:5.2f}%, "
              f"{r['dates_ci']['ci_high'] * 100:5.2f}%]  "
              f"{'excludes' if r['excludes_base_plain'] else 'includes'} base  "
              f"| global same-rate {r['global_precision'] * 100:6.2f}% "
              f"({r['global_signals']} sig)  "
              f"delta {r['delta_vs_global_same_rate'] * 100:+6.2f}pp")

    print("\n-- matched-budget global baselines, with PAIRED date-clustered test --")
    print(f"{'K':>4} {'budget':>8} {'topK':>8} {'oracleGlob':>11} "
          f"{'K-orcl':>8} {'paired95':>20} {'K>orcl':>6} {'trainGlob':>10} {'trainSig':>9}")
    for k in k_grid:
        m = res["matched_budget"].get(str(k))
        if not m:
            continue
        print(f"{k:>4} {m['budget']:>8} {m['topk_precision'] * 100:>7.2f}% "
              f"{m['oracle_global_precision'] * 100:>10.2f}% "
              f"{m['topk_minus_oracle'] * 100:>+7.2f}% "
              f"[{m['paired_vs_oracle']['ci_low'] * 100:>+6.2f},"
              f"{m['paired_vs_oracle']['ci_high'] * 100:>+6.2f}]pp "
              f"{'YES' if m['beats_oracle_same_budget'] else 'no':>6} "
              f"{m['train_threshold_precision'] * 100:>9.2f}% "
              f"{m['train_threshold_signals']:>9}")
    for k in k_grid:
        m = res["matched_budget"].get(str(k))
        if not m:
            continue
        pi = m["paired_vs_oracle"]
        p5 = m["paired_vs_oracle_block5"]
        print(f"     K={k}: paired vs oracle block1 "
              f"[{pi['ci_low'] * 100:+.2f}, {pi['ci_high'] * 100:+.2f}]pp "
              f"P(topK better)={pi['share_draws_a_better']:.3f} excl0={pi['excludes_zero']} | "
              f"block5 [{p5['ci_low'] * 100:+.2f}, {p5['ci_high'] * 100:+.2f}]pp "
              f"excl0={p5['excludes_zero']}")

    g = res["global_threshold"]
    prior = PRIOR_STRIDE5_POOLED_BASELINE_OOS_PRECISION * 100
    now = g["precision"] * 100
    print(f"\n  harness global threshold@rate{POOLED_BASELINE_TARGET_RATE}: "
          f"{g['n_signals']} sig, precision {now:.2f}%")
    print(f"    in-run baseline for every delta above: {now:.2f}%")
    print(f"    prior published stride-5 baseline    : {prior:.2f}% "
          f"(different population; reference only)")
    print(f"    difference                           : {now - prior:+.2f} pp "
          f"-- expected if this run is on another grid")

    eb = res.get("equal_budget_vs_baseline")
    if eb:
        print(f"\n-- EQUAL-SIGNAL-COUNT vs the harness baseline --")
        print(f"  harness global rate{POOLED_BASELINE_TARGET_RATE}: "
              f"{eb['baseline_signals']} sig @ {eb['baseline_precision'] * 100:.2f}%")
        print(f"  per-session top-{eb['k_equivalent']}: {eb['topk_signals']} sig @ "
              f"{eb['topk_precision'] * 100:.2f}%  "
              f"delta {eb['delta_vs_baseline'] * 100:+.2f}pp  "
              f"CI95 [{eb['topk_dates_ci']['ci_low'] * 100:.2f}%, "
              f"{eb['topk_dates_ci']['ci_high'] * 100:.2f}%] "
              f"excl base: {eb['topk_dates_ci']['ci_low'] > res['oos_base_rate']}  "
              f"excl baseline point: "
              f"{eb['topk_dates_ci']['ci_low'] > eb['baseline_precision']}")
        pb = eb["paired_vs_baseline"]
        print(f"  PAIRED vs baseline mask: {pb['delta'] * 100:+.2f}pp  "
              f"CI95 [{pb['ci_low'] * 100:+.2f}, {pb['ci_high'] * 100:+.2f}]pp  "
              f"excludes 0: {pb['excludes_zero']}")
        peb = eb["paired_vs_oracle_same_budget"]
        print(f"  PAIRED vs same-count ORACLE global threshold: "
              f"{peb['delta'] * 100:+.2f}pp  "
              f"CI95 [{peb['ci_low'] * 100:+.2f}, {peb['ci_high'] * 100:+.2f}]pp  "
              f"excludes 0: {peb['excludes_zero']} (block5 excludes 0: "
              f"{eb['paired_vs_oracle_same_budget_block5']['excludes_zero']})")

    if "nested" in res:
        n = res["nested"]
        print(f"\n-- NESTED protocol (K chosen on training block only) --")
        print(f"  K per fold {n['k_per_fold']}  ->  {n['n_signals']} signals, "
              f"precision {n['precision'] * 100:.2f}%")
        print(f"  date-clustered CI95 (block=1): "
              f"[{n['dates_ci']['ci_low'] * 100:.2f}%, {n['dates_ci']['ci_high'] * 100:.2f}%]"
              f"  excludes base: {n['excludes_base_plain']}")
        print(f"  date-clustered CI95 (block=5): "
              f"[{n['dates_ci_block5']['ci_low'] * 100:.2f}%, "
              f"{n['dates_ci_block5']['ci_high'] * 100:.2f}%]"
              f"  excludes base: {n['excludes_base_block5']}")
        pn = n["paired_vs_baseline"]
        po = n["paired_vs_oracle_same_budget"]
        print(f"  PAIRED vs harness baseline (same rule, correlated draws): "
              f"{pn['delta'] * 100:+.2f}pp  "
              f"CI95 [{pn['ci_low'] * 100:+.2f}, {pn['ci_high'] * 100:+.2f}]pp  "
              f"excludes 0: {pn['excludes_zero']}")
        print(f"  PAIRED vs same-budget ORACLE global threshold: "
              f"{po['delta'] * 100:+.2f}pp  "
              f"CI95 [{po['ci_low'] * 100:+.2f}, {po['ci_high'] * 100:+.2f}]pp  "
              f"excludes 0: {po['excludes_zero']}  (block5 "
              f"[{n['paired_vs_oracle_same_budget_block5']['ci_low'] * 100:+.2f}, "
              f"{n['paired_vs_oracle_same_budget_block5']['ci_high'] * 100:+.2f}]pp "
              f"excludes 0: {n['paired_vs_oracle_same_budget_block5']['excludes_zero']})")
        c = n["concentration"]
        print(f"  dates {c['n_distinct_dates']}, stocks {c['n_distinct_stocks']}, "
              f"HHI {c['herfindahl_dates']:.4f}, "
              f"drop busiest date ({c['busiest_date']}) -> "
              f"{c['precision_drop_busiest_date'] * 100:.2f}% "
              f"on {c['precision_drop_busiest_n']} signals")

    print("\n-- within-session ranking quality (mean over folds) --")
    aucs = [f["auc"] for f in res["per_fold_summary"]]
    for key in ("pooled_auc", "weighted_session_auc", "median_session_auc"):
        vals = [a[key] for a in aucs if np.isfinite(a.get(key, np.nan))]
        if vals:
            print(f"  {key:>24}: {np.mean(vals):.4f}")
    print(f"  {'share_sessions>0.5':>24}: "
          f"{np.mean([a['share_sessions_auc_above_half'] for a in aucs]):.4f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default=POOLED_BASELINE_CONFIG,
                    help="comma-separated keys of CONFIGS, or 'all'")
    ap.add_argument("--n-boot", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true", help="fewer bootstrap draws")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--cache-dir", default=str(wf.OUT_DIR / "crosssec_cache"),
                    help="where to cache scored fold frames ('' disables); lets "
                         "a re-analysis reuse the fitted scores instead of refitting")
    args = ap.parse_args()

    n_boot = 500 if args.quick else args.n_boot
    k_grid = xs.TOP_K_GRID
    p_grid = xs.PERCENTILE_GRID

    names = list(CONFIGS) if args.configs == "all" else args.configs.split(",")
    frame = xs.load()
    print(f"matrix {frame.shape}, base rate {frame['label_high'].mean() * 100:.3f}%",
          flush=True)

    payload = {
        "folds": 5, "horizon": 10, "embargo": 2, "min_train_sessions": 150,
        "final_holdout_start": xs.FINAL_HOLDOUT_START,
        "n_boot": n_boot, "seed": args.seed,
        "k_grid": list(k_grid), "percentile_grid": list(p_grid),
        # Both baselines, each labelled, because they are different populations
        # and were previously indistinguishable in the payload. Every delta in
        # `results` is computed against the in-run figure, not the prior one.
        "pooled_baseline_oos_precision": PRIOR_STRIDE5_POOLED_BASELINE_OOS_PRECISION,
        "prior_published_baseline": {
            "value": PRIOR_STRIDE5_POOLED_BASELINE_OOS_PRECISION,
            **PRIOR_STRIDE5_BASELINE_PROVENANCE,
        },
        "in_run_baseline_used_for_deltas": "results.<config>.global_threshold",
        "results": {},
    }
    for name in names:
        cfg = CONFIGS[name]
        print(f"\n### {name}", flush=True)
        res = run_config(frame, cfg, k_grid, p_grid, n_boot, args.seed,
                         cache_dir=(args.cache_dir or None))
        report(res, k_grid, n_boot)
        payload["results"][name] = strip_private(res)

    if not args.no_save:
        tag = f"_{args.tag}" if args.tag else ""
        # Derive the fold count from the results rather than asserting one. This
        # was hard-coded to 5 while every result recorded n_folds = 4 (the fold
        # list is built with n_folds=5 but a fold whose test block is too thin to
        # train on is dropped), so a reader taking `folds` at face value
        # overstated the count by one.
        observed = [
            r.get("n_folds") for r in payload["results"].values()
            if isinstance(r, dict) and r.get("n_folds")
        ]
        payload["folds"] = max(observed) if observed else None
        payload["folds_requested"] = 5
        if observed and len(set(observed)) > 1:
            payload["folds_note"] = (
                f"configs completed differing fold counts {sorted(set(observed))}; "
                f"`folds` is the maximum"
            )
        path = wf.save_report(f"crosssec{tag}", payload)
        print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
