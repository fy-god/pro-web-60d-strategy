"""Reproduce the PUBLISHED 12.14% holdout with HEAD code + HEAD-built matrix.

The published reports were produced by the committed code reading the committed
stride-5 matrix (`iloc[::5]`, 536,143 rows, base_rate_high 0.030916). The
worktree matrix at that path has since been rebound to the NEW session-grid
rule. This runner therefore points the HEAD `final_holdout` at the HEAD-rule
matrix rebuilt into scripts/scratch/_artifacts and checks that the published
numbers come back exactly.
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

from src.ml import walkforward as wf  # noqa: E402

ART = HERE / "_artifacts"
_orig_load = wf.load_matrix


def patched_load_matrix(horizon: int = 10, target: int = 30, stride: int = 5):
    path = ART / f"matrix_h{horizon}_t{target}_s{stride}.parquet"
    import pandas as pd

    return pd.read_parquet(path)


wf.load_matrix = patched_load_matrix

spec = importlib.util.spec_from_file_location(
    "_head_final_holdout", HERE / "_head_final_holdout.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.REPORT_DIR = ART / "reports_head"
mod.main()
