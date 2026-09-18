"""Is webpro_hit_rates.csv's `evaluated_points` column stale?

The experts audit reported it is. `evaluated_points` should be the number of grid
points the scan visited, which is a property of the POPULATION, not of a strategy
-- so every row should carry the same value (or the same per regime). If rows
disagree with each other or with the scan's recorded population, the column is
either stale or misnamed.

It is also suspicious that it is the one column nothing verified.
"""
from __future__ import annotations

import io
import json

import pandas as pd

w = pd.read_csv("reports/webpro_hit_rates.csv")
print(f"rows: {len(w)}")
print(f"evaluated_points unique values: {sorted(w['evaluated_points'].unique())}")
print(f"  n unique = {w['evaluated_points'].nunique()}")
print()
print("=== the first 8 rows ===")
print(w[["strategy_id", "evaluated_points", "signals_raw__webpro"]].head(8)
      .to_string(index=False))
print()
print("=== does evaluated_points correlate with signals_raw? ===")
r = w["evaluated_points"].corr(w["signals_raw__webpro"])
print(f"  pearson r = {r:.4f}")
print(f"  identical to signals_raw on "
      f"{int((w['evaluated_points'] == w['signals_raw__webpro']).sum())}/{len(w)} rows")

print("\n=== what population SHOULD it be? ===")
for name in ("webpro_baselines.json", "lowzone_baselines.json"):
    try:
        d = json.load(io.open(f"reports/{name}", encoding="utf-8"))
    except Exception as exc:
        print(f"  {name}: {type(exc).__name__}")
        continue
    print(f"  {name}:")
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                interesting = {kk: vv for kk, vv in v.items()
                               if any(s in kk.lower()
                                      for s in ("point", "rows", "n_", "population",
                                                "grid", "rate"))}
                print(f"    {k}: {interesting}")

print("\n=== what does the scan summary say the grid size is? ===")
try:
    s = json.load(io.open("reports/webpro_scan_summary.json", encoding="utf-8"))
    for k, v in s.items():
        if not isinstance(v, (dict, list)):
            print(f"    {k}: {v}")
except Exception as exc:
    print(f"    {type(exc).__name__}: {exc}")

print("\n=== is the column read anywhere? ===")
import pathlib
hits = []
for p in list(pathlib.Path("src").rglob("*.py")) + \
        list(pathlib.Path("scripts").rglob("*.py")) + \
        [pathlib.Path("README.md"), pathlib.Path("RESULTS.md")]:
    if not p.exists():
        continue
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception:
        continue
    for i, ln in enumerate(txt.splitlines(), 1):
        if "evaluated_points" in ln:
            hits.append((str(p), i, ln.strip()[:95]))
print(f"  {len(hits)} reference(s):")
for f, i, ln in hits:
    print(f"    {f}:{i}  {ln}")
