"""Make the strict_* family's base link machine-readable and its prose true.

Two defects, one fix:

  1. Only 5 of the 16 `strict_*` modules declare BASE_STRATEGY_ID, so nothing can
     check a strict variant against the strategy it claims to tighten. The base is
     resolvable at runtime (the module imports it as `_base_predict`) and that is
     how the relation was verified, but a runtime import is not a declaration.

  2. Twelve modules say "A higher cutoff keeps only ..." in THESIS. Measured
     against their own base's THRESHOLD, 7 of those 12 use a LOWER cutoff, and all
     9 lower-cutoff variants emit MORE signals than their base -- no exceptions --
     up to 102x for strict_oversold_rebound_v2. The sentence is false, and THESIS
     is read by nothing, so it was never wrong in a way the audit could see.

This adds BASE_STRATEGY_ID to every strict_* module and rewrites only the THESIS
lines whose direction claim is false. THRESHOLD values are NOT touched: they are
fitted outputs of the 100-card development scan, and moving a fitted number to
match a sentence would be the wrong repair. The sentence is what is wrong.

THESIS is read by no code (verified: the only occurrence of the word outside these
modules is a comment in scripts/audit_reports.py), so this is a text-only change.
"""
from __future__ import annotations

import importlib
import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
STRICT = sorted(p for p in STRAT.glob("strict_*.py"))


def resolve_base(name: str) -> str | None:
    """The module whose `predict` this variant reuses, by function identity."""
    mod = importlib.import_module(f"experts.strategies.{name}")
    wp = getattr(mod, "_base_predict", None)
    if wp is None:
        return None
    for cand in STRAT.glob("*.py"):
        if cand.stem == name:
            continue
        try:
            cmod = importlib.import_module(f"experts.strategies.{cand.stem}")
        except Exception:
            continue
        if getattr(cmod, "predict", None) is wp:
            return cand.stem
    return None


def threshold_of(name: str) -> float | None:
    return getattr(importlib.import_module(f"experts.strategies.{name}"),
                   "THRESHOLD", None)


report = []
for p in STRICT:
    name = p.stem
    src = p.read_text(encoding="utf-8")
    original = src
    notes = []

    base = resolve_base(name)
    if base is None:
        notes.append("NO BASE RESOLVED")
        report.append((name, base, None, None, notes, False))
        continue
    bt, st = threshold_of(base), threshold_of(name)
    direction = None
    if isinstance(bt, float) and isinstance(st, float):
        direction = "LOOSER" if st < bt else ("tighter" if st > bt else "equal")

    # --- 1. ensure BASE_STRATEGY_ID is declared -------------------------
    if "BASE_STRATEGY_ID" not in src:
        # Put it immediately after THRESHOLD, which every module has.
        anchor = re.search(r"^(THRESHOLD[^\n]*\n)", src, re.M)
        if anchor is None:
            notes.append("NO THRESHOLD ANCHOR")
            report.append((name, base, st, bt, notes, False))
            continue
        ins = f'BASE_STRATEGY_ID = "{base}"\n'
        src = src[:anchor.end()] + ins + src[anchor.end():]
        notes.append("declared BASE_STRATEGY_ID")
        # Export it too, if the module has an __all__.
        src = re.sub(r'(__all__ = \[\n)(\s*)("THRESHOLD",\n)',
                     r'\1\2"BASE_STRATEGY_ID",\n\2\3', src)

    # --- 2. correct a false direction claim ------------------------------
    if direction == "LOOSER":
        m = re.search(r'^THESIS = "A higher cutoff keeps only ([^"]*)"$',
                      src, re.M)
        if m:
            rest = m.group(1).rstrip(". ")
            new = (f'THESIS = "A cutoff fitted on the 100-card development scan, '
                   f'not a stricter one: THRESHOLD sits BELOW that of the base '
                   f'strategy {base}, so this selector emits a SUPERSET of it, '
                   f'not a subset of {rest}."')
            src = src[:m.start()] + new + src[m.end():]
            notes.append("corrected false 'higher cutoff' claim")
        else:
            # Different phrasing; flag for manual handling rather than guess.
            claims = re.search(r'^(THESIS = ".*?(?:higher|stronger|stricter).*?")$',
                               src, re.M | re.I)
            if claims:
                notes.append("CLAIM PHRASING NOT AUTO-CORRECTED")
    elif direction == "tighter":
        # The claim is true; leave the prose alone, but the newly declared
        # BASE_STRATEGY_ID makes it checkable.
        pass

    if src != original:
        p.write_text(src, encoding="utf-8")
    report.append((name, base, st, bt, notes, src != original))

print(f"{'variant':<34}{'base':<26}{'T':>9}{'baseT':>9}{'dir':>7}  action")
print("-" * 116)
for name, base, st, bt, notes, changed in report:
    d = "-"
    if isinstance(st, float) and isinstance(bt, float):
        d = "LOOSER" if st < bt else ("tighter" if st > bt else "equal")
    print(f"{name:<34}{str(base):<26}"
          f"{st if st is None else f'{st:.6f}':>9}"
          f"{bt if bt is None else f'{bt:.6f}':>9}{d:>7}  "
          f"{'; '.join(notes) if notes else 'unchanged'}")

looser = [r for r in report if isinstance(r[2], float) and isinstance(r[3], float)
          and r[2] < r[3]]
print("-" * 116)
print(f"  {sum(1 for r in report if r[5])} module(s) modified")
print(f"  {len(looser)} LOOSER than base")
print(f"  {sum(1 for r in report if not r[1])} with no resolvable base")
declared = sum(1 for p in STRICT
               if "BASE_STRATEGY_ID" in p.read_text(encoding="utf-8"))
print(f"  BASE_STRATEGY_ID now declared in {declared}/{len(STRICT)} strict_* modules")
