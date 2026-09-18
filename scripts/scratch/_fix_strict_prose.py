"""Correct the remaining false direction/coverage claims in the strict_* family.

The first pass fixed single-line `THESIS = "A higher cutoff..."` lines. What is
left, all on variants whose THRESHOLD is BELOW their base's (so they emit a
SUPERSET, not a subset):

  * 9 module docstrings say "high-precision"; measured against their own base on
    the published evaluation, every one of them has LOWER precision, by -0.66 to
    -9.01 percentage points (strict_oversold_rebound_v2 is the extreme: 102x the
    signals at 2.93% against the base's 11.94% and the panel's 3.035% base rate).
  * 2 say "High-precision, lower-coverage", and their THESIS lines (which are
    parenthesised multi-line, so the first pass skipped them) say "Require a
    strong ... score" / "Select only the upper ... scores ... deliberately lower
    coverage". All false: 6.97x and 2.45x the coverage.

Only prose is touched. THRESHOLD values are fitted outputs of the 100-card
development scan and are NOT moved to match a sentence -- the sentence was written
to fit, and it did not.
"""
from __future__ import annotations

import importlib
import pathlib
import re

import pandas as pd

STRAT = pathlib.Path("experts/strategies")
W = {r["strategy_id"]: r for r in pd.read_csv("reports/webpro_hit_rates.csv")
     .to_dict("records")}


def t_of(n):
    return getattr(importlib.import_module(f"experts.strategies.{n}"), "THRESHOLD", None)


def base_of(name):
    mod = importlib.import_module(f"experts.strategies.{name}")
    wp = getattr(mod, "_base_predict", None)
    for p in STRAT.glob("*.py"):
        if p.stem == name:
            continue
        try:
            c = importlib.import_module(f"experts.strategies.{p.stem}")
        except Exception:
            continue
        if wp is not None and getattr(c, "predict", None) is wp:
            return p.stem
    return None


changed = []
for p in sorted(STRAT.glob("strict_*.py")):
    name = p.stem
    src = p.read_text(encoding="utf-8")
    original = src
    base = base_of(name)
    st, bt = t_of(name), (t_of(base) if base else None)
    if not (isinstance(st, float) and isinstance(bt, float)) or st >= bt:
        continue  # only LOOSER variants are misdescribed

    # measured facts for the honest sentence
    n_ratio = dP = None
    if base in W and name in W:
        bs = int(W[base]["signals_deduped__webpro"])
        ss = int(W[name]["signals_deduped__webpro"])
        if bs:
            n_ratio = ss / bs
        dP = (float(W[name]["bull_precision_deduped__webpro"])
              - float(W[base]["bull_precision_deduped__webpro"])) * 100
    if n_ratio is None:
        fact = (f"THRESHOLD sits below {base}'s, so it emits a superset")
    else:
        fact = (f"emits {n_ratio:.2f}x {base}'s signals at "
                f"{dP:+.2f}pp precision")

    # --- 1. module docstring -------------------------------------------
    doc = re.match(r'^"""(.*?)"""\n', src, re.S)
    if doc and re.search(r"high-precision|lower-coverage|lower coverage",
                         doc.group(1), re.I):
        new_doc = (f'"""Fixed-cutoff {base} variant, fitted on the 100-card '
                   f'development scan, not a stricter selector: {fact}."""\n')
        src = new_doc + src[doc.end():]

    # --- 2. THESIS: single-line and parenthesised multi-line ------------
    m = re.match(r'^THESIS = (\()?\s*\n?(.*?)\n?\)?\n(?=[A-Z_]+ =|def |\n)',
                 src, re.S | re.M)
    # Simpler and safer: match either form explicitly.
    single = re.search(r'^THESIS = "([^"]*)"$', src, re.M)
    multi = re.search(r'^THESIS = \(\n(.*?)\n\)$', src, re.M | re.S)
    honest = (f'THESIS = (\n'
              f'    "A fixed cutoff fitted on the 100-card development scan, not a '
              f'stricter selector: it "\n'
              f'    "sits BELOW the threshold of the base strategy {base}, so it '
              f'emits a SUPERSET "\n'
              f'    "of that strategy rather than a subset."\n'
              f')')
    claims = ("higher", "stronger", "stricter", "only the upper", "strong ",
              "deliberately lower coverage", "small deliberate coverage",
              "trades recall", "high-precision")
    if multi:
        body = multi.group(1).lower()
        if any(c in body for c in claims):
            src = src[:multi.start()] + honest + src[multi.end():]
    elif single:
        body = single.group(1).lower()
        if any(c in body for c in claims):
            src = src[:single.start()] + honest + src[single.end():]

    if src != original:
        p.write_text(src, encoding="utf-8")
        changed.append((name, base, n_ratio, dP))

print(f"=== corrected {len(changed)} module(s) ===\n")
for name, base, ratio, dP in changed:
    r = f"{ratio:.2f}x" if ratio is not None else "n/a"
    d = f"{dP:+.2f}pp" if dP is not None else "n/a"
    print(f"  {name:<34} base={base:<24} {r:>9}  {d:>8}")

print("\n=== residual claim scan across the family ===")
BAD = ("high-precision", "lower-coverage", "lower coverage", "higher cutoff",
       "only the upper", "small deliberate coverage")
still = []
for p in sorted(STRAT.glob("strict_*.py")):
    name = p.stem
    base = base_of(name)
    st, bt = t_of(name), (t_of(base) if base else None)
    if not (isinstance(st, float) and isinstance(bt, float)) or st >= bt:
        continue
    src = p.read_text(encoding="utf-8")
    for i, ln in enumerate(src.splitlines(), 1):
        low = ln.lower()
        if any(b in low for b in BAD):
            still.append((name, i, ln.strip()[:88]))
if still:
    for name, i, ln in still:
        print(f"  STILL CLAIMS {name}:{i}  {ln}")
else:
    print("  no LOOSER module still makes a direction/coverage claim it fails")
