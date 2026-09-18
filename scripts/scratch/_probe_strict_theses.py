"""The exact contract of the strict_* family, read from source."""
from __future__ import annotations

import importlib
import pathlib
import re

STRAT = pathlib.Path("experts/strategies")

sel = STRAT / "_strict_selector.py"
print("=== experts/strategies/_strict_selector.py ===")
if sel.exists():
    print("\n".join("  " + l for l in sel.read_text(encoding="utf-8").splitlines()))
else:
    print("  NOT AT THAT PATH; searching...")
    for p in STRAT.glob("*strict*"):
        print("   ", p)

print("\n\n=== every strict_* module's THESIS / FORMULA / THRESHOLD ===")
for p in sorted(STRAT.glob("strict_*.py")):
    mod = importlib.import_module(f"experts.strategies.{p.stem}")
    t = getattr(mod, "THRESHOLD", None)
    th = str(getattr(mod, "THESIS", ""))
    fo = str(getattr(mod, "FORMULA", ""))
    claims_higher = bool(re.search(r"higher|stricter|tight", th + " " + fo, re.I))
    print(f"\n  {p.stem}   T={t}")
    print(f"    THESIS : {th[:150]}")
    print(f"    FORMULA: {fo[:130]}")
    print(f"    claims a HIGHER/tighter cutoff: {claims_higher}")

print("\n\n=== do any tests pin a strict_* threshold or the family relation? ===")
hits = []
for f in list(pathlib.Path("tests").rglob("*.py")) + \
        [pathlib.Path("scripts/audit_reports.py")]:
    if not f.exists():
        continue
    txt = f.read_text(encoding="utf-8")
    for i, ln in enumerate(txt.splitlines(), 1):
        if "strict_" in ln and ("THRESHOLD" in ln or "BASE_STRATEGY" in ln):
            hits.append((str(f), i, ln.strip()))
print(f"  {len(hits)} reference(s):")
for f, i, ln in hits:
    print(f"    {f}:{i}  {ln[:90]}")
if not hits:
    print("    (none -- nothing pins the relation)")
