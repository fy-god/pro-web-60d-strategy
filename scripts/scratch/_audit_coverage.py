"""List report files that scripts/audit_reports.py never references."""
from __future__ import annotations

import pathlib
import re

AUDIT = pathlib.Path("scripts/audit_reports.py")
text = AUDIT.read_text(encoding="utf-8")

named = set(re.findall(r"[\"']([A-Za-z0-9_]+\.(?:json|csv))[\"']", text))
on_disk = {p.name for p in pathlib.Path("reports").glob("*")
           if p.suffix in (".json", ".csv")}

print(f"named in audit: {len(named)}")
for n in sorted(named):
    print("   ", n)
print()
missing = sorted(on_disk - named)
print(f"present on disk but never referenced: {len(missing)}")
for n in missing:
    size = (pathlib.Path("reports") / n).stat().st_size
    print(f"    {n}  ({size/1024:.1f} KB)")
