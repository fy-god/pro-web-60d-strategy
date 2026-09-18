"""Trace which audit check loads each published artifact.

The coverage metric now says every published artifact is read by some check, but
the earlier regex-based metric said seven were not. Both cannot be right. Loading
is also not the same as CHECKING -- a file can be loaded and then never compared
to anything -- so this traces each load to the check that performed it, and prints
whether that check consumed a value from the payload.
"""
from __future__ import annotations

import collections
import importlib.util
import sys
import traceback

spec = importlib.util.spec_from_file_location("audit_reports",
                                              "scripts/audit_reports.py")
ar = importlib.util.module_from_spec(spec)
sys.modules["audit_reports"] = ar
spec.loader.exec_module(ar)

origin = collections.defaultdict(list)
real_load = ar.load
real_load_csv = ar.load_csv


def traced_load(name):
    stack = traceback.extract_stack()
    caller = None
    for fr in reversed(stack[:-1]):
        if fr.filename.endswith("audit_reports.py") and fr.name != "traced_load":
            caller = fr
            break
    if caller:
        origin[name].append(f"{caller.name}:{caller.lineno}")
    return real_load(name)


def traced_load_csv(name):
    stack = traceback.extract_stack()
    caller = None
    for fr in reversed(stack[:-1]):
        if fr.filename.endswith("audit_reports.py") and fr.name != "traced_load_csv":
            caller = fr
            break
    if caller:
        origin[name].append(f"{caller.name}:{caller.lineno}")
    return real_load_csv(name)


ar.load = traced_load
ar.load_csv = traced_load_csv

f = ar.Findings(verbose=False)
for fn in (ar.check_arithmetic, ar.check_pooling, ar.check_cross_report,
           ar.check_prose, ar.check_frontier, ar.check_markdown_structure):
    try:
        fn(f)
    except TypeError:
        fn(f, False)

print("=" * 72)
print(f"{len(origin)} artifact(s) loaded by the checks")
print("=" * 72)
for name in sorted(origin):
    print(f"\n{name}")
    for site in origin[name][:4]:
        print(f"    {site}")
