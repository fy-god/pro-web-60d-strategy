"""Is accumulation_base's THRESHOLD of 0.90 reachable?

The strategies audit reported the threshold is unreachable (max achievable score
~0.6828), which would explain why the strategy emits ZERO signals over the whole
evaluated universe -- the one documented anomaly in the family.

The score is 0.25*(range_compression + pnva + stable_turnover +
improving_close_location), each component clipped to [0,1], so the arithmetic
ceiling is 1.0 and a threshold of 0.90 is not impossible in principle. What matters
is the achievable maximum on real data. This scans ONE shard and reports the max,
the p99.9, and how many targets clear 0.90 -- using the project's own runner so the
cards are built exactly as the backtest builds them.
"""
from __future__ import annotations

import glob
import io
import json

import numpy as np
import pandas as pd

from experts.strategies import accumulation_base as strat
from src import runner

shards = sorted(glob.glob("data/shards/shard_*.parquet"))
print(f"shards found: {len(shards)}")
path = shards[0]
print(f"scanning {path}")

frame = pd.read_parquet(path)
print(f"  shard rows: {len(frame):,}  cols: {len(frame.columns)}")

targets = runner.build_scan_targets(frame, stride=5, min_history=runner.VISIBLE_BARS)
print(f"  targets at stride 5: {len(targets):,}")
if targets.empty:
    raise SystemExit("no targets")

runner.reset_errors()
out = runner.scan(frame, targets, strategy_ids=[strat.STRATEGY_ID])
print(f"  scan columns: {list(out.columns)[:12]}")

# Find the score column THIS strategy produced. The runner writes one prediction
# and one score per (target, strategy), so match on the id suffix.
score_col = next(
    (c for c in out.columns
     if strat.STRATEGY_ID in c and "score" in c.lower()),
    None)
if score_col is None:
    score_col = next((c for c in out.columns if c.lower() == "score"), None)
print(f"  score column: {score_col}")
if score_col is None:
    print("  available:", list(out.columns))
    raise SystemExit("cannot find score column")

s = pd.to_numeric(out[score_col], errors="coerce").dropna()
print(f"\n=== accumulation_base score distribution on one shard ===")
print(f"  n           : {len(s):,}")
print(f"  min / max   : {s.min():.6f} / {s.max():.6f}")
print(f"  mean        : {s.mean():.6f}")
for q in (0.5, 0.9, 0.99, 0.999, 0.9999):
    print(f"  p{q * 100:<7.2f}   : {s.quantile(q):.6f}")
print(f"  arithmetic ceiling (0.25 * 4)  : 1.000000")
th = strat.THRESHOLD
print(f"  THRESHOLD                      : {th}")
print(f"  rows with score >= THRESHOLD   : {int((s >= th).sum()):,}")
print(f"  runner predictions == 1        : {int((out['prediction'] == 1).sum())}")

print(f"\n=== is 0.90 reachable at all? ===")
print(f"  observed max {s.max():.6f} vs threshold {th}  ->  "
      f"{'REACHABLE' if s.max() >= th else 'UNREACHABLE on this shard'}")
frac = float((s >= th).mean())
print(f"  share of targets clearing it: {frac:.8f}")

json.dump({"shard": path, "n": int(len(s)), "max": float(s.max()),
           "min": float(s.min()), "mean": float(s.mean()),
           "ceiling": 1.0, "threshold": th,
           "n_at_or_above": int((s >= th).sum()),
           "share_at_or_above": frac,
           "quantiles": {str(q): float(s.quantile(q))
                         for q in (0.5, 0.9, 0.99, 0.999, 0.9999)}},
          io.open("scripts/scratch/_accum.md.json", "w", encoding="utf-8"), indent=2)
print("\nwrote scripts/scratch/_accum.md.json")
