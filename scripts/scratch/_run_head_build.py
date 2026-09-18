"""Run the HEAD (committed) build_matrix.build() without touching tracked files.

Redirects OUT_DIR into scripts/scratch/_artifacts so the committed stride-1
matrix can be compared bit-for-bit against the working-tree stride-1 matrix.
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "_head_build_matrix", HERE / "_head_build_matrix.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod.OUT_DIR = HERE / "_artifacts"
sys.argv = ["_run_head_build"] + sys.argv[1:]
mod.main()
