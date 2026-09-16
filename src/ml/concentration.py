"""How concentrated are the headline precision numbers?

A pooled precision can be carried by a handful of observations. A flagging
subagent reported that the walk-forward baseline's 15.98% is dominated by fold 1
(1,131 of 1,790 signals at 10.79%), while folds 3-4 contain only 45 and 75
signals at 31-33%. If true, "4/4 folds above base" is much weaker evidence than
it sounds, and the same scrutiny must be applied to the 2026 holdout result.

This module measures concentration three ways for both headline results:

* per-fold signal counts and precisions,
* precision after removing the busiest N dates,
* the precision of a leave-one-fold-out refit, to show how much any single
  period contributes.

Usage
-----
    python -m src.ml.concentration
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"
HOLDOUT_START = "2026-01-01"


def drop_top_dates(dates: np.ndarray, y: np.ndarray, n_drop: int) -> tuple[float, int]:
    """Precision after removing the ``n_drop`` dates contributing most signals."""
    counts = pd.Series(dates).value_counts()
    worst = set(counts.index[:n_drop])
    keep = np.array([d not in worst for d in dates])
    if keep.sum() == 0:
        return float("nan"), 0
    return float(y[keep].mean()), int(keep.sum())


def main() -> None:
    frame = wf.load_matrix()
    cols = wf.feature_columns(frame)
    sessions = np.sort(frame["date"].unique())
    folds = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                     min_train_sessions=150, final_holdout_start=HOLDOUT_START)
    cfg = wf.Config(name="conc", model="hgb", label="label_high", target_rate=0.02)

    print("=" * 78)
    print("A. WALK-FORWARD BASELINE — per-fold breakdown")
    print("=" * 78)
    fold_rows = []
    for fold in folds:
        train = frame[frame["date"].isin(fold.train_sessions)]
        test = frame[frame["date"].isin(fold.test_sessions)]
        r = wf.evaluate_fold(train, test, cfg, 0)
        if "error" in r:
            continue
        te = test[test["label_high"].notna()]
        y = te["label_high"].to_numpy("float64")
        model = wf.make_model(cfg, 0)
        tr = train[train["label_high"].notna() & train["resolved"].fillna(0).astype(bool)]
        model.fit(tr[cols].to_numpy("float32"), tr["label_high"].to_numpy("float64"))
        s_tr = model.predict_proba(tr[cols].to_numpy("float32"))[:, 1]
        s_te = model.predict_proba(te[cols].to_numpy("float32"))[:, 1]
        thr = wf.pick_threshold(s_tr, tr["label_high"].to_numpy("float64"), 0.02)
        mask = s_te >= thr
        fold_rows.append({
            "fold": fold.name,
            "signals": int(mask.sum()),
            "share_of_total": float(mask.sum()),
            "precision": float(y[mask].mean()) if mask.any() else float("nan"),
            "dates": int(te.loc[mask, "date"].nunique()) if mask.any() else 0,
            "_y": y[mask],
            "_dates": te.loc[mask, "date"].to_numpy(),
        })
    total = sum(r["signals"] for r in fold_rows)
    for r in fold_rows:
        r["share_of_total"] = r["signals"] / total if total else 0.0
        print(f"  {r['fold'][:38]:38s} signals {r['signals']:>5d} "
              f"({r['share_of_total']*100:5.1f}% of total)  "
              f"precision {r['precision']*100:6.2f}%  dates {r['dates']:>4d}")

    y_all = np.concatenate([r["_y"] for r in fold_rows])
    d_all = np.concatenate([r["_dates"] for r in fold_rows])
    print(f"\n  pooled: {len(y_all):,} signals, precision {y_all.mean()*100:.2f}%")
    print("\n  concentration: precision after dropping the busiest N dates")
    for n in (0, 1, 3, 5, 10, 20):
        p, k = drop_top_dates(d_all, y_all, n)
        print(f"    drop {n:>2d} dates -> {p*100:6.2f}%  ({k:,} signals)")

    # How much does the single largest fold carry?
    biggest = max(fold_rows, key=lambda r: r["signals"])
    rest = [r for r in fold_rows if r is not biggest]
    y_rest = np.concatenate([r["_y"] for r in rest])
    print(f"\n  removing the largest fold ({biggest['fold'][:30]}, "
          f"{biggest['share_of_total']*100:.0f}% of signals):")
    print(f"    -> {y_rest.mean()*100:.2f}% on {len(y_rest):,} signals")

    summary: dict = {
        "walkforward_folds": [
            {k: v for k, v in r.items() if not k.startswith("_")} for r in fold_rows
        ],
        "walkforward_pooled": float(y_all.mean()),
        "walkforward_total_signals": int(len(y_all)),
        "walkforward_largest_fold_share": float(biggest["share_of_total"]),
        "walkforward_excluding_largest_fold": float(y_rest.mean()),
    }

    print("\n" + "=" * 78)
    print("B. 2026 HOLDOUT — same scrutiny on the headline claim")
    print("=" * 78)
    cutoff = np.datetime64(pd.Timestamp(HOLDOUT_START))
    train = frame[frame["date"] < cutoff]
    test = frame[frame["date"] >= cutoff]
    tr = train[train["label_high"].notna() & train["resolved"].fillna(0).astype(bool)]
    te = test[test["label_high"].notna()]
    model = wf.make_model(cfg, 0)
    model.fit(tr[cols].to_numpy("float32"), tr["label_high"].to_numpy("float64"))
    s_tr = model.predict_proba(tr[cols].to_numpy("float32"))[:, 1]
    s_te = model.predict_proba(te[cols].to_numpy("float32"))[:, 1]
    thr = wf.pick_threshold(s_tr, tr["label_high"].to_numpy("float64"), 0.02)
    mask = s_te >= thr
    y_h = te["label_high"].to_numpy("float64")[mask]
    d_h = te["date"].to_numpy()[mask]
    print(f"  signals {len(y_h):,}  dates {len(np.unique(d_h)):,}  "
          f"stocks {te.loc[mask, 'code'].nunique():,}")
    print(f"  precision {y_h.mean()*100:.2f}%  base {te['label_high'].mean()*100:.2f}%")
    counts = pd.Series(d_h).value_counts()
    print(f"  busiest date carries {counts.iloc[0]:,} signals "
          f"({counts.iloc[0]/len(y_h)*100:.1f}% of total)")
    print("\n  precision after dropping the busiest N dates")
    for n in (0, 1, 3, 5, 10, 20, 40):
        p, k = drop_top_dates(d_h, y_h, n)
        print(f"    drop {n:>2d} dates -> {p*100:6.2f}%  ({k:,} signals)")
    # Half-sample split by date order, to show it is not one era.
    order = np.argsort(d_h)
    half = len(order) // 2
    first, second = order[:half], order[half:]
    print(f"\n  chronological halves by signal date:")
    print(f"    first half  {y_h[first].mean()*100:6.2f}%  ({len(first):,} signals)")
    print(f"    second half {y_h[second].mean()*100:6.2f}%  ({len(second):,} signals)")

    summary["holdout"] = {
        "signals": int(len(y_h)),
        "dates": int(len(np.unique(d_h))),
        "precision": float(y_h.mean()),
        "base_rate": float(te["label_high"].mean()),
        "busiest_date_share": float(counts.iloc[0] / len(y_h)),
        "drop_top_dates": {
            n: drop_top_dates(d_h, y_h, n)[0] for n in (0, 1, 3, 5, 10, 20, 40)
        },
        "first_half_precision": float(y_h[first].mean()),
        "second_half_precision": float(y_h[second].mean()),
    }

    (REPORT_DIR / "ml_concentration.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {REPORT_DIR / 'ml_concentration.json'}")


if __name__ == "__main__":
    main()
