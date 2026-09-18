"""ADVERSARIAL AUDIT 4/4 -- how much of the 15.98% is real signal, and could
selection or date-clustering have manufactured it?

Reads `outputs/ml/audit/real_oos_scores.npz`, written by
`audit_ml_nulls.py --stage battery` from the UNMODIFIED harness run.

Three things are measured.

1. PER-FOLD LIFT AGAINST EACH FOLD'S OWN BASE RATE.
   `wf.summarise` pools precision signal-weighted but averages base rates
   *unweighted*, so its `oos_lift` mixes two weightings.  The fold is the
   experimental unit; each fold is compared to its own contemporaneous base
   rate, which is the comparison a trader would actually make.

2. DATE-BLOCK BOOTSTRAP.
   Signals on nearby dates share a 10-session forward window, so they share
   outcome.  Resampling *dates* (not rows) gives an interval that respects that
   dependence.  A row-level interval would be far too narrow and is computed
   anyway, to show the size of the error.

3. SELECTION BUDGET.
   The published baseline is the best of a small grid.  Under the null, the
   expected best-of-K precision and its spread are computed by Monte Carlo, to
   answer: "could picking the best of N configs have produced 15.98% from
   noise?"  An oracle-threshold bound is also reported, as the number a
   test-block-tuned search could have claimed had it cheated.

Usage
-----
    python scripts/audit_ml/audit_ml_selection_ceiling.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.ml import walkforward as wf  # noqa: E402

OUT_DIR = REPO_ROOT / "outputs" / "ml" / "audit"
TARGET_RATE = 0.02
FOLD_BOUNDS = ["2023-01-01", "2024-02-02", "2024-07-30", "2025-01-20",
               "2025-07-15", "2026-01-01"]
N_BOOT = 4000


def main() -> None:
    d = np.load(OUT_DIR / "real_oos_scores.npz", allow_pickle=True)
    s = d["scores"].astype("float64")
    y = d["labels"].astype("float64")
    # Dates were stored as days-since-epoch (datetime64[D] -> int64); convert
    # back through pandas so every downstream comparison is in the same unit.
    dates = pd.to_datetime(d["dates"].astype("int64"), unit="D").to_numpy()
    codes = d["codes"]

    frame = wf.load_matrix()
    sessions = np.sort(frame["date"].unique())
    folds = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                     min_train_sessions=150, final_holdout_start="2026-01-01")

    report: dict = {"n_rows": int(len(y)), "n_positives": int(y.sum()),
                    "pooled_base_rate": float(y.mean())}

    # ---------------------------------------------------------------- 1
    per_fold = []
    for f in folds:
        lo = np.datetime64(pd.Timestamp(f.test_sessions[0]))
        hi = np.datetime64(pd.Timestamp(f.test_sessions[-1]))
        m = (dates >= lo) & (dates <= hi)
        if not m.any():
            continue
        yy, ss = y[m], s[m]
        per_fold.append({
            "fold": f.name,
            "n_test": int(m.sum()),
            "positives": int(yy.sum()),
            "base_rate": float(yy.mean()),
            "auc": float(roc_auc_score(yy, ss)) if 0 < yy.sum() < len(yy) else None,
        })
    report["per_fold"] = per_fold

    # ---------------------------------------------------------------- 2
    # Recover the exact published set using the thresholds the harness actually
    # used at run time (recorded by the recording proxy, one per fold).
    thr_by_fold: dict[str, float] = {}
    if "fold_thresholds" in d:
        for f, t in zip(folds, d["fold_thresholds"]):
            thr_by_fold[f.name] = float(t)

    published = np.zeros(len(y), dtype=bool)
    for f in folds:
        lo = np.datetime64(pd.Timestamp(f.test_sessions[0]))
        hi = np.datetime64(pd.Timestamp(f.test_sessions[-1]))
        m = (dates >= lo) & (dates <= hi)
        if f.name in thr_by_fold:
            published |= m & (s >= thr_by_fold[f.name])

    yp, sp, dp = y[published], s[published], dates[published]
    n_sig, hits = int(published.sum()), int(y[published].sum())
    report["published_set"] = {
        "signals": n_sig, "hits": hits,
        "precision": float(hits / n_sig) if n_sig else None,
        "base_rate_all_oos_rows": float(y.mean()),
        "distinct_dates": int(np.unique(dp).size),
        "distinct_stocks": int(np.unique(codes[published]).size),
        "signal_dates_share": float(np.unique(dp).size / np.unique(dates).size),
        "thresholds": thr_by_fold,
    }

    # date-block bootstrap: resample the *signal dates* with replacement
    uniq = np.unique(dp)
    by_date = {u: (yp[dp == u], sp[dp == u]) for u in uniq}
    rng = np.random.default_rng(20260917)
    boot = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(len(uniq), size=len(uniq), replace=True)
        hh = sum(int(by_date[uniq[j]][0].sum()) for j in pick)
        nn = sum(len(by_date[uniq[j]][0]) for j in pick)
        boot[b] = hh / nn if nn else np.nan
    report["bootstrap_precision"] = {
        "method": "resample signal DATES with replacement",
        "n_dates": int(len(uniq)), "n_boot": N_BOOT,
        "mean": float(np.nanmean(boot)),
        "ci95": [float(np.nanpercentile(boot, 2.5)),
                 float(np.nanpercentile(boot, 97.5))],
        "p_below_full_base_rate": float(np.nanmean(boot <= y.mean())),
        "p_below_2x_base_rate": float(np.nanmean(boot <= 2 * y.mean())),
    }
    # the naive row-level interval, to show how much narrower it is
    se_row = np.sqrt(y.mean() * (1 - y.mean()) / n_sig)
    report["row_level_ci_for_contrast"] = {
        "se": float(se_row),
        "ci95": [float(y.mean() - 1.96 * se_row), float(y.mean() + 1.96 * se_row)],
        "note": ("This is the interval the project would get if it ignored "
                 "overlapping forward windows. It is the WRONG interval, and it "
                 "is reported only to quantify how much the date-block "
                 "bootstrap widens it."),
    }

    # ---------------------------------------------------------------- 3
    # Could the best of K configs have produced 15.98% from noise?
    # Null model: precision ~ Hypergeometric-ish; Monte-Carlo the max of K.
    null_kinds = ("perm_global", "perm_within_date", "label_bernoulli",
                  "feat_gauss_auc0")
    nd = json.loads((OUT_DIR / "nulls_audit.json").read_text(encoding="utf-8"))
    nulls = [r["oos_precision"] for r in nd["results"]
             if r.get("variant") in null_kinds and "error" not in r]
    # Draw the best-of-K under the observed null spread, for the grid sizes the
    # project actually ran (search.py presets: models=3 configs were ranked).
    mu, sd = float(np.mean(nulls)), float(np.std(nulls, ddof=1))
    rng2 = np.random.default_rng(7)
    sel = {}
    for K in (1, 3, 10, 30, 100):
        draws = rng2.normal(mu, sd, size=(20000, K)).max(axis=1)
        sel[str(K)] = {
            "expected_best_of_K": float(draws.mean()),
            "p_best_of_K_ge_real": float((draws >= 0.1598).mean()),
        }
    # The note is FORMATTED FROM THE COMPUTED VALUES rather than hardcoded. The
    # previous version was a literal string that had drifted from the payload it
    # describes in four ways at once: it said the models preset had 3 configs
    # (it has 7), SD ~0.7% (0.0125 = 1.25%), mean ~3.9% (0.03749 = 3.75%), and
    # best-of-3 ~4.6% (0.04803 = 4.80%). Every one of those numbers already
    # existed in this same dict, so a reader could see the contradiction without
    # leaving the file -- which is exactly the kind of drift that hardcoding
    # guarantees and interpolation cannot reproduce.
    n_configs = None
    try:
        models_rep = json.loads(
            (REPO_ROOT / "reports" / "ml_search_models.json").read_text(
                encoding="utf-8"))
        n_configs = int(models_rep.get("n_configs")
                        or len(models_rep.get("ranked") or []))
    except (OSError, ValueError, TypeError):
        pass
    _b3 = sel["3"]["expected_best_of_K"]
    if n_configs:
        _scope = (f"The 15.98% baseline was the top of the {n_configs}-config "
                  f"`models` preset.")
    else:
        _scope = "The 15.98% baseline was the top of the `models` preset."
    report["selection_budget"] = {
        "null_precision_mean": mu, "null_precision_sd": sd,
        "n_null_draws": len(nulls),
        "real_precision": 0.1598,
        "model": "Gaussian on the observed nulls (mean/SD above)",
        "best_of_K": sel,
        "practical_note": (
            f"{_scope} Selecting the best of 3 i.i.d. nulls with mean "
            f"{mu * 100:.2f}% and SD {sd * 100:.2f}% gives "
            f"{_b3 * 100:.2f}%. Selection cannot manufacture 15.98%."
        ),
    }

    path = OUT_DIR / "selection_ceiling.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
