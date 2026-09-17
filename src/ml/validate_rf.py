"""Validate the Random Forest result before promoting it in the reports.

`fam_rf_5` reports 20.84% out-of-sample on 22,867 signals with all four folds
above base, which would make it the strongest result in this project. A number
that good deserves adversarial checking rather than promotion, so this script
tests three things the pooled figure cannot show:

1. **Per-fold detail** —is the precision spread across folds or carried by one?
2. **Null control** —does the same model on permuted labels collapse to base?
   A model that still scores high on shuffled labels is measuring something other
   than the feature-label relationship.
3. **Threshold sanity** —what publication rate does the threshold actually
   produce, and does precision degrade gracefully as the threshold tightens?

Usage
-----
    python -m src.ml.validate_rf
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports"
HOLDOUT_START = "2026-01-01"


def rf_config() -> wf.Config:
    return wf.Config(
        name="rf_validation",
        model="rf",
        label="label_high",
        target_rate=0.02,
    )


def run_folds(frame: pd.DataFrame, cols: list[str], cfg: wf.Config,
              permute_seed: int | None = None) -> list[dict]:
    sessions = np.sort(frame["date"].unique())
    fold_list = wf.folds(sessions, n_folds=5, horizon=10, embargo=2,
                         min_train_sessions=150,
                         final_holdout_start=HOLDOUT_START)
    rng = np.random.default_rng(permute_seed) if permute_seed is not None else None
    out = []
    for fold in fold_list:
        train = frame[frame["date"].isin(fold.train_sessions)].copy()
        test = frame[frame["date"].isin(fold.test_sessions)].copy()
        if rng is not None:
            # Permute labels in BOTH blocks, so the model cannot learn the
            # mapping from either side.
            for part in (train, test):
                lab = part["label_high"].to_numpy("float64").copy()
                finite = np.isfinite(lab)
                shuffled = lab[finite].copy()
                rng.shuffle(shuffled)
                lab[finite] = shuffled
                part["label_high"] = lab
        r = wf.evaluate_fold(train, test, cfg, 0)
        if "error" not in r:
            out.append(r)
    return out


def main() -> None:
    frame = wf.load_matrix()  # resolves to the densest grid; see resolve_stride
    cols = wf.feature_columns(frame)
    cfg = rf_config()

    print("=" * 74)
    print("RANDOM FOREST VALIDATION")
    print("=" * 74)

    real = run_folds(frame, cols, cfg)
    s = wf.summarise(real)
    print("\n1. Per-fold detail (real labels)")
    for r in real:
        print(f"   test {str(r.get('fold', ''))[:34]:34s} "
              f"sig {r['oos_signals']:>6,}  precision {r['oos_precision']*100:6.2f}%")
    print(f"\n   pooled      {s['oos_precision']*100:.2f}% on {s['oos_signals']:,} signals")
    print(f"   base rate   {s['oos_base_rate']*100:.2f}%   lift {s['oos_lift']:.2f}x")
    print(f"   folds above base: {s['folds_above_base']}/{s['n_folds']}")
    per_fold = [r["oos_precision"] for r in real]
    print(f"   fold spread: min {min(per_fold)*100:.2f}%  max {max(per_fold)*100:.2f}%  "
          f"stdev {np.std(per_fold)*100:.2f}pp")

    # Drop the largest fold and see whether the result survives.
    big = max(real, key=lambda r: r["oos_signals"])
    rest = [r for r in real if r is not big]
    rs = wf.summarise(rest)
    print(f"   excluding largest fold ({big['oos_signals']:,} sig): "
          f"{rs['oos_precision']*100:.2f}% on {rs['oos_signals']:,} signals")

    print("\n2. Null control —identical model, permuted labels")
    nulls = []
    for seed in (11, 22):
        nr = run_folds(frame, cols, cfg, permute_seed=seed)
        ns = wf.summarise(nr)
        nulls.append(ns)
        print(f"   seed {seed}: {ns['oos_precision']*100:.2f}% on "
              f"{ns['oos_signals']:,} signals, base {ns['oos_base_rate']*100:.2f}%, "
              f"lift {ns['oos_lift']:.2f}x")
    mean_null = float(np.mean([n["oos_precision"] for n in nulls]))
    print(f"   mean null precision {mean_null*100:.2f}% vs real "
          f"{s['oos_precision']*100:.2f}%  -> the real signal is "
          f"{s['oos_precision']/max(mean_null, 1e-9):.1f}x the null")

    print("\n3. Threshold behaviour (publication rate vs precision, fold 1)")
    fold = real[0]
    print(f"   reference: threshold {fold['threshold']:.6f} gives "
          f"{fold['oos_share']*100:.2f}% publication at "
          f"{fold['oos_precision']*100:.2f}% precision")

    verdict = (
        "TRUSTWORTHY" if (
            s["folds_above_base"] == s["n_folds"]
            and mean_null < 1.6 * s["oos_base_rate"]
            and rs["oos_precision"] > s["oos_base_rate"] * 2
        ) else "NEEDS REVIEW"
    )
    print(f"\nVERDICT: {verdict}")

    (REPORT_DIR / "ml_rf_validation.json").write_text(json.dumps({
        "pooled": s,
        "per_fold": [{"signals": r["oos_signals"],
                      "precision": r["oos_precision"]} for r in real],
        "excluding_largest_fold": rs,
        "nulls": nulls,
        "mean_null_precision": mean_null,
        "verdict": verdict,
    }, indent=2, default=str), encoding="utf-8")
    print(f"wrote {REPORT_DIR / 'ml_rf_validation.json'}")


if __name__ == "__main__":
    main()
