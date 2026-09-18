"""Mutation test: prove the holdout-treatment table check actually fires.

Temporarily rewrites one row of the 2026-holdout table in TARGET_70PCT.md to the
superseded values (13.02% / 7,588 at "Drop busiest date"), runs the audit, and
restores the file. Exits non-zero if the audit fails to notice.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

DOC = pathlib.Path("TARGET_70PCT.md")
STALE = "| Drop busiest date | 13.02% | 7,588 |"
LIVE = "| Drop busiest date | 14.13% | 5,781 |"

original = DOC.read_text(encoding="utf-8")
if LIVE not in original:
    sys.exit(f"probe: expected live row {LIVE!r} not found; refusing to guess")

try:
    DOC.write_text(original.replace(LIVE, STALE), encoding="utf-8")
    print("injected stale row:", STALE)
    proc = subprocess.run(
        [sys.executable, "scripts/audit_reports.py"],
        capture_output=True, text=True,
    )
    out = proc.stdout + proc.stderr
    hits = [ln.strip() for ln in out.splitlines()
            if "Drop busiest" in ln or "checks run" in ln]
    for ln in hits:
        print("  ", ln)
    caught = any("Drop busiest" in ln for ln in hits)
    print("\nRESULT:", "CAUGHT (check works)" if caught
          else "NOT CAUGHT  <-- the check is blind")
    sys.exit(0 if caught else 1)
finally:
    DOC.write_text(original, encoding="utf-8")
    print("restored TARGET_70PCT.md")
