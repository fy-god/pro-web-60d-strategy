"""Check audit/README.md's claims about THIS repository's own backtest.

audit/README.md lines 68-69 make two numeric claims about this repo:

  "V07/V08 in-sample hits (4.23%/4.08%) do not beat the honest walk-forward
   V03 (4.37%)"
  "4.37% at the 10-session/+30% contract; 0.15% at the 60-session/4x contract"

No check reads audit/README.md at all, so these have never been verified against
reports/lowzone_hit_rates.csv. This checks each claim.
"""
from __future__ import annotations

import csv
import io

rows = list(csv.DictReader(io.open("reports/lowzone_hit_rates.csv", encoding="utf-8")))
# `version` alone is NOT a unique key: the file holds 7 versions x 2 regimes, so
# V00-V08 each appear twice. Keying on version alone silently keeps whichever
# regime happens to sort last and makes every cross-regime claim look wrong --
# which is exactly the false alarm this script produced on its first run.
by_key = {(r["version"], r["regime"]): r for r in rows}
vers = sorted({r["version"] for r in rows})
regs = sorted({r["regime"] for r in rows})
print(f"{len(rows)} rows = {len(vers)} versions x {len(regs)} regimes "
      f"({', '.join(regs)})")
print(f"`version` is unique within a regime: "
      f"{len(by_key) == len(rows)}\n")

print("version  regime  model  hit_rate_pct  signals  baseline   lift")
for r in rows:
    print(f"{r['version']:<8} {r['regime']:<7} {r['model']:<6} "
          f"{float(r['hit_rate_pct']):>10.4f}%  {int(r['signals_deduped']):>7,}  "
          f"{float(r['baseline_rate']):.6f}  {float(r['lift_vs_baseline']):.4f}")

print("\n" + "=" * 74)
print("claim: 'the honest walk-forward V03 (4.37%)'")
print("=" * 74)
v03 = by_key.get(("V03", "webpro"))
if v03:
    print(f"  V03 hit_rate_pct = {float(v03['hit_rate_pct']):.4f}%")
    print(f"  V03 regime       = {v03['regime']}")
    print(f"  V03 model        = {v03['model']}")
    print(f"  in_sample        = {v03['in_sample']}")
    print(f"  document says 4.37% -> "
          f"{'MATCH' if abs(float(v03['hit_rate_pct']) - 4.37) < 0.005 else 'MISMATCH'}")
else:
    print("  V03 not present")

print("\n" + "=" * 74)
print("claim: 'V07/V08 in-sample hits (4.23%/4.08%)'")
print("=" * 74)
for vid, want in (("V07", 4.23), ("V08", 4.08)):
    r = by_key.get((vid, "webpro"))
    if r:
        got = float(r["hit_rate_pct"])
        print(f"  {vid} hit_rate_pct = {got:.4f}%  in_sample={r['in_sample']}  "
              f"-> doc {want}%  "
              f"{'MATCH' if abs(got - want) < 0.005 else 'MISMATCH'}")
    else:
        print(f"  {vid} not present")

print("\n" + "=" * 74)
print("claim: '0.15% at the 60-session/4x contract'")
print("=" * 74)
# low60/low504 are the 60-session/4x contracts. Look for the lowest hit rate.
for r in rows:
    if r["regime"] in ("low60", "low504"):
        print(f"  {r['version']:<8} {r['regime']:<7} "
              f"{float(r['hit_rate_pct']):.4f}%  signals {int(r['signals_deduped']):,}")
regimes = {r["regime"] for r in rows}
print(f"\n  regimes present: {sorted(regimes)}")
if "low60" not in regimes and "low504" not in regimes:
    print("  NOTE: this CSV holds only the webpro regime; the 60-session/4x")
    print("        contracts are in webpro_hit_rates.csv instead.")
    wrows = list(csv.DictReader(
        io.open("reports/webpro_hit_rates.csv", encoding="utf-8")))
    rates = []
    for r in wrows:
        for col in ("bull_precision_deduped__low60",
                    "bull_precision_deduped__low504"):
            v = r.get(col)
            if v not in (None, ""):
                rates.append((r["strategy_id"], col.split("__")[-1], float(v)))
    if rates:
        rates.sort(key=lambda t: t[2])
        print(f"\n  lowest 60-session/4x bull precisions across "
              f"{len(wrows)} strategies:")
        for sid, rg, v in rates[:6]:
            print(f"    {sid:<22} {rg:<8} {v*100:.4f}%")
        print(f"\n  document says 0.15% -> the minimum found is "
              f"{rates[0][2]*100:.4f}%")
