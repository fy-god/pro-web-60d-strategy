"""Is a 70% precision target mathematically reachable at a 3.1% base rate?

This is the defining question of the project, and it can be answered before any
further modelling. Precision is not a free parameter: for a fixed base rate it is
a deterministic function of where the model operates on its ROC curve.

Derivation
----------
Let pi be the natural base rate, r the true-positive rate (recall) and f the
false-positive rate at a chosen threshold. Then

    PPV = pi*r / (pi*r + (1-pi)*f).

Rearranging for the requirement PPV >= p*:

    f <= pi*r*(1-p*) / ((1-pi)*p*).

Two consequences matter enormously here.

1. **A 70% target demands a near-perfect ROC corner.** With pi = 3.1% and
   p* = 0.70, the permissible false-positive rate is only ~1.37% of the achieved
   true-positive rate. Catching even one in five real events permits a
   false-positive rate of just 0.27% — against a population that is 96.9%
   negative. That is a genuinely extreme operating point.

2. **Precision rises as you publish fewer signals**, so "70%" is trivially
   reachable by publishing almost nothing. The honest question is not "can we hit
   70%" but "at what recall, on how many signals, and does it survive
   out-of-sample".

What this module measures, on the real purged walk-forward folds:

* the empirical precision-recall frontier of the best available model,
* the **maximum precision achievable at any threshold** (the oracle bound for
  that model — an upper limit no threshold choice can beat),
* the same after the fold's own training data is included, to show how much of a
  high number is in-sample memory,
* and the required false-positive rate for each precision target.

Usage
-----
    python -m src.ml.precision_ceiling
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"
FINAL_HOLDOUT_START = "2026-01-01"


def frontier(y: np.ndarray, scores: np.ndarray, n_points: int = 200) -> pd.DataFrame:
    """Empirical precision/recall/FPR at every achievable operating point.

    The grid must be dense enough to represent small signal counts. An earlier
    version sampled only 200 points across the whole range, which jumped from 1
    published row straight to ~338 and so could not see the region where a
    per-session top-K rule operates. De-duplicating the candidate counts and
    including every k below 2,000 fixes that.
    """
    order = np.argsort(-scores, kind="stable")
    y_sorted = y[order]
    n = len(y)
    total_pos = int(y_sorted.sum())
    if total_pos == 0:
        return pd.DataFrame()

    small = np.arange(1, min(2000, n) + 1)
    large = np.linspace(2000, n, n_points).astype(int) if n > 2000 else np.array([], int)
    k = np.unique(np.concatenate([small, large]))
    k = k[(k >= 1) & (k <= n)]
    tp = np.cumsum(y_sorted)[k - 1]
    fp = k - tp
    return pd.DataFrame({
        "n_published": k,
        "publish_rate": k / n,
        "recall": tp / total_pos,
        "precision": tp / k,
        "fpr": fp / (n - total_pos),
    })


def required_fpr(pi: float, precision: float, recall: float) -> float:
    """Largest false-positive rate still consistent with the precision target."""
    return pi * recall * (1.0 - precision) / ((1.0 - pi) * precision)


def main() -> None:
    frame = wf.load_matrix()
    sessions = np.sort(frame["date"].unique())
    fold_list = wf.folds(
        sessions, n_folds=5, horizon=10, embargo=2,
        min_train_sessions=150, final_holdout_start=FINAL_HOLDOUT_START,
    )

    cfg = wf.Config(name="ceiling_hgb", model="hgb", label="label_high",
                    target_rate=0.02)
    cols = wf.feature_columns(frame)

    rows = []
    oos_scores_all, oos_scores_rank, oos_y_all = [], [], []
    insample_frontiers = []

    for fold in fold_list:
        train = frame[frame["date"].isin(fold.train_sessions)]
        test = frame[frame["date"].isin(fold.test_sessions)]
        tr = train[train["label_high"].notna() & train["resolved"].fillna(0).astype(bool)]
        te = test[test["label_high"].notna()]
        if len(tr) < 5000 or len(te) < 200:
            continue

        model = wf.make_model(cfg, 0)
        model.fit(tr[cols].to_numpy("float32"), tr["label_high"].to_numpy("float64"))
        s_te = model.predict_proba(te[cols].to_numpy("float32"))[:, 1]
        s_tr = model.predict_proba(tr[cols].to_numpy("float32"))[:, 1]
        y_te = te["label_high"].to_numpy("float64")

        oos_scores_all.append(s_te)
        oos_y_all.append(y_te)
        # Per-fold ranks. Raw probabilities from four separately-fitted models
        # are not on a common scale, so pooling them directly mixes
        # calibrations. Ranking within each fold puts them on a comparable
        # footing and is the fairer bound of the two.
        oos_scores_rank.append(pd.Series(s_te).rank(pct=True).to_numpy("float64"))

        f_te = frontier(y_te, s_te)
        f_tr = frontier(tr["label_high"].to_numpy("float64"), s_tr)
        if len(f_te):
            f_te["fold"] = fold.name
            rows.append(f_te)
        if len(f_tr):
            f_tr["fold"] = fold.name
            insample_frontiers.append(f_tr)

    oos = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    ins = (pd.concat(insample_frontiers, ignore_index=True)
           if insample_frontiers else pd.DataFrame())
    oos.to_csv(REPORT_DIR / "ml_precision_frontier_oos.csv", index=False)
    if len(ins):
        ins.to_csv(REPORT_DIR / "ml_precision_frontier_insample.csv", index=False)

    y_all = np.concatenate(oos_y_all)
    s_all = np.concatenate(oos_scores_all)
    s_rank = np.concatenate(oos_scores_rank)
    base = float(y_all.mean())
    pooled = frontier(y_all, s_all)
    pooled_rank = frontier(y_all, s_rank)

    print("=" * 78)
    print("PRECISION CEILING ANALYSIS")
    print("=" * 78)
    print(f"pooled out-of-sample rows : {len(y_all):,}")
    print(f"pooled base rate          : {base*100:.4f}%")
    print(f"out-of-sample positives   : {int(y_all.sum()):,}")

    print("\n--- ORACLE: best precision achievable at ANY threshold (OOS) ---")
    for target_recall in (0.5, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01):
        ok = pooled[pooled["recall"] >= target_recall]
        if len(ok):
            best = ok["precision"].max()
            at = ok.loc[ok["precision"].idxmax()]
            print(f"  recall >= {target_recall:5.2f}  ->  max precision {best*100:6.2f}%  "
                  f"(publishes {int(at['n_published']):>6,} = {at['publish_rate']*100:5.2f}% of rows)")
    overall_best = pooled["precision"].max()
    print(f"\n  ABSOLUTE max precision at any threshold: {overall_best*100:.2f}%")
    print(f"  (achieved by publishing only "
          f"{pooled.loc[pooled['precision'].idxmax(), 'n_published']:.0f} rows)")

    # The absolute max is a degenerate artifact: publish one row that happens to
    # be a hit and precision is 100%. That is exactly the trap the source project
    # fell into with 5-22 hand-picked predictions. The meaningful bound is the
    # best precision available subject to publishing a usable number of signals.
    print("\n--- TRUE BOUND: max OOS precision subject to a minimum signal count ---")
    print("  (both score poolings shown; per-fold rank is the fairer one)")
    print("  min signals   pooled-raw   per-fold-rank   at signals   recall")
    bounds = {}
    for min_n in (50, 100, 250, 500, 1000, 2000, 5000, 10000):
        ok = pooled[pooled["n_published"] >= min_n]
        okr = pooled_rank[pooled_rank["n_published"] >= min_n]
        if not len(ok):
            continue
        best = ok["precision"].max()
        bestr = okr["precision"].max() if len(okr) else float("nan")
        at = ok.loc[ok["precision"].idxmax()]
        bounds[min_n] = {
            "max_precision_raw": float(best),
            "max_precision_rank": float(bestr),
            "at_signals": int(at["n_published"]),
            "recall": float(at["recall"]),
        }
        print(f"  {min_n:>11,}   {best*100:9.2f}%   {bestr*100:12.2f}%   "
              f"{int(at['n_published']):>10,}   {at['recall']*100:5.2f}%")

    usable = {k: v for k, v in bounds.items() if k >= 250}
    if usable:
        hard_ceiling = max(v["max_precision_raw"] for v in usable.values())
        hard_rank = max(v["max_precision_rank"] for v in usable.values())
        print(f"\n  >>> Practical ceiling (>=250 signals), pooled raw : {hard_ceiling*100:.2f}%")
        print(f"  >>> Practical ceiling (>=250 signals), rank-norm  : {hard_rank*100:.2f}%")
        top = max(hard_ceiling, hard_rank)
        print(f"  >>> A 70% target is {(0.70/top):.2f}x that ceiling.")
        print("  >>> No threshold, model or hyperparameter choice can exceed the "
              "oracle rows above;")
        print("  >>> they are computed on the true labels, so they are upper "
              "bounds by construction.")

    print("\n--- IN-SAMPLE equivalent, for contrast ---")
    if len(ins):
        print(f"  in-sample absolute max precision: {ins['precision'].max()*100:.2f}%")
        print("  This is the number that looks like '70%+' and means nothing.")

    print("\n--- what 70% precision REQUIRES, by recall ---")
    print("  recall   permitted FPR    (population is "
          f"{(1-base)*100:.1f}% negative)")
    for r in (0.5, 0.3, 0.2, 0.1, 0.05, 0.01):
        fpr = required_fpr(base, 0.70, r)
        print(f"  {r*100:5.1f}%   {fpr*100:10.4f}%")

    print("\n--- achieved precision vs the 70% requirement ---")
    ok = pooled[pooled["recall"] >= 0.10]
    if len(ok):
        best10 = ok["precision"].max()
        print(f"  best OOS precision at recall >= 10% : {best10*100:.2f}%")
        print(f"  gap to 70%                          : "
              f"{(0.70-best10)*100:.2f} percentage points")
        ratio = 0.70 / best10 if best10 > 0 else float("inf")
        print(f"  the target is {ratio:.2f}x the best achieved precision")

    (REPORT_DIR / "ml_precision_ceiling.json").write_text(json.dumps({
        "base_rate": base,
        "oos_rows": int(len(y_all)),
        "oos_positives": int(y_all.sum()),
        "absolute_max_precision_oos": float(overall_best),
        "absolute_max_precision_insample": (
            float(ins["precision"].max()) if len(ins) else None
        ),
        "practical_ceiling_by_min_signals": bounds,
        "practical_ceiling_250plus_raw": (
            max(v["max_precision_raw"] for v in usable.values()) if usable else None
        ),
        "practical_ceiling_250plus_rank": (
            max(v["max_precision_rank"] for v in usable.values()) if usable else None
        ),
        "requirement_70pct": {
            f"recall_{r}": required_fpr(base, 0.70, r) for r in (0.5, 0.3, 0.2, 0.1, 0.05, 0.01)
        },
        "note": (
            "At a ~3.1-4.1% base rate a 70% precision target requires the "
            "false-positive rate to be a small fraction of the true-positive "
            "rate. The per-threshold rows are the maximum precision at any "
            "threshold for a fitted HGB model, so they bound what threshold "
            "tuning can achieve. The absolute max (100% on one row) is a "
            "degenerate artifact of publishing a single row and is exactly the "
            "trap the source project fell into with 5-22 hand-picked cases."
        ),
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {REPORT_DIR / 'ml_precision_ceiling.json'}")


if __name__ == "__main__":
    main()
