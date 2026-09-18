"""Check whether TARGET section 7's null table mixes base-rate pooling bases.

Line 339 (the real control) prints 4.09% / 3.91x, which the correction blockquote
identifies as the ratio-of-sums pooling. The ten null rows below print base rates
like 3.1%, 4.12%, 5.48%. If those come from the report's per-variant
`oos_base_rate` field, this script determines which pooling THAT field uses, so we
can say whether the table is internally consistent or silently mixes two bases.
"""
from __future__ import annotations

import io
import json

d = json.load(io.open("outputs/ml/audit/nulls_audit.json", encoding="utf-8"))
rows = d.get("results") or []
print(f"{len(rows)} result rows\n")
print(f"{'config':<22} {'prec':>7} {'base':>8} {'lift':>6}  keys present")
for r in rows:
    keys = [k for k in r.keys()
            if "base" in k.lower() or "pool" in k.lower()]
    print(f"{str(r.get('config')):<22} "
          f"{(r.get('oos_precision') or 0)*100:>6.2f}% "
          f"{(r.get('oos_base_rate') or 0)*100:>7.4f}% "
          f"{(r.get('oos_lift') or 0):>6.2f}  {keys}")

print()
# Does the report distinguish pooling variants for any row?
allkeys = set()
for r in rows:
    allkeys |= set(r.keys())
print("all keys in results rows:", sorted(allkeys))
print()
print("top-level summary keys:", sorted(d.keys()))
for k in sorted(d.keys()):
    v = d[k]
    if isinstance(v, (int, float, str)) and ("base" in k.lower() or "lift" in k.lower()
                                             or "pool" in k.lower()):
        print(f"  {k} = {v}")

real = next((r for r in rows if r.get("config") == "real"), None)
if real:
    print("\nreal row:")
    for k, v in real.items():
        print(f"   {k} = {v}")
    p, b = real.get("oos_precision"), real.get("oos_base_rate")
    if p and b:
        print(f"\n   precision/base = {p/b:.4f}  (document prints 3.91x)")
        print(f"   with 0.040878 base  = {p/0.04087801:.4f}  "
              f"(the ratio-of-sums figure)")
