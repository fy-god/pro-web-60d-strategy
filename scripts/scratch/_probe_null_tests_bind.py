"""Verify TARGET_70PCT.md's claims about the smaller null battery.

TARGET_70PCT.md:389-391 says reports/ml_null_tests.json reached the same
conclusion "by different means": permuted labels 3.11% vs 3.08% base, noise
features 4.06% vs 4.09%, and no feature exceeding AUC 0.68. The report was opened
by the audit only for its `stride` field, so none of those three claims was ever
compared to the payload. This checks each against the file.
"""
from __future__ import annotations

import io
import json

d = json.load(io.open("reports/ml_null_tests.json", encoding="utf-8"))

print("=" * 74)
print("permuted_labels")
print("=" * 74)
pl = d["permuted_labels"]
prec = pl["oos_precision"]
base = pl["oos_base_rate"]
print(f"  oos_precision  {[round(p*100, 4) for p in prec]}")
print(f"  oos_base_rate  {[round(b*100, 4) for b in base]}")
mean_p, mean_b = sum(prec) / len(prec), sum(base) / len(base)
print(f"  mean precision {mean_p*100:.4f}%  -> document says 3.11%")
print(f"  mean base      {mean_b*100:.4f}%  -> document says 3.08%")
print(f"  n_folds        {pl.get('n_folds')}")
print(f"  verdict        {pl.get('verdict')}  leak_factor {pl.get('leak_factor')}")

print()
print("=" * 74)
print("noise_features")
print("=" * 74)
nf = d["noise_features"]
print(f"  oos_precision  {nf['oos_precision']*100:.4f}%  -> document says 4.06%")
print(f"  oos_base_rate  {nf['oos_base_rate']*100:.4f}%  -> document says 4.09%")
print(f"  oos_signals    {nf['oos_signals']:,}")
print(f"  n_folds        {nf.get('n_folds')}")
print(f"  verdict        {nf.get('verdict')}")

print()
print("=" * 74)
print("feature_auc  (document: 'no feature exceeding AUC 0.68')")
print("=" * 74)
fa = d["feature_auc"]
top = fa.get("top") or []
if isinstance(top, dict):
    items = list(top.items())
else:
    items = [(t.get("feature"), t.get("auc")) for t in top]
mx = max(a for _, a in items)
for name, auc in items[:6]:
    print(f"    {name:<26} {auc:.4f}")
print(f"  max AUC = {mx:.6f}  ->  0.68 threshold: "
      f"{'OK (none exceeds)' if mx <= 0.68 else 'VIOLATED'}")
# Any feature anywhere above 0.68?
allmax = mx
if "all" in fa:
    print(f"  report also carries 'all' with {len(fa['all'])} entries")
print(f"  verdict field on report: {d.get('verdict')}")

print()
print("=" * 74)
ok = (abs(mean_p * 100 - 3.11) < 0.005
      and abs(mean_b * 100 - 3.08) < 0.005
      and abs(nf["oos_precision"] * 100 - 4.06) < 0.005
      and abs(nf["oos_base_rate"] * 100 - 4.09) < 0.005
      and mx <= 0.68)
print("RESULT:", "PASS -- all three document claims match the payload" if ok
      else "FAIL -- at least one claim does not match")
raise SystemExit(0 if ok else 1)
