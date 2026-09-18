"""Blast radius of the P0-A comparator fix on the PUBLISHED label_joint numbers.

Changing the first-hit freeze from `>=` to `>` alters `label_strict_low` and hence
`label_joint` on exactly the rows where some bar's high EQUALS entry*(1+target).
Real A-share prices are cent-quantised, so an exact touch is plausible rather than
measure-zero -- entry 10.00 gives target 13.00, a legal high.

The shards (and therefore every published joint_rate) were built with the old
`>=` code. This loads the raw panel ONCE and counts, per regime, how many scans of
the window hit the target exactly and how many of those would flip the joint label.
It writes a report; it does not rebuild the shards.
"""
from __future__ import annotations

import io
import json
import sys

import numpy as np
import pandas as pd

from src import labels

print("loading the raw panel once ...", flush=True)
from src import data_pipeline

panel = data_pipeline.load_panel()
print(f"  panel rows: {len(panel):,}", flush=True)

sub = panel.sort_values(["code", "date"]).reset_index(drop=True)
codes = sub["code"].to_numpy()
highs = sub["high"].to_numpy(dtype="float64")
lows = sub["low"].to_numpy(dtype="float64")
opens = sub["open"].to_numpy(dtype="float64")
n = len(sub)

results = {}
for regime, (horizon, target_return, strict_low_ratio) in labels.REGIMES.items():
    print(f"\nregime {regime}: horizon={horizon} target={target_return} "
          f"strict_low={strict_low_ratio}", flush=True)
    entry = np.full(n, np.nan)
    entry[:-1] = opens[1:]
    same_next = np.zeros(n, dtype=bool)
    same_next[:-1] = codes[1:] == codes[:-1]
    entry[~same_next] = np.nan
    target = entry * (1.0 + target_return)

    exact_touch = 0          # a bar whose high == target exactly
    exact_is_first = 0       # ... and it is the first bar to reach the target
    joint_flips = 0          # ... and the joint label differs between >= and >
    rows_with_any_touch = 0

    run_min = np.full(n, np.inf)
    seen = np.zeros(n, dtype=bool)
    for d in range(1, horizon + 1):
        if d >= n:
            break
        sl = slice(0, n - d)
        sh = slice(d, n)
        same = codes[sh] == codes[sl]
        high_d = np.full(n, np.nan)
        low_d = np.full(n, np.nan)
        high_d[sl] = np.where(same, highs[sh], np.nan)
        low_d[sl] = np.where(same, lows[sh], np.nan)
        valid = np.isfinite(high_d)
        run_min = np.where(valid, np.minimum(run_min, low_d), run_min)
        seen |= valid

        # exact equality, on resolved rows with a finite target
        eq = valid & np.isfinite(target) & (high_d == target)
        exact_touch += int(eq.sum())

        # First-hit freeze, both ways, recording the path low each gives.
        ge_new = eq | (valid & np.isfinite(target) & (high_d > target))
        # `>=` freeze == eq | `>`; `>` freeze == strict only. Both stop at the
        # same bar UNLESS the exact-touch bar is the first to reach the target.
        first_strict = valid & np.isfinite(target) & (high_d > target)
        # Detect "the exact-touch bar precedes any strict exceed": track state.
        if d == 1:
            hit_ge = np.zeros(n, dtype=bool)
            hit_gt = np.zeros(n, dtype=bool)
            low_ge = np.full(n, np.nan)
            low_gt = np.full(n, np.nan)
        newly_ge = (~hit_ge) & ge_new
        low_ge[newly_ge] = run_min[newly_ge]
        hit_ge |= newly_ge
        newly_gt = (~hit_gt) & first_strict
        low_gt[newly_gt] = run_min[newly_gt]
        hit_gt |= newly_gt

    # Where the two freezes gave DIFFERENT path lows, the strict-low/joint outcome
    # can differ. Count only rows where it actually does.
    finite_both = np.isfinite(low_ge) & np.isfinite(low_gt)
    differed = finite_both & (low_ge != low_gt)
    resolved = seen & (np.arange(n) + 0 < n)
    # strict_low: gate_low >= ratio*entry
    ge_gate = np.where(np.isfinite(low_ge), low_ge, -np.inf) >= strict_low_ratio * entry
    gt_gate = np.where(np.isfinite(low_gt), low_gt, -np.inf) >= strict_low_ratio * entry
    both_hit = np.isfinite(low_ge) & np.isfinite(low_gt)
    flips = both_hit & (ge_gate != gt_gate)

    rows_with_any_touch = int(np.isfinite(low_ge).sum())
    exact_touch_rows = int((np.isfinite(low_ge) & np.isfinite(low_gt)
                            & (low_ge != low_gt)).sum())
    results[regime] = {
        "panel_rows": n,
        "rows_with_a_resolved_window": rows_with_any_touch,
        "bar_level_exact_touches": exact_touch,
        "rows_where_the_two_freezes_differ": int(differed.sum()),
        "strict_low_outcome_flips": int(flips.sum()),
        "flip_share_of_resolved": (float(flips.sum()) / rows_with_any_touch
                                   if rows_with_any_touch else 0.0),
    }
    print(f"  rows with a resolved window      : {rows_with_any_touch:,}")
    print(f"  bar-level exact touches (high==E) : {exact_touch:,}")
    print(f"  rows where the freezes differ     : {int(differed.sum()):,}")
    print(f"  strict_low outcome flips          : {int(flips.sum()):,}")
    if rows_with_any_touch:
        print(f"  flip share of resolved            : "
              f"{flips.sum()/rows_with_any_touch*100:.6f}%")

with io.open("scripts/scratch/_p0a_blast_radius.json", "w",
             encoding="utf-8") as fh:
    json.dump(results, fh, indent=2)
print("\nwrote scripts/scratch/_p0a_blast_radius.json")
