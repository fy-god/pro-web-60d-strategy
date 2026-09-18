"""Audit every false direction/coverage claim in the strict_* family.

The first pass corrected single-line `THESIS = "A higher cutoff..."` lines. Two
modules use a parenthesised multi-line THESIS with different wording, and several
module docstrings claim "High-precision, lower-coverage". Measured against each
base on the published evaluation, a lower threshold means MORE signals and (for
every such variant) LOWER precision, so both phrases are false for those modules.

This lists, per module: the resolved base, the threshold direction, the measured
signal ratio and precision delta, and every prose line that makes a claim.
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


CLAIM_WORDS = ("higher", "stricter", "stronger", "strong ", "upper", "only the",
               "lower-coverage", "lower coverage", "high-precision",
               "small deliberate coverage", "trades recall")

print(f"{'module':<34}{'dir':>8}{'sig ratio':>11}{'dP(pp)':>9}  claims in prose")
print("-" * 118)
for p in sorted(STRAT.glob("strict_*.py")):
    name = p.stem
    src = p.read_text(encoding="utf-8")
    base = base_of(name)
    st, bt = t_of(name), (t_of(base) if base else None)
    d = "?"
    ratio = dP = float("nan")
    if isinstance(st, float) and isinstance(bt, float):
        d = "LOOSER" if st < bt else ("tighter" if st > bt else "equal")
    if base in W and name in W:
        bs = int(W[base]["signals_deduped__webpro"])
        ss = int(W[name]["signals_deduped__webpro"])
        ratio = ss / bs if bs else float("inf")
        dP = (float(W[name]["bull_precision_deduped__webpro"])
              - float(W[base]["bull_precision_deduped__webpro"])) * 100
    # Every prose line making a direction/coverage claim.
    prose = []
    for i, ln in enumerate(src.splitlines(), 1):
        low = ln.lower()
        if any(w in low for w in CLAIM_WORDS) and not ln.lstrip().startswith(("#", "from", "import")):
            prose.append((i, ln.strip()))
    print(f"{name:<34}{d:>8}"
          f"{(f'{ratio:.2f}x' if ratio == ratio else '--'):>11}"
          f"{(f'{dP:+.2f}' if dP == dP else '--'):>9}  {len(prose)} line(s)")
    for i, ln in prose:
        print(f"      L{i}: {ln[:100]}")

print("\n=== the universally false phrases on LOOSER variants ===")
bad = [("High-precision, lower-coverage", "docstring"),
       ("high-precision selector with deliberately lower coverage", "THESIS"),
       ("small deliberate coverage", "THESIS"),
       ("Select only the upper", "THESIS"),
       ("Require a strong", "THESIS")]
for phrase, where in bad:
    hits = []
    for p in sorted(STRAT.glob("strict_*.py")):
        name = p.stem
        if phrase.lower() not in p.read_text(encoding="utf-8").lower():
            continue
        base = base_of(name)
        st, bt = t_of(name), (t_of(base) if base else None)
        if isinstance(st, float) and isinstance(bt, float) and st < bt:
            hits.append(name)
    print(f"  {phrase!r:<58} on {len(hits)} LOOSER module(s): {hits}")
