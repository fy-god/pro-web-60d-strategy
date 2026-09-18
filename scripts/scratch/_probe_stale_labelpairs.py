"""Check the claim in label_pairs_audit.json against the SHIPPED matrix.

The audit reported that outputs/ml/audit/label_pairs_audit.json stores
`label_close_defined_where_resolved_false = 5747` and its `read_this` prose still
instructs a reader to treat `> 0` as "a genuine defect in build_matrix", while the
shipped stride-5 matrix measures 0 (the fix landed in c97de8c and the matrix was
rebuilt after the artifact was written).

Reads 3 columns of the 536,143-row stride-5 matrix -- no full load.
"""
from __future__ import annotations

import io
import json
import pathlib

import numpy as np
import pandas as pd

ART = pathlib.Path("outputs/ml/audit/label_pairs_audit.json")
M5 = pathlib.Path("outputs/ml/matrix_h10_t30_s5.parquet")
META = pathlib.Path("outputs/ml/matrix_h10_t30_s5_meta.json")

d = json.load(io.open(ART, encoding="utf-8"))


def find(obj, key, path=""):
    """Locate `key` anywhere in the payload."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield path + "/" + k, v
            yield from find(v, key, path + "/" + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find(v, key, f"{path}[{i}]")


print("=== what the artifact stores ===")
for p, v in find(d, "label_close_defined_where_resolved_false"):
    print(f"  {p} = {v}")

print("\n=== the surviving prose ===")
for p, v in find(d, "read_this"):
    txt = str(v)
    if "resolved_false" in txt:
        for line in txt.split("."):
            if "resolved_false" in line or "defect" in line:
                print(f"  {line.strip()[:160]}")
    else:
        print(f"  {p}: (no mention of resolved_false)")

print("\n=== measured on the SHIPPED stride-5 matrix ===")
cols = ["resolved", "label_close"]
have = set(pd.read_parquet(M5, columns=["resolved"]).columns)
df = pd.read_parquet(M5, columns=cols)
n = len(df)
n_unres = int((~df["resolved"].astype(bool)).sum())
offend = int((df["label_close"].notna() & ~df["resolved"].astype(bool)).sum())
print(f"  rows                                   : {n:,}")
print(f"  resolved == 0                          : {n_unres:,}")
print(f"  label_close notna & resolved == 0      : {offend}")
print(f"  label_close finite exactly where res=1 : "
      f"{bool((df['label_close'].notna() == df['resolved'].astype(bool)).all())}")

meta = json.load(io.open(META, encoding="utf-8"))
mc = float(df["label_close"].mean())
print(f"  label_close mean                       : {mc!r}")
print(f"  meta base_rate_close                   : {meta.get('base_rate_close')!r}")

stored = next(find(d, "label_close_defined_where_resolved_false"), (None, None))[1]
print(f"\n  artifact says {stored}; matrix says {offend} -> "
      f"{'STALE ARTIFACT' if stored != offend else 'agree'}")

# Timestamps, to show the ordering rather than assert it.
import datetime
for p in (ART, M5, pathlib.Path("src/ml/build_matrix.py")):
    if p.exists():
        print(f"  mtime {datetime.datetime.fromtimestamp(p.stat().st_mtime):%Y-%m-%d %H:%M:%S}  {p}")
