"""Parallel driver for the full Web Pro strategy scan.

One worker process per shard, so each worker loads only its own slice of the
universe and memory stays bounded. Every stock is scanned at a fixed session
stride, all 36 Web Pro strategies are run, forward labels are attached, and a
per-strategy hit-rate report is written for each evaluation regime.

Usage
-----
    python -m src.build_shards --shards 8
    python -m src.scan_all --stride 5
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from src import labels, runner

REPO_ROOT = Path(__file__).resolve().parents[1]
SHARD_DIR = REPO_ROOT / "data" / "shards"
OUT_DIR = REPO_ROOT / "outputs"
REPORT_DIR = REPO_ROOT / "reports"

SHARD: pd.DataFrame | None = None
STRIDE = 5
MIN_HISTORY = runner.VISIBLE_BARS


def _work(path: str) -> tuple[pd.DataFrame, dict, dict]:
    assert SHARD is not None
    runner.reset_errors()
    targets = runner.build_scan_targets(SHARD, stride=STRIDE, min_history=MIN_HISTORY)
    if targets.empty:
        return pd.DataFrame(), {}, {}
    frame = runner.scan(SHARD, targets)
    return frame, dict(runner.LAST_ERRORS), dict(runner.LAST_ERROR_SAMPLES)


SIGNALS_CACHE = OUT_DIR / "webpro_signals_raw.parquet"


def collect_signals(shard_paths: list[str], n_workers: int, stride: int,
                    reuse: bool = True) -> pd.DataFrame:
    """Run (or reload) the sharded scan, returning one emitted-signal frame.

    The scan costs ~11 minutes on the full universe, so its result is cached.
    Reporting routines that change frequently then never force a rescan.
    """
    global STRIDE
    STRIDE = stride
    if reuse and SIGNALS_CACHE.exists():
        print(f"reusing cached scan: {SIGNALS_CACHE}", flush=True)
        return pd.read_parquet(SIGNALS_CACHE)

    t1 = time.time()
    frames: list[pd.DataFrame] = []
    all_errors: Counter = Counter()
    error_samples: dict[str, str] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_scan_one, path): path for path in shard_paths}
        for done, future in enumerate(as_completed(futures), 1):
            frame, errors, samples = future.result()
            frames.append(frame)
            all_errors.update(errors)
            error_samples.update(samples)
            print(f"  shard {done}/{len(shard_paths)} -> {len(frame)} rows "
                  f"({time.time()-t1:.0f}s)", flush=True)

    if all_errors:
        print("\n!! strategy errors were recorded (these points are NOT negatives):")
        for key, count in all_errors.most_common():
            print(f"   {key:36s} {count:8d}  e.g. {error_samples.get(key, '')[:110]}")
    else:
        print("\nno strategy errors: every point produced a decision")

    signals = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if signals.empty:
        raise SystemExit("scan produced no rows - refusing to write an empty report")
    print(f"emitted signals: {len(signals)} in {time.time()-t1:.0f}s", flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signals.to_parquet(SIGNALS_CACHE, index=False, compression="zstd")
    globals()["_LAST_ERRORS"] = all_errors
    return signals


def scan_all(stride: int, workers: int | None, codes_limit: int = 0,
             reuse: bool = True) -> dict:
    manifest = json.loads((SHARD_DIR / "manifest.json").read_text(encoding="utf-8"))
    shard_paths = [s["path"] for s in manifest["shards"]]
    if codes_limit:
        shard_paths = shard_paths[: max(1, codes_limit)]

    n_workers = workers or len(shard_paths)
    n_workers = min(n_workers, len(shard_paths))
    print(f"scanning {len(shard_paths)} shards with {n_workers} workers, stride={stride}",
          flush=True)

    t0 = time.time()
    signals = collect_signals(shard_paths, n_workers, stride, reuse=reuse)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    emitted = signals
    emitted.to_csv(OUT_DIR / "webpro_signals.csv", index=False)

    # The natural base rate must come from the whole evaluated population, not
    # from the signals, or "lift" would be measured against itself. Only the
    # label columns are read, so this stays cheap.
    baselines = population_baselines(shard_paths, stride)
    print("population base rates: " + json.dumps(baselines, indent=2), flush=True)
    (REPORT_DIR / "webpro_baselines.json").write_text(
        json.dumps(baselines, indent=2, ensure_ascii=False), encoding="utf-8")

    rows: list[dict] = []
    for sid, group in emitted.groupby("strategy_id", sort=False):
        report = {
            "strategy_id": sid,
            # NOTE: only *emitted signals* cross the worker boundary, so this
            # counts signals for this strategy — not the 493,246 points every
            # strategy was evaluated on. That shared count is in
            # reports/webpro_baselines.json.
            "signals_for_strategy": int(len(group)),
        }
        for regime in labels.REGIMES:
            sub = pd.DataFrame({
                "code": group["code"].to_numpy(),
                "date": group["date"].to_numpy(),
                "label_bull": group[f"label_bull__{regime}"].to_numpy(),
                "label_joint": group[f"label_joint__{regime}"].to_numpy(),
                "label_strict_low": group[f"label_strict_low__{regime}"].to_numpy(),
                "label_resolved": group[f"label_resolved__{regime}"].to_numpy(),
            })
            regime_report = labels.score_signals(
                sub, horizon=labels.REGIMES[regime][0], cooldown=60)
            base = baselines[regime]["bull_rate"]
            for k, v in regime_report.items():
                if k in ("cooldown", "horizon"):
                    continue
                report[f"{k}__{regime}"] = v
            precision = regime_report["bull_precision_deduped"]
            report[f"baseline__{regime}"] = base
            report[f"lift__{regime}"] = (
                precision / base if base and precision == precision else float("nan")
            )
            # Travel with the value: every `baseline__*` in this file comes from
            # the scanned grid. reports/lowzone_hit_rates.csv carries the same
            # two column names but its `baseline_rate` censuses the full panel,
            # so a reader must be able to tell the families apart without
            # re-deriving which script wrote the file.
            report[f"baseline_population__{regime}"] = (
                baselines[regime]["population"]["population_id"]
            )
        rows.append(report)

    report_frame = pd.DataFrame(rows)
    order = "bull_precision_deduped__webpro"
    if order in report_frame.columns:
        report_frame = report_frame.sort_values(order, ascending=False)
    report_frame.to_csv(REPORT_DIR / "webpro_hit_rates.csv", index=False)

    summary = {
        "stride": stride,
        "min_history": MIN_HISTORY,
        # Restated here because `stride` alone does not identify the population:
        # min_history is what removes the pre-2023-04-04 warm-up window.
        "population": labels.population_provenance(
            "scanned", stride=stride, min_history=MIN_HISTORY,
        ),
        "regimes": {k: {"horizon": v[0], "target_return": v[1], "strict_low": v[2]}
                    for k, v in labels.REGIMES.items()},
        "cooldown": 60,
        "shards": len(shard_paths),
        "signals_emitted": int(len(emitted)),
        "baselines": baselines,
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    (REPORT_DIR / "webpro_scan_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:1200])
    return summary


LABEL_COLUMNS = [
    "entry_open", "forward_max_return", "forward_min_return", "bars_to_target",
    "label_bull", "label_strict_low", "label_joint", "label_resolved",
]


def _scan_one(path: str) -> tuple[pd.DataFrame, dict, dict]:
    """Worker entry: load one shard, scan it, attach labels, keep signals only.

    The join happens inside the worker because each shard already carries its own
    label columns, and returning all 2.2M scored rows per shard to the parent
    would cost ~18M rows of IPC. Filtering to emitted signals first keeps the
    parent's footprint proportional to the number of *signals*, not points.
    """
    global SHARD
    SHARD = pd.read_parquet(path)
    runner.reset_errors()
    targets = runner.build_scan_targets(SHARD, stride=STRIDE, min_history=MIN_HISTORY)
    if targets.empty:
        return pd.DataFrame(), {}, {}

    frame = runner.scan(SHARD, targets)
    errors = dict(runner.LAST_ERRORS)
    samples = dict(runner.LAST_ERROR_SAMPLES)
    if frame.empty:
        return frame, errors, samples

    key = ["code", "date"]
    for regime in labels.REGIMES:
        key += [f"{c}__{regime}" for c in LABEL_COLUMNS]
    available = [c for c in key if c in SHARD.columns]
    frame = frame.merge(SHARD[available], on=["code", "date"], how="left")
    return frame[frame["prediction"] == 1].copy(), errors, samples


def population_baselines(shard_paths: list[str], stride: int) -> dict:
    """Natural outcome rate over the SCANNED evaluation grid, per regime.

    This is the population the strategies were actually scored on, so it is the
    correct denominator for a lift. It is deliberately *not* the same row set as
    ``backtest_lowzone.main``'s baseline, which censuses the full resolved panel:
    here a row survives only if the scan would have visited it —
    ``_seq >= MIN_HISTORY`` and then every ``stride``-th bar — whereas
    ``backtest_lowzone`` applies no stride and no minimum history. On this panel
    that is a difference in the *period* covered, not just a thinned sample:
    2,853 of 3,193 codes are present on the first session, so ``_seq >= 60``
    implies ``date >= 2023-04-04`` and the filter removes the 2023-Q1 warm-up
    window. The two payloads therefore disagree by ~1.8% (webpro), ~3.6% (low60)
    and ~10.3% (low504) in relative terms, and every payload carries a
    ``population`` block naming the row set it counted. See the "Baseline
    provenance" note in src/labels.py.

    Read shard by shard and only the label columns, so this never holds the full
    panel in memory. Applying the same stride as the scan matters: the base rate
    must be measured on the same population the strategies were scored over.
    """
    totals = {r: {"n": 0, "bull": 0, "joint": 0, "lo": None, "hi": None}
              for r in labels.REGIMES}
    for path in shard_paths:
        cols = ["code", "date"] + [
            f"{c}__{r}" for r in labels.REGIMES
            for c in ("label_bull", "label_joint", "label_resolved")
        ]
        frame = pd.read_parquet(path, columns=cols)
        if stride > 1:
            # cumcount must be taken on the full shard, then filtered, so the
            # stride aligns with the scan's own target selection.
            seq = frame.groupby("code", sort=False).cumcount()
            frame = frame[(seq >= MIN_HISTORY) & (seq % stride == 0)]
        for regime in labels.REGIMES:
            resolved = frame[frame[f"label_resolved__{regime}"]]
            totals[regime]["n"] += int(len(resolved))
            totals[regime]["bull"] += int(resolved[f"label_bull__{regime}"].fillna(0).sum())
            totals[regime]["joint"] += int(resolved[f"label_joint__{regime}"].fillna(0).sum())
            if len(resolved):
                # Tracked per regime, not globally: each contract has its own
                # resolvable span (a 504-session window runs out of future bars
                # far earlier than a 10-session one), so a single shared window
                # would misdescribe at least two of the three populations.
                lo, hi = resolved["date"].min(), resolved["date"].max()
                if totals[regime]["lo"] is None or lo < totals[regime]["lo"]:
                    totals[regime]["lo"] = lo
                if totals[regime]["hi"] is None or hi > totals[regime]["hi"]:
                    totals[regime]["hi"] = hi
    out = {}
    for regime, t in totals.items():
        out[regime] = {
            "evaluated_points": t["n"],
            "bull_rate": t["bull"] / t["n"] if t["n"] else float("nan"),
            "joint_rate": t["joint"] / t["n"] if t["n"] else float("nan"),
            "horizon": labels.REGIMES[regime][0],
            "target_return": labels.REGIMES[regime][1],
            "population": labels.population_provenance(
                "scanned", stride=stride, min_history=MIN_HISTORY,
                rows=t["n"], date_min=t["lo"], date_max=t["hi"],
            ),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--shards-limit", type=int, default=0)
    args = parser.parse_args()
    scan_all(args.stride, args.workers or None, codes_limit=args.shards_limit)


if __name__ == "__main__":
    main()
