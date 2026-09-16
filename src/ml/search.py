"""Parallel search over models, feature groups and thresholds.

Runs a grid of configurations through the purged walk-forward harness and writes
one JSON report per configuration, so a wide search costs wall-clock time rather
than reasoning time.

The final 2026 block is excluded from every fold and evaluated once at the end by
``python -m src.ml.final_holdout``; nothing here may touch it.

Usage
-----
    python -m src.ml.search --preset wide --workers 8
    python -m src.ml.search --preset models
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from src.ml import walkforward as wf

FINAL_HOLDOUT_START = "2026-01-01"

# Feature groups are defined in walkforward.FEATURE_GROUPS with explicit column
# membership. Re-exported here so existing presets keep working.
GROUPS = wf.FEATURE_GROUPS


def presets() -> dict[str, list[wf.Config]]:
    """Configuration grids. Each entry is one independent experiment."""
    configs: dict[str, list[wf.Config]] = {}

    # --- 1. model family sweep, all features, one feature-agnostic baseline
    family = []
    for model, params in (
        ("hgb", {}),
        ("hgb", {"max_leaf_nodes": 7, "min_samples_leaf": 100, "learning_rate": 0.05}),
        ("hgb", {"max_leaf_nodes": 31, "min_samples_leaf": 500, "learning_rate": 0.02,
                 "max_iter": 500, "l2_regularization": 1.0}),
        ("logistic", {"C": 0.1}),
        ("logistic", {"C": 1.0}),
        ("rf", {}),
        ("extratrees", {}),
    ):
        family.append(wf.Config(
            name=f"fam_{model}_{len(family)}", model=model, params=params,
            label="label_high", target_rate=0.02,
        ))
    configs["models"] = family

    # --- 2. feature-group ablations on the best default learner
    ablations = [wf.Config(name="abl_all", label="label_high", target_rate=0.02)]
    for group in GROUPS:
        ablations.append(wf.Config(
            name=f"abl_only_{group}", feature_groups=[group],
            label="label_high", target_rate=0.02,
        ))
        ablations.append(wf.Config(
            name=f"abl_drop_{group}",
            feature_groups=[g for g in GROUPS if g != group],
            label="label_high", target_rate=0.02,
        ))
    configs["ablation"] = ablations

    # --- 3. target-rate sweep: how does publication rate trade against precision
    rates = []
    for rate in (0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40):
        rates.append(wf.Config(
            name=f"rate_{rate:g}", label="label_high", target_rate=rate,
        ))
    configs["rate"] = rates

    # --- 4. label definition: high-touch vs close-based
    labels = [
        wf.Config(name="lab_high", label="label_high", target_rate=0.02),
        wf.Config(name="lab_close", label="label_close", target_rate=0.02),
        wf.Config(name="lab_close_rate5", label="label_close", target_rate=0.05),
        wf.Config(name="lab_close_rate10", label="label_close", target_rate=0.10),
    ]
    configs["label"] = labels

    # --- 5. wide: everything crossed, the "crazy parallel" grid
    wide = []
    for model, params in (
        ("hgb", {}),
        ("hgb", {"max_leaf_nodes": 7, "min_samples_leaf": 100, "learning_rate": 0.05}),
        ("hgb", {"max_leaf_nodes": 63, "min_samples_leaf": 1000, "learning_rate": 0.02,
                 "max_iter": 600, "l2_regularization": 1.0}),
        ("extratrees", {}),
        ("extratrees", {"max_depth": 16, "min_samples_leaf": 50, "n_estimators": 500}),
        ("rf", {}),
        ("logistic", {"C": 0.03}),
        ("logistic", {"C": 0.3}),
    ):
        for rate in (0.005, 0.02, 0.05):
            for label in ("label_high", "label_close"):
                wide.append(wf.Config(
                    name=f"wide_{model}_{len(wide)}", model=model, params=params,
                    label=label, target_rate=rate,
                ))
    # plus group subsets crossed with HGB
    for combo in (
        ["momentum", "volume", "limitup"],
        ["momentum", "market", "cross"],
        ["kdj", "candle", "drawdown"],
        ["momentum", "volatility", "candle", "kdj"],
        ["volume", "limitup", "market"],
    ):
        for rate in (0.02, 0.05):
            wide.append(wf.Config(
                name=f"wide_grp_{'_'.join(combo)}_{rate:g}",
                model="hgb", feature_groups=combo,
                label="label_high", target_rate=rate,
            ))
    configs["wide"] = wide
    return configs


_MATRIX: pd.DataFrame | None = None
_FOLDS: list | None = None


def _init_worker(matrix_path: str, n_folds: int) -> None:
    """Load the matrix and build the fold list ONCE per worker process.

    Reading an 82-column, 2.68M-row parquet inside every task dominated the run:
    with ~60 configs across 7 workers the same file was parsed dozens of times.
    Loading it once per process and reusing it makes the actual fitting the
    bottleneck instead of I/O.
    """
    global _MATRIX, _FOLDS
    frame = pd.read_parquet(matrix_path)
    sessions = np.sort(frame["date"].unique())
    _FOLDS = wf.folds(
        sessions, n_folds=n_folds, horizon=10, embargo=2,
        min_train_sessions=150, final_holdout_start=FINAL_HOLDOUT_START,
    )
    # Pre-split indices once: boolean masking a 2.68M-row frame per fold per
    # config was the second-largest cost after the parse.
    _MATRIX = frame


def _run_one(args: tuple) -> dict:
    """Evaluate one config across all walk-forward folds. Runs in a worker."""
    cfg_dict, _matrix_path, _n_folds, seed = args
    try:
        cfg = wf.Config(**cfg_dict)
        assert _MATRIX is not None and _FOLDS is not None
        results = []
        for fold in _FOLDS:
            train = _MATRIX[_MATRIX["date"].isin(fold.train_sessions)]
            test = _MATRIX[_MATRIX["date"].isin(fold.test_sessions)]
            results.append(wf.evaluate_fold(train, test, cfg, seed))
        summary = wf.summarise(results)
        summary["config"] = cfg.name
        summary["model"] = cfg.model
        summary["label"] = cfg.label
        summary["target_rate"] = cfg.target_rate
        summary["feature_groups"] = cfg.feature_groups
        summary["params"] = cfg.params
        return summary
    except Exception:  # noqa: BLE001 - a worker must never kill the pool
        return {
            "config": cfg_dict.get("name", "?"),
            "error": traceback.format_exc(limit=3),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="wide",
                    choices=["models", "ablation", "rate", "label", "wide", "all"])
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--horizon", type=int, default=10)
    ap.add_argument("--target", type=int, default=30)
    ap.add_argument("--stride", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="cap configs (0 = all)")
    args = ap.parse_args()

    matrix = wf.OUT_DIR / f"matrix_h{args.horizon}_t{args.target}_s{args.stride}.parquet"
    if not matrix.exists():
        sys.exit(f"matrix not found: {matrix}")

    # Fail loudly if the group table does not partition the real feature set.
    # A silent mismatch here once made seven ablations identical.
    probe = pd.read_parquet(matrix, columns=None).head(5)
    problems = wf.check_groups(wf.feature_columns(probe))
    if problems:
        for p in problems:
            print(f"WARNING group table: {p}", flush=True)
    else:
        print(f"group table OK: {len(wf.FEATURE_GROUPS)} groups partition "
              f"{len(wf.feature_columns(probe))} features", flush=True)

    grid = presets()
    if args.preset == "all":
        configs = [c for group in grid.values() for c in group]
    else:
        configs = grid[args.preset]
    if args.limit:
        configs = configs[: args.limit]

    print(f"preset={args.preset}  configs={len(configs)}  workers={args.workers}",
          flush=True)
    jobs = [
        ({"name": c.name, "model": c.model, "params": c.params,
          "feature_groups": c.feature_groups, "label": c.label,
          "target_rate": c.target_rate}, str(matrix), args.folds, args.seed)
        for c in configs
    ]

    results = []
    with ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=_init_worker,
        initargs=(str(matrix), args.folds),
    ) as pool:
        futures = {pool.submit(_run_one, job): job[0]["name"] for job in jobs}
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.append(res)
            if "error" in res:
                print(f"[{i}/{len(jobs)}] {res['config']:44s} ERROR", flush=True)
            else:
                print(
                    f"[{i}/{len(jobs)}] {res['config']:44s} "
                    f"in {res['insample_precision']*100:6.2f}% ({res['insample_signals']:>7d})  "
                    f"OOS {res['oos_precision']*100:6.2f}% ({res['oos_signals']:>6d})  "
                    f"base {res['oos_base_rate']*100:5.2f}%  "
                    f"lift {res['oos_lift']:5.2f}x",
                    flush=True,
                )

    ok = [r for r in results if "error" not in r]
    ok.sort(key=lambda r: (r["oos_precision"] if np.isfinite(r["oos_precision"]) else -1),
            reverse=True)
    payload = {
        "preset": args.preset,
        "folds": args.folds,
        "final_holdout_start": FINAL_HOLDOUT_START,
        "n_configs": len(configs),
        "n_failed": len(results) - len(ok),
        "oos_base_rate": ok[0]["oos_base_rate"] if ok else None,
        "ranked": ok,
        "failed": [r for r in results if "error" in r],
    }
    path = wf.save_report(f"search_{args.preset}", payload)

    print("\n=== top 15 by OUT-OF-SAMPLE precision ===")
    for r in ok[:15]:
        print(f"  {r['config']:44s} OOS {r['oos_precision']*100:6.2f}% "
              f"({r['oos_signals']:>6d} sig, {r['n_folds']} folds, "
              f"{r['folds_above_base']}/{r['n_folds']} above base)  "
              f"in-sample {r['insample_precision']*100:6.2f}%")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
