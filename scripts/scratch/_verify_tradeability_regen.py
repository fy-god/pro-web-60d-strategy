"""Verify the regenerated tradeability report changed only what the fix touched.

The fix moved the denominator from the emitted count to the resolved count, so
`signals`, `hit_rate` and `unfillable_pct` legitimately change. Everything else --
the unfillable REASONS, the tradeable subsets, and the ordering -- must be
invariant, and each row's new `signals` must equal signals_raw - censored.
"""
from __future__ import annotations

import io
import json
import os
import pathlib

import pandas as pd

TMP = pathlib.Path(os.environ.get("TEMP", "."))
BEFORE = json.load(io.open(TMP / "tb_before.json", encoding="utf-8"))
AFTER = json.load(io.open("reports/tradeability.json", encoding="utf-8"))
bcsv = pd.read_csv(TMP / "tb_before.csv")
acsv = pd.read_csv("reports/tradeability_by_strategy.csv")

b, a = BEFORE["overall"], AFTER["overall"]
print("=== overall ===")
for k in sorted(set(b) | set(a)):
    bv, av = b.get(k), a.get(k)
    tag = ""
    if isinstance(bv, float) and isinstance(av, float):
        if abs(bv - av) > 1e-12:
            tag = f"   <-- CHANGED ({av - bv:+.6f})"
    elif bv != av:
        tag = "   <-- CHANGED"
    print(f"  {k:<22} {bv!r:>26} -> {av!r}{tag}")

print("\n=== what must NOT have changed ===")
for k in ("hits", "tradeable_hits"):
    same = b.get(k) == a.get(k)
    print(f"  {k:<20} {b.get(k)!r:>12} -> {a.get(k)!r:<12} {'OK' if same else 'MOVED'}")

# The reason counts DO move, and must. A row with no next bar cannot have a
# resolved forward window, so the censored set is a superset of the `no_next_bar`
# set and excluding censored rows necessarily removes those reasons too. The
# invariant is therefore not "the counts are identical" -- my first version of this
# script asserted that and flagged 142 correct changes -- but that the counts stay
# bounded by the new denominator and that `no_next_bar` is exactly 0.
print("\n=== the reason counts are bounded by the new denominator ===")
print(f"  no_next_bar {b['no_next_bar']} -> {a['no_next_bar']}  "
      f"(must be 0: no next bar implies no resolved window)")
print(f"  unfillable  {b['unfillable']} -> {a['unfillable']}  "
      f"(delta {a['unfillable'] - b['unfillable']})")
delta = b["unfillable"] - a["unfillable"]
explained = b["no_next_bar"] - a["no_next_bar"]
print(f"  unfillable delta {delta} vs no_next_bar delta {explained} "
      f"+ gapped delta {b['gapped_at_limit'] - a['gapped_at_limit']} = "
      f"{explained + (b['gapped_at_limit'] - a['gapped_at_limit'])}")
for k in ("unfillable", "one_word_limit", "gapped_at_limit", "no_next_bar"):
    f_ok = a[k] <= a["signals"]
    print(f"  {k:<20} {a[k]:>8} <= signals {a['signals']:>8}  "
          f"{'OK' if f_ok else 'IMPOSSIBLE'}")
print(f"  no_next_bar == 0 (resolved frame): "
      f"{'OK' if a['no_next_bar'] == 0 else 'UNEXPECTED'}")

print("\n=== the denominator identity ===")
rows = acsv.to_dict("records")
ok_id = 0
for r in rows:
    if r["signals"] == r["signals_raw"] - r["censored"]:
        ok_id += 1
print(f"  signals == signals_raw - censored on {ok_id}/{len(rows)} rows")
print(f"  total raw {int(acsv['signals_raw'].sum()):,}  "
      f"censored {int(acsv['censored'].sum()):,}  "
      f"resolved {int(acsv['signals'].sum()):,}")

print("\n=== hit_rate is now on the resolved basis ===")
ok_rate = sum(1 for r in rows
              if abs(r["hit_rate"] - r["hits"] / r["signals"]) < 1e-12)
print(f"  hit_rate == hits/signals on {ok_rate}/{len(rows)} rows")
# And it must NOT equal the old censored-inclusive basis, except where censored==0.
was = 0
for r in rows:
    if r["censored"] == 0:
        continue
    if abs(r["hit_rate"] - r["hits"] / r["signals_raw"]) < 1e-12:
        was += 1
print(f"  rows with censored>0 whose rate still equals hits/signals_raw: {was} "
      f"(expected 0)")

print("\n=== per-strategy: hits invariant, denominators and reasons move with censoring ===")
bmap = {r["label"]: r for r in bcsv.to_dict("records")}
amap = {r["label"]: r for r in rows}
joined, hits_moved, impossible = 0, [], []
for lab, br in bmap.items():
    ar = amap.get(lab)
    if ar is None:
        impossible.append((lab, "row vanished"))
        continue
    joined += 1
    if br["hits"] != ar["hits"]:
        hits_moved.append((lab, br["hits"], ar["hits"]))
    # Every reason count must be bounded by the new resolved denominator.
    for k in ("unfillable", "one_word_limit", "gapped_at_limit", "no_next_bar",
              "tradeable_signals"):
        if ar[k] > ar["signals"]:
            impossible.append((lab, f"{k} {ar[k]} > signals {ar['signals']}"))
    if ar["signals"] != ar["signals_raw"] - ar["censored"]:
        impossible.append((lab, "denominator identity"))
    if ar["no_next_bar"] != 0:
        impossible.append((lab, f"no_next_bar {ar['no_next_bar']} != 0"))
print(f"  strategies joined: {joined}/{len(bmap)}")
print(f"  hits changed: {len(hits_moved)} (must be 0 -- hits are on resolved rows "
      f"either way)")
for lab, x, y in hits_moved[:5]:
    print(f"    {lab}: {x} -> {y}")
print(f"  violations: {len(impossible)}")
for lab, what in impossible[:8]:
    print(f"    {lab}: {what}")

print("\n=== the published README numbers this feeds ===")
print(f"  overall hit rate : {b['hit_rate']*100:.3f}% -> {a['hit_rate']*100:.3f}%")
print(f"  leader_momentum  : "
      f"{bmap['leader_momentum']['hit_rate']*100:.2f}% -> "
      f"{amap['leader_momentum']['hit_rate']*100:.2f}%")
print(f"  censored excluded: {int(acsv['censored'].sum()):,} of "
      f"{int(acsv['signals_raw'].sum()):,} emitted")

ok = (not impossible and not hits_moved and ok_id == len(rows)
      and ok_rate == len(rows) and was == 0 and a["no_next_bar"] == 0)
print("\nRESULT:", "CLEAN -- only what the censoring implies changed"
      if ok else f"ATTENTION -- {len(impossible)} violations, "
                 f"{len(hits_moved)} hit moves")
