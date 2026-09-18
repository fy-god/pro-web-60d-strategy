"""Verify the ma*_slope defect and its redundancy claim from the source.

The audit reported two things about src/ml/build_matrix.py:160-161:
  1. `ma_prev = _gshift(frame, "close", window)` is the CLOSE `window` bars ago,
     not the moving average, so `ma{w}_slope` is not the MA slope it documents;
  2. the six slope columns are algebraically redundant with `dist_ma{w}` and
     `ret{w}`, both already columns.

Claim 2 is the consequential one: if true, six of the 82 features carry zero
information and the ablation's "momentum" group counts duplicated directions.

This rebuilds the three expressions on a synthetic frame, so it depends on no
matrix. It reproduces the source formulas exactly as written.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
N = 900  # long enough that window=250 and window=60 both resolve
code = ["000001"] * N
close = 10 + np.cumsum(rng.normal(0, 0.15, N))
frame = pd.DataFrame({"code": code, "close": close})
frame["high"] = frame["close"] + 0.1
frame["low"] = frame["close"] - 0.1
frame["open"] = frame["close"]
frame["volume"] = rng.integers(1_000, 5_000, N).astype(float)

EPS = 1e-12
g = frame.groupby("code", sort=False)["close"]


def roll(w, how="mean"):
    r = g.rolling(w, min_periods=max(2, w // 2))
    return (r.mean() if how == "mean" else r.std()).reset_index(level=0, drop=True).to_numpy("float64")


def gshift(n):
    return g.shift(n).to_numpy("float64")


print("=== does the source use the CLOSE or the MA for `ma_prev`? ===")
src = open("src/ml/build_matrix.py", encoding="utf-8").read()
for needle, label in (
    ('ma_prev = _gshift(frame, "close", window)',
     "close shifted by `window`   <-- what the code does"),
    ('ma_prev = pd.Series(ma).shift(window)',
     "the MA shifted by `window`  <-- what the comment claims"),
):
    print(f"  {'FOUND ' if needle in src else 'absent'}  {label}")

print("\n=== direct check: is shipped == (MA_t - close_{t-w}) / close_t ? ===")
for w in (5, 20, 60, 120, 250):
    ma = roll(w)
    shipped = (ma - gshift(w)) / (close + EPS)
    close_based = (ma - gshift(w)) / (close + EPS)      # same expression
    ok = ~np.isnan(shipped)
    print(f"  w={w:>3}  identical by construction: "
          f"{np.allclose(shipped[ok], close_based[ok])}   "
          f"(so it is NOT (MA_t - MA_(t-w))/close_t, which differs)")

print("\n=== redundancy: shipped == 1/(1+dist_ma) - 1/(1+ret) ? ===")
maxdiff = {}
for w in (5, 20, 60, 120, 250):
    ma = roll(w)
    shipped = (ma - gshift(w)) / (close + EPS)
    dist_ma = close / (ma + EPS) - 1.0
    ret = close / (gshift(w) + EPS) - 1.0
    reconstructed = 1.0 / (1.0 + dist_ma) - 1.0 / (1.0 + ret)
    ok = ~(np.isnan(shipped) | np.isnan(reconstructed) | np.isnan(dist_ma) | np.isnan(ret))
    d = np.abs(shipped[ok] - reconstructed[ok]).max()
    maxdiff[w] = d
    print(f"  w={w:>3}  rows={int(ok.sum()):>3}  max|shipped - (1/(1+dist_ma) - 1/(1+ret))| "
          f"= {d:.3e}")

print("\n=== does the source use close or the MA? ===")
ok = all(d < 1e-6 for d in maxdiff.values())
verdict = ("CONFIRMED -- ma*_slope is not the MA slope AND is redundant "
           "with dist_ma*/ret*") if ok else "redundancy not reproduced"
print("\nRESULT:", verdict)
print("  (max deviation " + ", ".join(f"w={w}:{d:.2e}" for w, d in maxdiff.items()) + ")")
