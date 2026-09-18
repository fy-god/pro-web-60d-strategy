"""Definitive: is accumulation_base's 0.90 threshold reachable anywhere?

One shard gave max 0.835167 against a 0.90 threshold, but the strategies audit
reported a max of 0.6828. Two different numbers for the same quantity means one of
them is measuring a different thing, so this scans ALL eight shards at the scan's
own stride and reports the global maximum, the shard that produced it, and the
count of targets clearing the threshold anywhere in the universe.

This is the whole reason the strategy emits zero signals -- the only such anomaly
in the 36-strategy family -- so it is worth pinning exactly.
"""
from __future__ import annotations

import glob
import io
import json

import pandas as pd

from experts.strategies import accumulation_base as strat
from src import runner

shards = sorted(glob.glob("data/shards/shard_*.parquet"))
print(f"scanning {len(shards)} shards at stride 5, min_history "
      f"{runner.VISIBLE_BARS}, THRESHOLD {strat.THRESHOLD}\n")

rows = []
overall_max = -1.0
overall_argmax = None
total_targets = 0
total_hits = 0
for i, path in enumerate(shards):
    frame = pd.read_parquet(path)
    targets = runner.build_scan_targets(frame, stride=5,
                                        min_history=runner.VISIBLE_BARS)
    if targets.empty:
        print(f"  [{i}] {path.split(chr(92))[-1]}  no targets")
        continue
    out = runner.scan(frame, targets, strategy_ids=[strat.STRATEGY_ID])
    s = pd.to_numeric(out["score"], errors="coerce").dropna()
    n_hit = int((s >= strat.THRESHOLD).sum())
    total_targets += len(s)
    total_hits += n_hit
    mx = float(s.max())
    where = int(s.idxmax())
    code = out.loc[where, "code"] if where in out.index else "?"
    date = out.loc[where, "date"] if where in out.index else "?"
    if mx > overall_max:
        overall_max, overall_argmax = mx, (code, str(date))
    rows.append({"shard": path, "n": int(len(s)), "max": mx,
                 "mean": float(s.mean()), "at_or_above": n_hit,
                 "argmax_code": str(code), "argmax_date": str(date)})
    print(f"  [{i}] {path.split(chr(92))[-1]}  n={len(s):>7,}  "
          f"max={mx:.6f}  mean={s.mean():.4f}  >=T: {n_hit}")

print(f"\n=== global result ===")
print(f"  targets scanned        : {total_targets:,}")
print(f"  arithmetic ceiling     : 1.000000  (0.25 * 4 clipped components)")
print(f"  THRESHOLD              : {strat.THRESHOLD}")
print(f"  observed GLOBAL maximum: {overall_max:.6f}")
print(f"  reached at             : code={overall_argmax[0]} date={overall_argmax[1]}")
print(f"  targets >= THRESHOLD   : {total_hits}")
print(f"  headroom to threshold  : {strat.THRESHOLD - overall_max:.6f}")
print(f"  -> {'REACHABLE' if total_hits else 'UNREACHABLE over the whole universe'}")

per_shard_max = max(r["max"] for r in rows)
print(f"\n  the highest single-shard max is {per_shard_max:.6f}; the reviewer's "
      f"0.6828 was therefore not the global maximum.")

json.dump({"threshold": strat.THRESHOLD, "global_max": overall_max,
           "argmax": {"code": overall_argmax[0], "date": overall_argmax[1]},
           "n_targets": total_targets, "n_at_or_above": total_hits,
           "headroom": strat.THRESHOLD - overall_max, "shards": rows},
          io.open("scripts/scratch/_accum_all.json", "w", encoding="utf-8"),
          indent=2)
print("wrote scripts/scratch/_accum_all.json")
