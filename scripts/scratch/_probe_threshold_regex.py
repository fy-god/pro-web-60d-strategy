"""Why does the audit's direction counter resolve only 7 of 16 modules?

The check uses
    ^THRESHOLD\\s*[:=][^=]*?([\\d.]+)
which cannot cross the `=` in `THRESHOLD: float = 0.90`, so annotated modules are
skipped. A skipped module is one the "no false claim" check never examines, which
is the fail-open pattern this whole review keeps finding -- in the new guard
itself. This measures the correct resolution and compares.
"""
from __future__ import annotations

import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
BAD = re.compile(r"^THRESHOLD\s*[:=][^=]*?([\d.]+)", re.M)
GOOD = re.compile(r"^THRESHOLD\s*(?::[^=\n]*)?=\s*([\d.]+)", re.M)

n_bad = n_good = 0
print(f"{'module':<34}{'annotated':>10}  {'bad regex':>10}{'good regex':>12}")
print("-" * 70)
for p in sorted(STRAT.glob("strict_*.py")):
    src = p.read_text(encoding="utf-8")
    ann = bool(re.search(r"^THRESHOLD\s*:", src, re.M))
    a = BAD.search(src)
    b = GOOD.search(src)
    if a:
        n_bad += 1
    if b:
        n_good += 1
    print(f"{p.stem:<34}{str(ann):>10}  "
          f"{(a.group(1) if a else '--'):>10}{(b.group(1) if b else '--'):>12}")
print("-" * 70)
print(f"  bad  regex resolves {n_bad}/16")
print(f"  good regex resolves {n_good}/16")

# And confirm both agree on the value where both match.
diff = []
for p in sorted(STRAT.glob("strict_*.py")):
    src = p.read_text(encoding="utf-8")
    a, b = BAD.search(src), GOOD.search(src)
    if a and b and a.group(1) != b.group(1):
        diff.append((p.stem, a.group(1), b.group(1)))
print(f"  value disagreements where both match: {len(diff)} {diff}")

# The direction census under the correct regex.
looser = tighter = equal = 0
for p in sorted(STRAT.glob("strict_*.py")):
    src = p.read_text(encoding="utf-8")
    bm = re.search(r'^BASE_STRATEGY_ID\s*=\s*"([a-z0-9_]+)"', src, re.M)
    if not bm:
        continue
    bs = (STRAT / f"{bm.group(1)}.py").read_text(encoding="utf-8")
    a, b = GOOD.search(src), GOOD.search(bs)
    if not (a and b):
        continue
    st, bt = float(a.group(1)), float(b.group(1))
    if st < bt:
        looser += 1
    elif st > bt:
        tighter += 1
    else:
        equal += 1
print(f"\n  correct census: looser={looser} tighter={tighter} equal={equal} "
      f"(sum {looser + tighter + equal})")
