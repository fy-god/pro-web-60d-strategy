"""Which pairs does the audit's direction check silently skip, and why?

The check continues past any module whose own or base THRESHOLD it cannot parse.
A skipped module is one the "no false claim" assertion never examines -- the same
fail-open this review keeps finding, now inside the new guard. This replicates the
audit's exact regex and lists every skip.
"""
from __future__ import annotations

import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
AUDIT = re.compile(r"^THRESHOLD\s*[:=][^=]*?([\d.]+)", re.M)
FIXED = re.compile(r"^THRESHOLD\s*(?::[^=\n]*)?=\s*([\d.]+)", re.M)

skipped, resolved = [], []
for p in sorted(STRAT.glob("strict_*.py")):
    src = p.read_text(encoding="utf-8")
    bm = re.search(r'^BASE_STRATEGY_ID\s*=\s*"([a-z0-9_]+)"', src, re.M)
    if not bm:
        skipped.append((p.stem, "no BASE_STRATEGY_ID"))
        continue
    base = bm.group(1)
    bs = (STRAT / f"{base}.py").read_text(encoding="utf-8")
    a, b = AUDIT.search(src), AUDIT.search(bs)
    if not a or not b:
        which = []
        if not a:
            which.append("own")
        if not b:
            which.append(f"base({base})")
        skipped.append((p.stem, "+".join(which)))
        continue
    resolved.append((p.stem, base, float(a.group(1)), float(b.group(1))))

print(f"resolved by the audit's regex : {len(resolved)}/16")
for name, base, st, bt in resolved:
    d = "LOOSER" if st < bt else ("tighter" if st > bt else "equal")
    print(f"   {name:<34} {st:.4f} vs {base} {bt:.4f}  {d}")

print(f"\nSILENTLY SKIPPED             : {len(skipped)}/16")
for name, why in skipped:
    print(f"   {name:<34} skipped: {why}")

print("\n=== the base files that defeat the regex ===")
for p in sorted(STRAT.glob("*.py")):
    if p.stem.startswith("strict_"):
        continue
    src = p.read_text(encoding="utf-8")
    line = next((l for l in src.splitlines() if l.startswith("THRESHOLD")), None)
    if line is None:
        continue
    a, b = AUDIT.search(src), FIXED.search(src)
    if not a or not b:
        print(f"  {p.stem:<30} {line.strip():<34} "
              f"audit={'ok' if a else 'FAIL'}  fixed={'ok' if b else 'FAIL'}")

print("\n=== what the fixed regex yields ===")
n = {"looser": 0, "tighter": 0, "equal": 0}
for p in sorted(STRAT.glob("strict_*.py")):
    src = p.read_text(encoding="utf-8")
    bm = re.search(r'^BASE_STRATEGY_ID\s*=\s*"([a-z0-9_]+)"', src, re.M)
    if not bm:
        continue
    bs = (STRAT / f"{bm.group(1)}.py").read_text(encoding="utf-8")
    a, b = FIXED.search(src), FIXED.search(bs)
    if not (a and b):
        continue
    st, bt = float(a.group(1)), float(b.group(1))
    n["looser" if st < bt else ("tighter" if st > bt else "equal")] += 1
print(f"  {n}  sum={sum(n.values())}")
print("\n  => the audit reported looser=1 tighter=6 (7) and stayed GREEN because")
print("     the other 9 were never examined. That is a real fail-open.")
