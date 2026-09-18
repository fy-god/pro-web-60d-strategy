"""Count how many turnover-consuming strategies read the LEVEL, from the code.

Two documents disagreed: README implies 1 level reader, src/features.py said 2.
A docstring edit is only correct if the count is measured, so this reads the five
strategy modules and classifies each by whether the turnover term is a raw level or
a ratio of two turnover aggregates. It also reads the test that claims to pin this.
"""
from __future__ import annotations

import io
import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
CONSUMERS = ["accumulation_base", "turnover_weak_to_strong", "turnover_regime_switch",
             "leader_momentum", "strict_turnover_weak_to_strong_v2"]

print("=== turnover usage per strategy ===")
level, ratio = [], []
for name in CONSUMERS:
    p = STRAT / f"{name}.py"
    if not p.exists():
        print(f"  {name:<38} MISSING")
        continue
    src = p.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in src.splitlines()
             if "turnover" in ln and not ln.strip().startswith("#")]
    # A ratio divides/multiplies two turnover aggregates; a level uses turnover
    # directly against a constant (e.g. /4.0) or bare.
    is_ratio = any(("/" in ln and ln.count("turnover") >= 2)
                   or "std" in ln or "cv" in ln.lower()
                   for ln in lines)
    # Explicit: leader_momentum reads turnover_mean(...)/4.0, a constant divisor.
    is_level = any(re.search(r"turnover[a-z_]*\([^)]*\)\s*/\s*[\d.]+", ln)
                   for ln in lines) and not is_ratio
    kind = "LEVEL" if is_level else ("ratio" if is_ratio else "?")
    (level if kind == "LEVEL" else ratio).append((name, kind))
    print(f"  {name:<38} {kind:<6}")
    for ln in lines[:3]:
        print(f"        {ln[:96]}")

print(f"\n  LEVEL readers : {len(level)}  {[n for n, _ in level]}")
print(f"  ratio readers : {len(ratio)}  {[n for n, _ in ratio]}")
print(f"  total         : {len(level) + len(ratio)} of {len(CONSUMERS)}")

print("\n=== what the test pins ===")
t = pathlib.Path("tests/test_engine.py").read_text(encoding="utf-8")
m = re.search(r"def (test_\w*(?:scale|invariant)\w*)\(.*?\n(.*?)(?=\ndef |\Z)",
              t, re.S)
if m:
    body = m.group(2)
    ids = re.findall(r'"([a-z_0-9]+)"', body)
    ids = [i for i in ids if i in CONSUMERS]
    print(f"  {m.group(1)} enumerates {len(ids)}: {ids}")
else:
    print("  no scale-invariance test found")

print("\n=== what README says ===")
rd = pathlib.Path("README.md").read_text(encoding="utf-8")
i = rd.find("turnover-consuming")
if i < 0:
    i = rd.find("turnover")
seg = rd[max(0, i - 200):i + 700]
for ln in seg.splitlines():
    if "turnover" in ln or "scale-invariant" in ln or "level" in ln:
        print(f"  {ln.strip()[:110]}")

print("\nRESULT:", "1 level reader -- features.py was wrong"
      if len(level) == 1 else f"{len(level)} level readers -- recheck")
