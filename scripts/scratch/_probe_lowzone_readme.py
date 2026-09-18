"""Do the README's low-zone figures match reports/lowzone_hit_rates.csv?

The source fix (src/backtest_lowzone.py) stopped thresholding 2024 on 2024's own
quantile, and the README section was rewritten with the equal-footing counterfactual
figures. But the CSV was never regenerated, so it still holds the LEAKED numbers.

If the two disagree, the repository ships a table that contradicts its own artifact
-- and the audit is green, which means nothing binds them. This measures that
disagreement precisely, per (version, regime), for the eight published rows.
"""
from __future__ import annotations

import io
import json
import pathlib
import re

import pandas as pd

csv = pd.read_csv("reports/lowzone_hit_rates.csv")
print("=== reports/lowzone_hit_rates.csv ===")
print(f"  columns: {list(csv.columns)}")
print(f"  rows: {len(csv)}  versions: {sorted(csv['version'].unique())}")
print()
print(csv[["version", "regime", "in_sample", "signals_deduped", "bull_hits",
           "bull_precision", "baseline_rate"]].to_string(index=False))

readme = pathlib.Path("README.md").read_text(encoding="utf-8")
# The README's low-zone table has no bold on the version:
#   | V03 | webpro | 26,897 | 1,176 | **4.37%** | 1.42x | gain model (best honest) |
pat = re.compile(
    r"^\|\s*(V\d\d)\s*\|\s*(webpro|low60 \(4x\)|low504)\s*\|([^|]*)\|([^|]*)\|"
    r"\s*\*{0,2}([\d.]+)%\*{0,2}\s*\|", re.M)
rows = pat.findall(readme)
print(f"\n=== README low-zone table rows parsed: {len(rows)} ===")
for v, reg, sig, hits, prec in rows:
    print(f"  {v} {reg:<7} signals={sig.strip():<8} hits={hits.strip():<6} "
          f"precision={prec}%")

print("\n=== comparison ===")
c = {(r["version"], r["regime"]): r for r in csv.to_dict("records")}
print(f"{'(version, regime)':<20}{'CSV precision':>15}{'README':>10}  match")
print("-" * 62)
diffs = []
for v, reg, sig, hits, prec in rows:
    key = (v, reg)
    if key not in c:
        print(f"{str(key):<20}{'MISSING':>15}{prec:>10}  --")
        continue
    csvp = float(c[key]["bull_precision"]) * 100
    same = abs(csvp - float(prec)) < 0.005
    if not same:
        diffs.append((key, csvp, float(prec)))
    print(f"{str(key):<20}{csvp:>14.2f}%{prec:>9}%  {'OK' if same else 'DIFFERS'}")
print("-" * 62)
print(f"  {len(diffs)} of {len(rows)} rows differ between README and CSV")

print("\n=== is the LEAK still visible in the CSV? ===")
# The leaked rows are the in_sample=False rows whose precision came from a 2024
# block thresholded on 2024's own quantile. The README's corrected figure for
# V03/webpro is 2.865%.
for key in (("V03", "webpro"), ("V06", "webpro"), ("V03", "low60")):
    if key in c:
        r = c[key]
        print(f"  {key}: CSV says {float(r['bull_precision'])*100:.3f}%  "
              f"in_sample={r['in_sample']}  signals={int(r['signals_deduped']):,}")
print()
print("  README's corrected equal-footing figures are 2.87% (V03/webpro),")
print("  3.55%/3.72% (V07/V08), and the panel base rate is 3.089%.")
print("  A CSV value near 4.37% for V03/webpro is the LEAKED figure.")

json.dump({"rows_parsed": len(rows), "diffs": [(k, a, b) for k, a, b in diffs]},
          io.open("scripts/scratch/_lowzone_readme_vs_csv.json", "w",
                  encoding="utf-8"), indent=2)
print("\nwrote scripts/scratch/_lowzone_readme_vs_csv.json")
