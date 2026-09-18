"""Is removing the censoring mask a real behaviour change, or an equivalent mutant?

The reviewer reported that `test_right_censoring_not_negative` catches removing the
NaN mask at labels.py:199-200. My mutation probe replaced the loop with `pass` and
the suite still passed. Two possibilities:

  (a) the test is weaker than believed, or
  (b) the mask is a NO-OP because `forward_high`/`forward_low` are already NaN on
      unresolved rows, so removing it changes no observable value.

(b) is entirely plausible by construction: `forward_high` is initialised to NaN and
only overwritten via `np.where(valid, run_max, forward_high)`, so a row whose future
never became valid stays NaN -- and `bull = np.where(np.isfinite(forward_high), ...,
np.nan)` is then already NaN. If that is the case, the mask is defensive, not
load-bearing, and no test can or should catch its removal.

This settles it by comparing outputs directly, not by reading.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import sys

import numpy as np
import pandas as pd

SRC = pathlib.Path(r"D:\ccc\pro-web-60d-strategy")
WORK = pathlib.Path(r"D:\ccc\pro-web-60d-strategy\.audit_tmp\probe_mask")


def build(module_path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, module_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def frame(rows):
    df = pd.DataFrame(rows)
    df["code"] = df["code"].astype(str)
    df["date"] = pd.to_datetime(df["date"])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df


def flat(code, n, price=10.0):
    dates = pd.bdate_range("2024-01-01", periods=n)
    return [{"code": code, "date": d, "open": price, "high": price,
             "low": price, "close": price, "volume": 1000.0} for d in dates]


# Mutant: the censoring loop replaced with `pass`.
if WORK.exists():
    shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
mod_path = WORK / "labels_mutant.py"
src = (SRC / "src" / "labels.py").read_text(encoding="utf-8")
old = ("    for arr in (bull, strict_low, joint):\n"
       "        arr[~resolved] = np.nan")
assert src.count(old) == 1, f"anchor not unique: {src.count(old)}"
src_mut = src.replace(old, "    pass")
mod_path.write_text(src_mut, encoding="utf-8")

# Load both the real and the mutant module by path, so a relative import inside
# labels.py cannot pick up the wrong one. Both are executed with the repo on
# sys.path.
sys.path.insert(0, str(SRC))
real = build(SRC / "src" / "labels.py", "labels_real")
mut = build(mod_path, "labels_mutant")

print("=== do the two modules differ on any observable output? ===")
cases = {
    "flat 20 bars, horizon 60 (all rows censored)": (flat("000001", 20), 60, {}),
    "flat 40 bars, horizon 30 (last rows censored)": (flat("000001", 40), 30, {}),
    "40 bars with a spike at bar 5, horizon 30": (
        [dict(r) for r in flat("000001", 40)], 30, {"spike": 5}),
    "two stocks, 40 bars, horizon 30": (
        [dict(r) for r in flat("000001", 40)] + [dict(r) for r in flat("000002", 40)],
        30, {}),
}
diffs = 0
for label, (rows, horizon, opt) in cases.items():
    if opt.get("spike"):
        rows[opt["spike"]]["high"] = 13.0
    df = frame(rows)
    a = real.forward_outcomes(df.copy(), horizon=horizon)
    b = mut.forward_outcomes(df.copy(), horizon=horizon)
    differing = []
    for col in a.columns:
        sa, sb = a[col], b[col]
        same = ((sa.isna() & sb.isna())
                | (sa.fillna(-9e9) == sb.fillna(-9e9)))
        if not same.all():
            differing.append((col, int((~same).sum()),
                              sa[~same].head(2).tolist(),
                              sb[~same].head(2).tolist()))
    diffs += len(differing)
    print(f"  {label}")
    print(f"     differing columns: "
          f"{[d[0] for d in differing] if differing else 'NONE'}")
    for col, n, av, bv in differing[:3]:
        print(f"       {col}: {n} rows differ; real={av} mutant={bv}")

print()
if diffs == 0:
    print("VERDICT: EQUIVALENT MUTANT.")
    print("  The censoring loop changes NO observable value on these inputs, because")
    print("  forward_high/forward_low are already NaN wherever the window is")
    print("  unresolved, so `bull`/`strict_low`/`joint` are NaN before the mask runs.")
    print("  The mask is defensive belt-and-braces, not load-bearing, and no test can")
    print("  catch its removal. The reviewer's claim that a test catches it is wrong;")
    print("  the test suite is not at fault.")
else:
    print(f"VERDICT: REAL BEHAVIOUR CHANGE ({diffs} column(s) differ) -- the test")
    print("  suite IS missing coverage for this and should be strengthened.")

shutil.rmtree(WORK, ignore_errors=True)
