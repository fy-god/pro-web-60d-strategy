"""Reproduce the two P0 defects the 18:59 expert-ML audit reported.

P0-A  src/labels.py:169 freezes the first-hit path on `high_d >= target` while the
      bull label (lines 186/188) uses strict `>`. The two comparators disagree, so
      `path_low_to_hit` can stop at a bar that only TOUCHED the threshold.

P0-B  src/scan_all.py:254 gates the warm-up filter behind `if stride > 1:`, but
      src/runner.py::build_scan_targets applies `_seq >= min_history`
      unconditionally. At stride=1 the baseline therefore counts the first 60
      warm-up bars per stock that the scan never visits.

Both are reproduced here from the real functions, not re-implemented.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

from src import labels, runner, scan_all

print("=" * 74)
print("P0-A  strict '>' vs first-hit '>=' in forward_outcomes")
print("=" * 74)

# Independently build the reviewer's counterexample.
#   E = 10, threshold 13 (+30%).  Day 1 high=13.00 (exactly on), low=9.00.
#   Day 2 high=13.10 (first STRICT exceed), low=7.00.
# Entry is bar 0's next open = bar 1's open = 10.0.
rows = []
dates = pd.bdate_range("2024-01-01", periods=6)
spec = {
    0: dict(open=10.0, high=10.0, low=10.0, close=10.0),
    1: dict(open=10.0, high=13.00, low=9.00, close=10.0),   # touches 13 exactly
    2: dict(open=10.0, high=13.10, low=7.00, close=10.0),   # first strict exceed
    3: dict(open=10.0, high=10.0, low=10.0, close=10.0),
    4: dict(open=10.0, high=10.0, low=10.0, close=10.0),
    5: dict(open=10.0, high=10.0, low=10.0, close=10.0),
}
for i, d in enumerate(dates):
    s = spec[i]
    rows.append({"code": "000001", "date": d, "volume": 1000.0, **s})

df = pd.DataFrame(rows)
df["code"] = df["code"].astype(str)
df["date"] = pd.to_datetime(df["date"])

out = labels.forward_outcomes(df, horizon=5, target_return=0.30)
row = out.iloc[0]
print(f"  entry_open        = {row['entry_open']}")
print(f"  target (1.30*E)   = {1.30 * row['entry_open']}")
print(f"  forward_max_return= {row['forward_max_return']:.6f}")
print(f"  bars_to_target    = {row['bars_to_target']}")
print(f"  forward_min_return= {row['forward_min_return']:.6f}")
print(f"  label_bull        = {row['label_bull']}")
print(f"  label_strict_low  = {row['label_strict_low']}")
print(f"  label_joint       = {row['label_joint']}")

# What SHOULD happen under one consistent strict-`>` rule:
#   the first strict exceed is bar index 2 (entry-relative d=2), where low=7.00.
#   risk-first: 7.00 < 0.8*10 = 8.0 -> strict_low must be 0, joint must be 0.
print()
print("  under one consistent strict-'>' rule:")
print(f"    first strict hit      = d=2 (high 13.10 > 13)")
print(f"    gate low up to hit    = 7.00")
print(f"    strict_low (7.00>=8.0)= 0")
print(f"    joint                 = 0")
print()
p0a = (row["bars_to_target"] == 1 and row["label_joint"] == 1.0)
print("  REPRODUCED: froze at d=1 (the ==target bar -> joint=1, should be d=2/joint=0)"
      if p0a else
      "  NOT reproduced (fixed?): bars_to_target="
      f"{row['bars_to_target']}, joint={row['label_joint']}")

print()
print("=" * 74)
print("P0-B  stride=1 baseline counts warm-up bars the scan never visits")
print("=" * 74)

# 2 stocks x 65 bars, MIN_HISTORY = 60.
n = 65
recs = []
for code in ("000001", "000002"):
    for i, d in enumerate(pd.bdate_range("2024-01-01", periods=n)):
        recs.append({"code": code, "date": d, "open": 10.0, "high": 10.0,
                     "low": 10.0, "close": 10.0, "volume": 1000.0})
panel = pd.DataFrame(recs)
panel["code"] = panel["code"].astype(str)
panel["date"] = pd.to_datetime(panel["date"])

targets = runner.build_scan_targets(panel, stride=1, min_history=60)
print(f"  panel rows                        = {len(panel)}")
print(f"  build_scan_targets(stride=1)      = {len(targets)} rows "
      f"(expected 2 stocks x 5 bars = 10)")

# Call the REAL function, so this measures the shipped code rather than a copy of
# the old guard.
tmp = pathlib.Path("scripts/scratch/_p0b_shard.parquet")
base = panel.copy()
for r in labels.REGIMES:
    base[f"label_bull__{r}"] = 1.0
    base[f"label_joint__{r}"] = 1.0
    base[f"label_resolved__{r}"] = True
base.to_parquet(tmp, index=False)
try:
    got = scan_all.population_baselines([str(tmp)], stride=1)
    baseline_n = got["webpro"]["evaluated_points"]
finally:
    tmp.unlink(missing_ok=True)
print(f"  panel rows                        = {len(panel)}")
print(f"  build_scan_targets(stride=1)      = {len(targets)} rows "
      f"(expected 2 stocks x 5 bars = 10)")
print(f"  population_baselines(stride=1)    = {baseline_n} rows")
print(f"  warm-up rows wrongly included     = {baseline_n - len(targets)}")
print()
p0b = baseline_n != len(targets)
print(f"  REPRODUCED: baseline {baseline_n} != scan targets {len(targets)}"
      if p0b else
      f"  FIXED: baseline and scan targets both {baseline_n}")

# And show the guard is harmless at stride 5 (both agree), which is why the
# shipped stride-5 report was never affected and the bug stayed hidden.
t5 = runner.build_scan_targets(panel, stride=5, min_history=60)
f5 = panel.copy()
s5 = f5.groupby("code", sort=False).cumcount()
if 5 > 1:
    f5 = f5[(s5 >= 60) & (s5 % 5 == 0)]
print(f"\n  at stride=5: targets={len(t5)} baseline_rows={len(f5)} "
      f"-> {'agree' if len(t5) == len(f5) else 'DISAGREE'}")
