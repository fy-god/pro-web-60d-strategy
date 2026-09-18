"""Single, one-shot evaluation on the reserved 2026 holdout.

Every other script in `src/ml` excludes sessions from 2026-01-01 onward. Those 160
sessions were never used for feature design, model selection, threshold choice or
hyperparameter tuning, so this is the only script whose output constitutes
out-of-sample evidence rather than development feedback.

Discipline this file enforces:

* It refuses to run with a threshold supplied from outside; the threshold must be
  derived from pre-2026 training scores.
* It evaluates each configuration **once**. There is no loop over configurations
  and no reporting of a maximum. Choosing the best of many configurations on this
  block would destroy its value as a holdout, which is exactly how the source
  project's numbers became unreproducible.
* It reports the same configuration the walk-forward search selected, so the
  holdout validates a pre-committed choice rather than searching for one.

Usage
-----
    python -m src.ml.final_holdout
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"
HOLDOUT_START = "2026-01-01"

# Pre-committed configuration: the walk-forward baseline, fixed before the
# holdout was touched. Changing this after seeing holdout output would invalidate
# the holdout; if it must change, say so explicitly in the report.
COMMITTED = wf.Config(
    name="committed_hgb_baseline",
    model="hgb",
    params={
        "max_leaf_nodes": 15,
        "min_samples_leaf": 300,
        "l2_regularization": 10.0,
        "learning_rate": 0.03,
        "max_iter": 300,
        "early_stopping": False,
    },
    label="label_high",
    target_rate=0.02,
)


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval — honest for small n and extreme proportions."""
    if n == 0:
        return float("nan"), float("nan")
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def date_clustered_ci(
    frame: pd.DataFrame, mask: np.ndarray, n_boot: int = 1000, seed: int = 0
) -> tuple[float, float]:
    """Bootstrap CI resampling DATES, not rows.

    Signals on the same session share a market move, so treating them as
    independent Bernoulli draws understates the interval by a wide margin. This
    resamples whole sessions with replacement.
    """
    rng = np.random.default_rng(seed)
    sub = frame.loc[mask, ["date", "label_high"]]
    if sub.empty:
        return float("nan"), float("nan")
    groups = {d: g["label_high"].to_numpy("float64") for d, g in sub.groupby("date")}
    keys = list(groups)
    if len(keys) < 2:
        return float("nan"), float("nan")
    stats = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        vals = np.concatenate([groups[keys[j]] for j in pick])
        stats[i] = vals.mean() if len(vals) else np.nan
    return float(np.nanpercentile(stats, 2.5)), float(np.nanpercentile(stats, 97.5))


def main() -> None:
    frame = wf.load_matrix()
    sessions = np.sort(frame["date"].unique())
    cutoff = np.datetime64(pd.Timestamp(HOLDOUT_START))

    train = frame[frame["date"] < cutoff]
    test = frame[frame["date"] >= cutoff]

    tr = train[train["label_high"].notna() & train["resolved"].fillna(0).astype(bool)]
    te = test[test["label_high"].notna()]
    print(f"train sessions < {HOLDOUT_START}: {train['date'].nunique():,} "
          f"({len(tr):,} usable rows)")
    print(f"holdout sessions >= {HOLDOUT_START}: {test['date'].nunique():,} "
          f"({len(te):,} usable rows)")

    cols = wf.feature_columns(frame)
    model = wf.make_model(COMMITTED, 0)
    model.fit(tr[cols].to_numpy("float32"), tr["label_high"].to_numpy("float64"))

    s_tr = model.predict_proba(tr[cols].to_numpy("float32"))[:, 1]
    s_te = model.predict_proba(te[cols].to_numpy("float32"))[:, 1]
    y_te = te["label_high"].to_numpy("float64")

    # Threshold from pre-2026 training scores ONLY.
    thr = wf.pick_threshold(s_tr, tr["label_high"].to_numpy("float64"),
                            COMMITTED.target_rate)
    pred = s_te >= thr

    n = int(pred.sum())
    hits = int(y_te[pred].sum())
    base = float(y_te.mean())
    prec = hits / n if n else float("nan")
    lo, hi = wilson(hits, n)
    clo, chi = date_clustered_ci(te, pred)

    print("\n" + "=" * 74)
    print("FINAL HOLDOUT — evaluated once, no configuration search")
    print("=" * 74)
    print(f"threshold (from pre-2026 train scores) : {thr:.6f}")
    print(f"holdout base rate                      : {base*100:.4f}%")
    print(f"signals published                      : {n:,}")
    print(f"hits                                   : {hits:,}")
    print(f"PRECISION                              : {prec*100:.2f}%")
    print(f"lift over base rate                    : {prec/base:.2f}x")
    print(f"Wilson 95% interval                    : [{lo*100:.2f}%, {hi*100:.2f}%]")
    print(f"date-clustered 95% interval            : [{clo*100:.2f}%, {chi*100:.2f}%]")
    print(f"distinct stocks                        : {te.loc[pred, 'code'].nunique():,}")
    print(f"distinct dates                         : {te.loc[pred, 'date'].nunique():,}")
    if n:
        share = te.loc[pred, "date"].value_counts()
        hhi = float(((share / share.sum()) ** 2).sum())
        print(f"date HHI                               : {hhi:.4f} "
              f"(~{1/hhi:.1f} effective dates)")
        top = share.index[0]
        keep = pred & (te["date"].to_numpy() != np.datetime64(top))
        if keep.sum():
            print(f"precision excluding busiest date        : "
                  f"{y_te[keep].mean()*100:.2f}% ({int(keep.sum())} signals)")

    payload = {
        "holdout_start": HOLDOUT_START,
        "config": {"model": COMMITTED.model, "params": COMMITTED.params,
                   "label": COMMITTED.label, "target_rate": COMMITTED.target_rate},
        "threshold": float(thr),
        "n_train_rows": int(len(tr)),
        "n_holdout_rows": int(len(te)),
        "base_rate": base,
        "signals": n,
        "hits": hits,
        "precision": float(prec),
        "lift": float(prec / base) if base else None,
        "wilson_95": [lo, hi],
        "date_clustered_95": [clo, chi],
        "distinct_stocks": int(te.loc[pred, "code"].nunique()) if n else 0,
        "distinct_dates": int(te.loc[pred, "date"].nunique()) if n else 0,
        "note": (
            "Single pre-committed configuration, evaluated once on sessions never "
            "used for any selection. No maximum is taken over configurations here "
            "by design."
        ),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "ml_final_holdout.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
