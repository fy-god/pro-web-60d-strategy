"""Verify search.py's new ranking filter and per-label base rate.

Reproduces the selection logic against the real ml_search_wide.json rows, without
re-running the search. Confirms (a) the 3-signal row no longer ranks, (b) the
filtering keeps the large-n rows, (c) the mixed-label population is detected.
"""
from __future__ import annotations

import io
import json
import statistics

FOLDS = 5
MIN_SIGNALS = 250
MIN_FOLDS = FOLDS - 1

with io.open("reports/ml_search_wide.json", encoding="utf-8") as fh:
    doc = json.load(fh)
rows = doc["ranked"]

ok = sorted(rows, key=lambda r: -r["oos_precision"])
eligible = [r for r in ok
            if r.get("oos_signals", 0) >= MIN_SIGNALS
            and r.get("n_folds", 0) >= MIN_FOLDS]

print(f"rows: {len(rows)}   eligible (>= {MIN_SIGNALS} sig, >= {MIN_FOLDS} folds): "
      f"{len(eligible)}")
print("\nrank 1 BEFORE the filter:", ok[0]["config"],
      f"{ok[0]['oos_precision']*100:.2f}% on {ok[0]['oos_signals']} signals, "
      f"{ok[0]['n_folds']} folds")
print("rank 1 AFTER  the filter:", eligible[0]["config"],
      f"{eligible[0]['oos_precision']*100:.2f}% on "
      f"{eligible[0]['oos_signals']} signals, "
      f"{eligible[0]['n_folds']} folds")

# The degenerate row must be absent from the ranked list and present in the
# unfiltered one.
names = {r["config"] for r in eligible}
print(f"\nfiltered out: {[r['config'] for r in ok if r['config'] not in names]}")

# Per-label base rate: the point of the change.
full = [r for r in ok if r.get("n_folds", 0) >= FOLDS - 1
        and r.get("oos_signals", 0) >= 100 and r.get("oos_base_rate")]
by_label: dict[str, list[float]] = {}
for r in full:
    by_label.setdefault(str(r.get("label")), []).append(float(r["oos_base_rate"]))

print(f"\nfull-fold rows: {len(full)}")
for k in sorted(by_label):
    vals = by_label[k]
    print(f"  label {k:12s} n={len(vals):3d}  "
          f"base={statistics.median(vals):.8f}  "
          f"distinct={len(set(round(v, 10) for v in vals))}")
labels_present = len(by_label)
print(f"\ndistinct labels in the pooled population: {labels_present}")
print("mixed-label population detected:", labels_present > 1)
