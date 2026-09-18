"""Verify the strict_* family's threshold direction against its declared base.

The experts/ audit reported that 10 of the 16 `strict_*` variants use a LOWER
threshold than the strategy they claim to be a stricter version of, so the
"stricter" selector admits a strict superset. `_strict_selector`'s docstring claims
a "stricter binary cutoff" and every THESIS claims a higher one.

It also reported `BASE_STRATEGY_ID` is declared in 5 modules and read nowhere, so
the only machine-readable statement of the link is inert.

This measures both from source: it imports the registry, reads each strict module's
THRESHOLD, resolves its base (from BASE_STRATEGY_ID where present, else from the
module's own import of `predict as _base_predict`), and compares.
"""
from __future__ import annotations

import importlib
import pathlib
import re

STRAT = pathlib.Path("experts/strategies")
STRICT = sorted(p.stem for p in STRAT.glob("strict_*.py"))

print(f"=== {len(STRICT)} strict_* modules ===\n")
print(f"{'variant':<38}{'its T':>10}{'base':>26}{'base T':>9}{'dir':>7}")
print("-" * 92)

rows = []
for name in STRICT:
    mod = importlib.import_module(f"experts.strategies.{name}")
    t = getattr(mod, "THRESHOLD", None)
    src = (STRAT / f"{name}.py").read_text(encoding="utf-8")

    # Declared link, if any.
    declared = getattr(mod, "BASE_STRATEGY_ID", None)
    # Actual link: the base imported for its score. The import may span lines
    # (`from experts.strategies.oversold_rebound import (\n    FACTOR_DEFINITIONS
    # ...,\n    predict as _base_predict,\n)`), so search the whole module text for
    # the source module that supplies `_base_predict` rather than one line.
    # Resolve the base by OBJECT IDENTITY rather than by parsing the import.
    # A regex over `from X import (... predict as _base_predict)` is fragile: the
    # parenthesised form spans lines, the `_v2` modules import `FACTOR_DEFINITIONS`
    # alongside `predict`, and a first attempt silently resolved every `_v2` to
    # `__future__`. Comparing the function object itself cannot be fooled.
    imported = None
    wp = getattr(mod, "_base_predict", None)
    if wp is not None:
        for cand in STRAT.glob("*.py"):
            if cand.stem == name:
                continue
            try:
                cmod = importlib.import_module(f"experts.strategies.{cand.stem}")
            except Exception:
                continue
            if getattr(cmod, "predict", None) is wp:
                imported = cand.stem
                break

    base_id = declared or imported
    base_t = None
    if base_id:
        try:
            bmod = importlib.import_module(f"experts.strategies.{base_id}")
            base_t = getattr(bmod, "THRESHOLD", None)
        except Exception as exc:
            base_t = f"<{type(exc).__name__}>"

    if isinstance(t, float) and isinstance(base_t, float):
        direction = "LOOSER" if t < base_t else ("tighter" if t > base_t else "equal")
    else:
        direction = "?"
    rows.append({"variant": name, "T": t, "declared": declared,
                 "imported": imported, "base": base_id, "base_T": base_t,
                 "direction": direction})
    print(f"{name:<38}{t if t is None else f'{t:.6f}':>10}"
          f"{str(base_id):>26}{'' if base_t is None else (f'{base_t:.6f}' if isinstance(base_t, float) else str(base_t)):>9}"
          f"{direction:>7}")

print("-" * 92)
looser = [r for r in rows if r["direction"] == "LOOSER"]
tighter = [r for r in rows if r["direction"] == "tighter"]
print(f"\n  LOOSER than base : {len(looser)}  {[r['variant'] for r in looser]}")
print(f"  tighter than base: {len(tighter)}  {[r['variant'] for r in tighter]}")

print("\n=== is BASE_STRATEGY_ID read anywhere? ===")
hits = []
for p in pathlib.Path(".").rglob("*.py"):
    if ".venv" in str(p) or "site-packages" in str(p):
        continue
    try:
        txt = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if "BASE_STRATEGY_ID" in txt:
        for i, ln in enumerate(txt.splitlines(), 1):
            if "BASE_STRATEGY_ID" in ln:
                hits.append((str(p), i, ln.strip()))
print(f"  {len(hits)} references in total:")
for path, i, ln in hits:
    kind = "DECLARES" if ": str =" in ln or ": str=" in ln else "reads/other"
    print(f"    {kind:<12} {path}:{i}  {ln[:80]}")
declares = [h for h in hits if "str =" in h[2]]
reads = [h for h in hits if "import" in h[2] or "getattr" in h[2]]
print(f"\n  declared: {len(declares)}   imported/read elsewhere: {len(reads)}")
print("  -> inert" if not reads else "  -> used")

print("\n=== the guard that would have caught this ===")
importable = [r for r in rows if isinstance(r["T"], float) and isinstance(r["base_T"], float)]
bad = [r for r in importable if r["T"] < r["base_T"]]
print(f"  assert variant.THRESHOLD >= base.THRESHOLD  would fail on "
      f"{len(bad)} of {len(importable)} resolvable pairs")

import json, io
io.open("scripts/scratch/_strict_direction.json", "w", encoding="utf-8").write(
    json.dumps(rows, indent=2, default=str))
print("\nwrote scripts/scratch/_strict_direction.json")
print("\nRESULT:", "INVERSION CONFIRMED" if looser else "no inversion found")
