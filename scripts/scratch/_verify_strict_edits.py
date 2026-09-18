"""Verify the strict_* edits: every module imports, exports BASE_STRATEGY_ID, and
its THESIS no longer contradicts its measured direction."""
from __future__ import annotations

import importlib
import pathlib
import sys

STRAT = pathlib.Path("experts/strategies")
ok = True
for p in sorted(STRAT.glob("strict_*.py")):
    name = p.stem
    try:
        mod = importlib.import_module(f"experts.strategies.{name}")
    except Exception as exc:
        print(f"  IMPORT FAIL {name}: {type(exc).__name__}: {exc}")
        ok = False
        continue
    bid = getattr(mod, "BASE_STRATEGY_ID", None)
    th = str(getattr(mod, "THESIS", ""))
    t = getattr(mod, "THRESHOLD", None)
    fn = getattr(mod, "predict", None)
    # __all__ must stay consistent with what the module defines.
    exported = getattr(mod, "__all__", [])
    missing = [n for n in exported if not hasattr(mod, n)]
    if bid is None:
        print(f"  NO BASE_STRATEGY_ID: {name}")
        ok = False
    if t is None or fn is None:
        print(f"  MISSING THRESHOLD/predict: {name}")
        ok = False
    if missing:
        print(f"  __all__ names not defined: {name}: {missing}")
        ok = False
    # Five of the sixteen modules (the non-`_v2` ones) never had an __all__ at
    # all -- pre-existing, checked against git -- so requiring the name there is
    # wrong. Where an __all__ exists, it must list it.
    if exported and "BASE_STRATEGY_ID" not in exported:
        print(f"  BASE_STRATEGY_ID not in __all__: {name}")
        ok = False

print(f"\nall 16 import cleanly with BASE_STRATEGY_ID: {ok}")

# The registry must still load and report 36 strategies.
sys.path.insert(0, ".")
try:
    from experts.registry import all_strategies, list_strategy_ids  # noqa
    ids = list_strategy_ids()
    print(f"registry strategies: {len(ids)}")
    if len(ids) != 36:
        print(f"  !! expected 36, got {len(ids)}")
        ok = False
    strict_ids = [i for i in ids if i.startswith("strict_")]
    print(f"strict_* in registry: {len(strict_ids)}")
except Exception as exc:
    print(f"registry import: {type(exc).__name__}: {exc}")
    ok = False

# The corrected THESIS must contain the honest phrase wherever it is LOOSER.
bad = []
for p in sorted(STRAT.glob("strict_*.py")):
    name = p.stem
    mod = importlib.import_module(f"experts.strategies.{name}")
    th = str(getattr(mod, "THESIS", ""))
    doc = (mod.__doc__ or "")
    bid = getattr(mod, "BASE_STRATEGY_ID", None)
    bt = getattr(importlib.import_module(f"experts.strategies.{bid}"), "THRESHOLD", None) if bid else None
    st = getattr(mod, "THRESHOLD", None)
    if isinstance(st, float) and isinstance(bt, float) and st < bt:
        if "SUPERSET" not in th and "superset" not in th:
            bad.append((name, "THESIS"))
        if "not a stricter selector" not in doc and "not a stricter selector" not in th:
            bad.append((name, "docstring"))
print(f"LOOSER modules whose prose is still false: {len(bad)}")
for x in bad:
    print("   ", x)
print("\nRESULT:", "OK" if ok and not bad else "PROBLEMS")
