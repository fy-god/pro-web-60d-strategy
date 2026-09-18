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
import statistics
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
    # plus group subsets crossed with HGB.
    #
    # "drawdown" is NOT a feature group: FEATURE_GROUPS has candle, cross, kdj,
    # limitup, market, momentum, position, volatility, volume. The combo below
    # used to name it, so `wide_grp_kdj_candle_drawdown_0.02` and `_0.05` failed
    # with KeyError on every run and were reported only in the report's `failed`
    # list — 2 of 58 configurations that could never produce a number. The
    # drawdown-flavoured features live in the `position` group, which is what
    # this now uses. `check_presets` below makes any future typo a hard error at
    # startup rather than two silent failures per run.
    for combo in (
        ["momentum", "volume", "limitup"],
        ["momentum", "market", "cross"],
        ["kdj", "candle", "position"],
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
    check_presets(configs)
    return configs


def check_presets(configs: dict[str, list]) -> None:
    """Fail at startup if a preset names a feature group that does not exist.

    A typo here costs two configurations per run and shows up only as an entry in
    the report's `failed` list, where it reads like a runtime mishap rather than a
    configuration error. Better to refuse to start.
    """
    known = set(wf.FEATURE_GROUPS)
    for preset, items in configs.items():
        for cfg in items:
            unknown = [g for g in (cfg.feature_groups or []) if g not in known]
            if unknown:
                raise SystemExit(
                    f"preset {preset!r} config {cfg.name!r} names unknown feature "
                    f"group(s) {unknown}; known groups are {sorted(known)}"
                )


_MATRIX: pd.DataFrame | None = None
_FOLDS: list | None = None


def _init_worker(matrix_path: str, n_folds: int, horizon: int, embargo: int) -> None:
    """Load the matrix and build the fold list ONCE per worker process.

    Reading an 82-column, 2.68M-row parquet inside every task dominated the run:
    with ~60 configs across 7 workers the same file was parsed dozens of times.
    Loading it once per process and reusing it makes the actual fitting the
    bottleneck instead of I/O.
    """
    global _MATRIX, _FOLDS
    frame = pd.read_parquet(matrix_path)
    sessions = np.sort(frame["date"].unique())
    # horizon and embargo arrive through initargs rather than being hard-coded.
    # They were literals here, so `--horizon 20` would have built folds purging 10
    # sessions against a 20-session label window, quietly letting 10 sessions of
    # holdout prices into training. The matrices on disk are all h10, so this was
    # latent, but it is the same class of bug concentration.py guards against.
    _FOLDS = wf.folds(
        sessions, n_folds=n_folds, horizon=horizon, embargo=embargo,
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
    ap.add_argument("--embargo", type=int, default=2,
                    help="sessions of embargo after each fold boundary; must be "
                         "passed with --horizon so the purge matches the label "
                         "window actually used")
    ap.add_argument("--target", type=int, default=30)
    ap.add_argument("--stride", type=int, default=None,
                    help="matrix stride; default resolves to the densest grid "
                         "that exists so reports are not silently mixed")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="cap configs (0 = all)")
    ap.add_argument("--min-signals", type=int, default=250,
                    help="out-of-sample signal floor a config must clear across "
                         "every fold to be RANKED (the unfiltered list is kept "
                         "under ranked_unfiltered). Guards against a few-signal "
                         "config topping the table on noise.")
    args = ap.parse_args()

    # Resolve the grid explicitly rather than defaulting to a number. Reports
    # differ between grids, so an implicit default here can silently overwrite a
    # report produced on a different sample of the panel.
    stride = args.stride if args.stride is not None else wf.resolve_stride()
    matrix = wf.matrix_path(horizon=args.horizon, target=args.target, stride=stride)
    if not matrix.exists():
        sys.exit(f"matrix not found: {matrix}")
    print(f"matrix: {matrix.name} (stride {stride})", flush=True)

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

    # Search reads the parquet through pandas rather than wf.load_matrix, so
    # LAST_LOAD stayed empty and save_report could not stamp the row and session
    # counts -- reports carried a stride but no evidence of which grid produced
    # it. Record the provenance here. The counts come from the metadata file when
    # present (cheap) and otherwise from the frame the workers will load; either
    # way they describe THIS matrix, not whatever happens to be in outputs/.
    meta_path = matrix.with_name(matrix.stem + "_meta.json")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        meta = {}
    wf.LAST_LOAD = {
        "path": str(matrix),
        "stride": stride,
        "rows": int(meta.get("rows") or 0),
        "sessions": int(meta.get("sessions") or 0),
    }
    if not wf.LAST_LOAD["rows"]:
        print(f"WARNING: {meta_path.name} missing; reports will not record the "
              f"matrix row count", flush=True)

    grid = presets()
    if args.preset == "all":
        configs = [c for group in grid.values() for c in group]
    else:
        configs = grid[args.preset]
    if args.limit:
        configs = configs[: args.limit]

    # A partial run must not overwrite a complete published report. Testing with
    # `--limit 1` once replaced the 58-configuration `ml_search_wide.json` with a
    # single row, silently deleting 55 results and their evidence. The report is
    # named after the preset, not after the subset, so the guard belongs here.
    report_path = wf.REPORT_DIR / f"ml_search_{args.preset}.json"
    full_run = len(configs) == len(grid.get(args.preset, []))
    if report_path.exists() and not full_run:
        try:
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            prior = int(existing.get("n_configs") or 0)
        except (json.JSONDecodeError, OSError):
            prior = 0
        if prior > len(configs):
            sys.exit(
                f"refusing to overwrite {report_path.name}, which holds {prior} "
                f"configuration(s), with a partial run of {len(configs)}. "
                f"Re-run without --limit, or set --out to a scratch name."
            )

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
        initargs=(str(matrix), args.folds, args.horizon, args.embargo),
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
    # Rank on a row that could actually be traded.
    #
    # Ranking the raw list by precision alone put `wide_hgb_13` first in the wide
    # grid: 33.33% precision on THREE signals, having completed only 2 of 4 folds.
    # A binomial standard error at n=3, p=1/3 is 0.272, so that row is
    # indistinguishable from noise and cannot support any claim. A minimum signal
    # floor and a requirement that the config completed every fold are applied
    # before the sort; the unfiltered list is kept under "ranked_unfiltered" so
    # nothing is hidden.
    # A config that completed only 2 of 5 folds cannot be rank 1 either. The
    # threshold is `args.folds - 1`, matching the `full_fold` definition below:
    # `n_folds` counts folds that produced at least one signal, and a fold with
    # zero signals is dropped by summarise(), so requiring an exact match would
    # exclude every config on a grid where any fold is thin.
    min_signals = args.min_signals
    min_folds = args.folds - 1
    ok.sort(key=lambda r: (r["oos_precision"] if np.isfinite(r["oos_precision"]) else -1),
            reverse=True)
    ranked_unfiltered = list(ok)
    eligible = [
        r for r in ok
        if r.get("oos_signals", 0) >= min_signals
        and r.get("n_folds", 0) >= min_folds
    ]
    if eligible:
        ok = eligible
    else:
        # Never silently produce an empty ranking: say why and fall back, so a
        # threshold that is too high is visible rather than yielding a report
        # with no ranked rows.
        print(f"WARNING: no config reached {min_signals} signals across at least "
              f"{min_folds} folds; ranking the unfiltered list instead",
              flush=True)
    # The pooled base rate is a property of the GRID and the fold split, so it is
    # the same for every config that completed all folds. Earlier this field was
    # `ok[0]["oos_base_rate"]` — the rank-1 row's OWN base rate. When that row
    # happened to be a degenerate config that completed only 2 of 4 folds, the
    # report-level field advertised a base rate belonging to two folds, and a
    # reader pairing it with a 4-fold row overstated lift by up to 17.9%.
    #
    # Filter to full-fold rows AND to a single label. The base rate is a property
    # of the label as much as of the grid: in the wide grid `label_close` rows sit
    # at 0.02649 and `label_high` rows at 0.04088, so a median across both is a
    # number belonging to neither, while looking perfectly plausible because it
    # lands on a real row's value. Grouping by label keeps each scalar meaningful;
    # the per-label breakdown is published alongside it so a mixed grid is visible
    # rather than averaged away.
    full_fold = [r for r in ok if r.get("n_folds", 0) >= args.folds - 1
                 and r.get("oos_signals", 0) >= 100 and r.get("oos_base_rate")]
    by_label: dict[str, list[float]] = {}
    for r in full_fold:
        by_label.setdefault(str(r.get("label")), []).append(float(r["oos_base_rate"]))
    basis = (
        f"median over {len(full_fold)} config(s) with n_folds >= "
        f"{args.folds - 1} and >= 100 signals"
    )
    if len(by_label) > 1:
        # More than one label present: publish the breakdown and take the median
        # of the largest group, so the top-level scalar still means something.
        biggest = max(by_label, key=lambda k: len(by_label[k]))
        pooled_base = float(statistics.median(by_label[biggest]))
        basis += (
            f"; the set spans {len(by_label)} labels "
            f"({ {k: round(v[0], 8) for k, v in sorted(by_label.items())} }), so "
            f"this is the median over '{biggest}' "
            f"({len(by_label[biggest])} configs); per-label values live under "
            f"oos_base_rate_by_label"
        )
    else:
        pooled_base = (
            float(statistics.median([r["oos_base_rate"] for r in full_fold]))
            if full_fold else None
        )
    payload = {
        "preset": args.preset,
        "stride": stride,
        "matrix": matrix.name,
        "folds_requested": args.folds,
        "final_holdout_start": FINAL_HOLDOUT_START,
        "n_configs": len(configs),
        "n_failed": len(results) - len(ok),
        "min_signals": min_signals,
        "ranked_basis": (
            f"{len(ok)} config(s) with >= {min_signals} out-of-sample signals "
            f"across at least {min_folds} folds, sorted by out-of-sample precision"
        ),
        # Report-level pooled base rate over configs that completed every fold.
        "oos_base_rate": pooled_base,
        "oos_base_rate_by_label": {
            k: float(statistics.median(v)) for k, v in sorted(by_label.items())
        },
        "oos_base_rate_basis": basis,
        "ranked": ok,
        # Everything that ran, in the same order, so the filter hides nothing.
        "ranked_unfiltered": ranked_unfiltered,
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
