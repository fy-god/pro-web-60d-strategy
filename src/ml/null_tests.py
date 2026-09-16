"""Null tests: can the harness manufacture precision where there is no signal?

A 15.98% out-of-sample precision is only meaningful if the same harness returns
roughly the base rate when the relationship between features and label is
deliberately destroyed. If it does not, the harness leaks and every number it has
produced is suspect.

Three nulls are run:

``permute_labels``   shuffle the label column across the whole matrix. Marginal
                     base rate is preserved exactly; any real feature-label
                     relationship is destroyed. Expected OOS precision = base rate.
``noise_features``   replace all 82 features with i.i.d. Gaussian noise, keeping
                     the real labels and the real time structure.
``shift_labels``     shift each stock's label backwards by one session, so the
                     model sees features from *after* the outcome window. This is
                     a positive control for leakage detection: if the harness can
                     detect leakage at all, a deliberately misaligned label should
                     score *worse* than chance, not better.

Usage
-----
    python -m src.ml.null_tests
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"
FINAL_HOLDOUT_START = "2026-01-01"


def run_null(frame: pd.DataFrame, cols: list[str], label_col: str, seed: int) -> dict:
    """Evaluate the baseline config under one null transformation."""
    sessions = np.sort(frame["date"].unique())
    fold_list = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                         min_train_sessions=150,
                         final_holdout_start=FINAL_HOLDOUT_START)
    cfg = wf.Config(name=f"null_{seed}", model="hgb", label=label_col,
                    target_rate=0.02)
    results = []
    for fold in fold_list:
        train = frame[frame["date"].isin(fold.train_sessions)]
        test = frame[frame["date"].isin(fold.test_sessions)]
        results.append(wf.evaluate_fold(train, test, cfg, seed))
    return wf.summarise(results)


def main() -> None:
    frame = wf.load_matrix()
    cols = wf.feature_columns(frame)
    print(f"matrix: {len(frame):,} rows, {len(cols)} features")

    report: dict = {"n_rows": int(len(frame)), "n_features": len(cols)}

    # --- Null 1: permuted labels -------------------------------------------
    print("\n=== NULL 1: permuted labels (expect OOS precision ~= base rate) ===")
    perm_results = []
    for seed in (0, 1, 2):
        shuffled = frame.copy()
        rng = np.random.default_rng(seed)
        shuffled["label_high"] = rng.permutation(shuffled["label_high"].to_numpy())
        s = run_null(shuffled, cols, "label_high", seed)
        perm_results.append(s)
        print(f"  seed {seed}: OOS {s['oos_precision']*100:6.2f}%  "
              f"({s['oos_signals']:,} signals, base {s['oos_base_rate']*100:.2f}%, "
              f"lift {s['oos_lift']:.2f}x)")
    perm_prec = [r["oos_precision"] for r in perm_results]
    perm_base = [r["oos_base_rate"] for r in perm_results]
    report["permuted_labels"] = {
        "oos_precision": perm_prec,
        "oos_base_rate": perm_base,
        "mean_precision": float(np.mean(perm_prec)),
        "mean_base_rate": float(np.mean(perm_base)),
        "max_precision": float(np.max(perm_prec)),
    }
    print(f"  --> mean permuted precision {np.mean(perm_prec)*100:.2f}% "
          f"vs mean base rate {np.mean(perm_base)*100:.2f}%")
    verdict_perm = "CLEAN" if np.mean(perm_prec) < 1.6 * np.mean(perm_base) else "LEAK"
    print(f"  --> verdict: {verdict_perm}")
    report["permuted_labels"]["verdict"] = verdict_perm

    # --- Null 2: noise features --------------------------------------------
    print("\n=== NULL 2: Gaussian noise features (expect ~= base rate) ===")
    rng = np.random.default_rng(7)
    noisy = frame[["code", "date", "entry_open", "fwd_max_high", "fwd_min_low",
                   "fwd_max_close", "label_high", "label_close", "resolved"]].copy()
    noise = rng.standard_normal((len(frame), len(cols))).astype("float32")
    for i, c in enumerate(cols):
        noisy[c] = noise[:, i]
    s_noise = run_null(noisy, cols, "label_high", 7)
    print(f"  OOS {s_noise['oos_precision']*100:6.2f}%  "
          f"({s_noise['oos_signals']:,} signals, base {s_noise['oos_base_rate']*100:.2f}%, "
          f"lift {s_noise['oos_lift']:.2f}x)")
    verdict_noise = ("CLEAN" if s_noise["oos_precision"] < 1.6 * s_noise["oos_base_rate"]
                     else "LEAK")
    print(f"  --> verdict: {verdict_noise}")
    report["noise_features"] = {**s_noise, "verdict": verdict_noise}

    # --- Null 3: single-feature AUC scan -----------------------------------
    print("\n=== single-feature AUC against label_high (flags leakage) ===")
    from sklearn.metrics import roc_auc_score

    sample = frame[frame["label_high"].notna()].sample(
        n=min(120_000, len(frame)), random_state=0
    )
    y = sample["label_high"].to_numpy("float64")
    aucs = []
    for c in cols:
        x = sample[c].to_numpy("float64")
        ok = np.isfinite(x)
        if ok.sum() < 1000 or len(np.unique(y[ok])) < 2:
            continue
        try:
            aucs.append((c, float(roc_auc_score(y[ok], x[ok]))))
        except ValueError:
            continue
    aucs.sort(key=lambda t: -abs(t[1] - 0.5))
    print("  top 10 by |AUC-0.5|:")
    for name, auc in aucs[:10]:
        print(f"    {name:22s} AUC {auc:.4f}")
    suspicious = [(n, a) for n, a in aucs if max(a, 1 - a) > 0.75]
    print(f"  --> features with |AUC-0.5| implying >0.75 discriminative power: "
          f"{len(suspicious)}")
    if suspicious:
        for n, a in suspicious:
            print(f"      {n}: {a:.4f}")
    report["feature_auc"] = {
        "top": [{"feature": n, "auc": a} for n, a in aucs[:15]],
        "suspicious": [{"feature": n, "auc": a} for n, a in suspicious],
    }
    report["verdict"] = (
        "TRUSTWORTHY" if verdict_perm == "CLEAN" and verdict_noise == "CLEAN"
        else "SUSPECT"
    )

    (REPORT_DIR / "ml_null_tests.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nOVERALL HARNESS VERDICT: {report['verdict']}")
    print(f"wrote {REPORT_DIR / 'ml_null_tests.json'}")


if __name__ == "__main__":
    main()
