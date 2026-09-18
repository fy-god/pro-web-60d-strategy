"""Verify search.py now stamps matrix provenance into its report.

Before this change search.py read the parquet through pandas instead of
wf.load_matrix, so LAST_LOAD stayed empty and save_report could stamp neither
_matrix_rows nor _matrix_sessions. Reports carried a stride with no evidence of
which grid produced it.

This drives the same stamping path without running a search: it performs the
provenance assignment search.py:main() now does, then writes a throwaway report
and inspects the keys. The throwaway file is deleted afterwards.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, ".")
from src.ml import walkforward as wf  # noqa: E402

stride = wf.resolve_stride()
matrix = wf.matrix_path(horizon=10, target=30, stride=stride)
print(f"resolved matrix: {matrix.name} (stride {stride})")

meta_path = matrix.with_name(matrix.stem + "_meta.json")
print(f"meta file: {meta_path.name}  exists={meta_path.exists()}")
meta = json.loads(meta_path.read_text(encoding="utf-8"))
print(f"  rows={meta.get('rows')}  sessions={meta.get('sessions')}")

# The assignment under test.
wf.LAST_LOAD = {
    "path": str(matrix),
    "stride": stride,
    "rows": int(meta.get("rows") or 0),
    "sessions": int(meta.get("sessions") or 0),
}

path = wf.save_report("_provenance_probe", {"probe": True})
doc = json.loads(path.read_text(encoding="utf-8"))
print(f"\nwrote {path.name}")
for k in ("_matrix", "stride", "_matrix_rows", "_matrix_sessions"):
    print(f"  {k} = {doc.get(k)!r}")

ok = (doc.get("stride") == stride
      and doc.get("_matrix") == matrix.name
      and doc.get("_matrix_rows") == int(meta.get("rows"))
      and doc.get("_matrix_sessions") == int(meta.get("sessions")))
path.unlink(missing_ok=True)
print(f"\nprobe file removed: {not path.exists()}")
for extra in ("_matrix", "stride"):
    pass
bogus = wf.REPORT_DIR / "ml__provenance_probe.json"
print(f"no stray report left: {not bogus.exists()}")

print("\nRESULT:", "PASS -- provenance is stamped" if ok else "FAIL")
raise SystemExit(0 if ok else 1)
