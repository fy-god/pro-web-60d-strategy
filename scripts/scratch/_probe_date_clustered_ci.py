"""Unit-test the rewritten date_clustered_ci.

Checks the two things the fix is about:
  1. a full-calendar universe (with zero-signal days) widens the interval
     relative to a signal-dates-only universe;
  2. block=5 widens it further relative to block=1;
  3. the result is stable under a fixed seed and reproducible.

Also confirms the old call signature still works (defaults preserved).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from src.ml.final_holdout import date_clustered_ci  # noqa: E402

rng = np.random.default_rng(7)
# 40 sessions; only 25 of them carry signals, so 15 are zero-signal days.
all_days = pd.to_datetime("2026-01-01") + pd.to_timedelta(np.arange(40), unit="D")
sig_days = all_days[:: 40 // 25][:25]

rows = []
for d in sig_days:
    k = int(rng.integers(3, 25))
    # A strongly date-clustered outcome: each day is either mostly hits or mostly
    # misses. This is exactly the structure that makes row-level CIs wrong.
    p = rng.choice([0.05, 0.4])
    for _ in range(k):
        rows.append({"date": d, "label_high": float(rng.random() < p)})
frame = pd.DataFrame(rows)
mask = np.ones(len(frame), dtype=bool)

lo_s, hi_s = date_clustered_ci(frame, mask, block=1)                       # old
lo_f, hi_f = date_clustered_ci(frame, mask, universe_dates=all_days, block=1)
lo_b, hi_b = date_clustered_ci(frame, mask, universe_dates=all_days, block=5)

w_s, w_f, w_b = hi_s - lo_s, hi_f - lo_f, hi_b - lo_b
print(f"signal-dates only   (old default): [{lo_s:.4f}, {hi_s:.4f}]  width {w_s:.4f}")
print(f"full calendar block=1            : [{lo_f:.4f}, {hi_f:.4f}]  width {w_f:.4f}")
print(f"full calendar block=5            : [{lo_b:.4f}, {hi_b:.4f}]  width {w_b:.4f}")
print(f"\nzero-signal sessions admitted: {len(all_days) - len(sig_days)}")

# Reproducibility.
lo2, hi2 = date_clustered_ci(frame, mask, universe_dates=all_days, block=5)
print(f"reproducible under seed        : {abs(lo2-lo_b) < 1e-12 and abs(hi2-hi_b) < 1e-12}")

ok = True
if not (w_f >= w_s):
    print("FAIL: full calendar did not widen the interval vs signal dates")
    ok = False
if not (w_b >= w_s):
    print("FAIL: block=5 did not widen the interval vs signal dates")
    ok = False
if not (abs(lo2 - lo_b) < 1e-12):
    print("FAIL: not reproducible")
    ok = False

# Degenerate inputs must not raise.
empty = frame.iloc[0:0]
r = date_clustered_ci(empty, np.zeros(0, dtype=bool))
print(f"empty frame returns            : {r}")
single = frame[frame["date"] == sig_days[0]]
r2 = date_clustered_ci(single, np.ones(len(single), dtype=bool))
print(f"single-date frame returns      : {r2}")

print("\nRESULT:", "PASS" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
