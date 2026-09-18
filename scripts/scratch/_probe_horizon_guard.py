"""Verify concentration.main() refuses to run when HORIZON disagrees with the matrix.

The guard exists because HORIZON was declared as a constant AND written as a bare
literal in the wf.folds call, so the two could drift; a wrong horizon silently
produces a plausible precision on a leaky split. This probe stubs the matrix load
so the real dense matrix is never read (the machine is running another job), and
checks that the mismatch is fatal and the match is not.
"""
from __future__ import annotations

import sys
import types

sys.path.insert(0, ".")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.ml import concentration as conc  # noqa: E402
from src.ml import walkforward as wf  # noqa: E402

# A tiny frame with the columns main() touches before the guard.
sessions = pd.date_range("2023-01-03", periods=400, freq="B").date
frame = pd.DataFrame({
    "code": np.repeat(["600000", "000001"], len(sessions))[:len(sessions)],
    "date": sessions,
    "entry_open": 1.0,
    "label_high": 0.0,
    "label_close": 0.0,
    "resolved": True,
})
for c in sorted(wf.FEATURE_GROUPS):
    pass
# Give it one feature per group so feature_columns() is non-empty.
for g in wf.FEATURE_GROUPS:
    frame[f"f_{g}"] = 0.0

wf.load_matrix = lambda *a, **k: frame  # type: ignore[assignment]


class _Stop(Exception):
    pass


def run_with(horizon):
    wf.LAST_LOAD = {"path": "matrix_h10_t30_s1.parquet", "stride": 1,
                    "rows": 1, "sessions": 1, "horizon": horizon}
    # Stop right after the guard so no folding/model work happens.
    real_folds = wf.folds

    def boom(*a, **k):
        raise _Stop()

    wf.folds = boom
    try:
        conc.main()
        return "completed"
    except SystemExit as e:
        return f"SystemExit: {e}"
    except _Stop:
        return "passed the guard"
    finally:
        wf.folds = real_folds


print(f"concentration.HORIZON = {conc.HORIZON}")
ok = True

print("\nmatrix horizon 10 (agrees):")
r = run_with(10)
print("  ->", r)
if r != "passed the guard":
    print("  FAIL: the guard should not block a matching horizon")
    ok = False

print("\nmatrix horizon 20 (disagrees):")
r = run_with(20)
print("  ->", r)
if "HORIZON is 10" not in r or "horizon 20" not in r:
    print("  FAIL: the mismatch should be fatal and name both values")
    ok = False

print("\nRESULT:", "PASS -- the horizon guard works" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
