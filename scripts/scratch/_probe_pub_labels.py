"""Check TARGET_70PCT.md section 4's publication-rate labels against target_rate.

Each row of that table names a publication rate ("2% publication", "5%
publication") and gives an out-of-sample signal count. The report rows carry
`target_rate`, which is the publication budget the label names. This matches by
signal count (unique across the 56 ranked rows) and prints the label the document
uses beside the rate the report records.
"""
from __future__ import annotations

import io
import json
import re

doc = io.open("TARGET_70PCT.md", encoding="utf-8").read().splitlines()
report = json.load(io.open("reports/ml_search_wide.json", encoding="utf-8"))
rows = report["ranked"]
by_sig = {r["oos_signals"]: r for r in rows}

# The section 4 table: | <name> | <insample>% | **<oos>%** | <signals> | <folds> |
print("TARGET_70PCT.md section 4 table, lines 166-173:")
print(f"{'line':>4}  {'document label':<34} {'OOS':>7} {'sig':>6}  "
      f"{'target_rate':>11}  implied")
bad = []
for i, line in enumerate(doc, 1):
    if not (160 <= i <= 178):
        continue
    if line.count("|") < 5:
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 5:
        continue
    m = re.search(r"([\d.]+)%\s*publication", cells[0])
    if not m:
        continue
    sig_m = re.match(r"^([\d,]+)$", cells[3])
    if not sig_m:
        continue
    sig = int(sig_m.group(1).replace(",", ""))
    r = by_sig.get(sig)
    tr = r.get("target_rate") if r else None
    implied = f"{tr*100:g}% publication" if tr is not None else "?"
    flag = ""
    if tr is not None and abs(float(m.group(1)) / 100 - tr) > 1e-9:
        flag = "  <-- MISMATCH"
        bad.append((i, cells[0], m.group(1), sig, tr))
    print(f"{i:>4}  {cells[0]:<34} {cells[2]:>7} {sig:>6}  "
          f"{tr if tr is not None else '?':>11}  {implied}{flag}")

print()
if bad:
    print(f"{len(bad)} MISMATCH(es) -- only the rate label is wrong if the "
          f"numbers match:")
    for i, label, doc_rate, sig, tr in bad:
        print(f"  line {i}: label says {doc_rate}% publication, "
              f"target_rate is {tr} ({tr*100:g}%)")
else:
    print("All publication-rate labels agree with target_rate.")

# Confirm the numeric cells are right, so the defect is purely the label.
print("\nNumeric cells for the flagged rows:")
for i, label, doc_rate, sig, tr in bad:
    r = by_sig[sig]
    print(f"  line {i}: OOS {r['oos_precision']*100:.2f}%, signals {sig:,}, "
          f"folds {r['n_folds']}, config {r['config']}")
