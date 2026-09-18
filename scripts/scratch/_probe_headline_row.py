"""Verify P0-4 is fixed: README's headline holdout row must be protected.

Copies README.md, replaces the live holdout precision in the *headline results
table row* with a superseded value, runs the audit, and restores the file. The
previous version exempted that row because "previous" appeared in the table row
above it. Exits non-zero if the audit fails to flag it.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

DOC = pathlib.Path("README.md")
BACKUP = pathlib.Path("scripts/scratch/_readme_backup.md")

# The headline row, and a superseded value that must be caught.
LIVE = "| **One-shot 2026 holdout, purged** | — | **13.61%** | 6,202 | — |"
STALE = "| **One-shot 2026 holdout, purged** | — | **11.05%** | 6,202 | — |"


def main() -> int:
    original = DOC.read_text(encoding="utf-8")
    if LIVE not in original:
        # Fall back to a looser anchor so the probe still reports something
        # useful if the table is reformatted.
        idx = original.find("One-shot 2026 holdout, purged")
        if idx < 0:
            sys.exit("probe: headline holdout row not found")
        line_start = original.rfind("\n", 0, idx) + 1
        line_end = original.find("\n", idx)
        old_line = original[line_start:line_end]
        print(f"anchor line: {old_line!r}")
        new_line = old_line.replace("13.61", "11.05")
    else:
        old_line, new_line = LIVE, STALE
    if "13.61" not in old_line:
        sys.exit("probe: anchor does not contain the live precision")

    shutil.copy2(DOC, BACKUP)
    try:
        DOC.write_text(original.replace(old_line, new_line, 1), encoding="utf-8")
        print(f"injected: {new_line!r}")
        proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        hits = [ln.strip() for ln in out.splitlines()
                if "superseded" in ln or "checks run" in ln]
        for ln in hits:
            print("  ", ln)
        caught = any("superseded" in ln and "FAIL" in ln for ln in hits)
        print("\nRESULT:", "CAUGHT (headline row protected)" if caught
              else "NOT CAUGHT  <-- the headline row is still masked")
        return 0 if caught else 1
    finally:
        shutil.copy2(BACKUP, DOC)
        BACKUP.unlink(missing_ok=True)
        print("restored README.md")


if __name__ == "__main__":
    raise SystemExit(main())
