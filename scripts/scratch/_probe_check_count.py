"""Verify the moving-check-count guard fires.

Inserts a line claiming a specific audit-check count into README.md, runs the
audit, and restores the file. Exits non-zero if the audit does not catch it.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

DOC = pathlib.Path("README.md")
BACKUP = pathlib.Path("scripts/scratch/_readme_count_backup.md")
INJECT = "python scripts/audit_reports.py        # still 111 checks, 0 problems\n"


def main() -> int:
    original = DOC.read_text(encoding="utf-8")
    anchor = "python scripts/audit_reports.py"
    if anchor not in original:
        sys.exit("probe: anchor line not found")
    line_start = original.find(anchor)
    line_end = original.find("\n", line_start) + 1
    mutated = original[:line_start] + INJECT + original[line_end:]

    shutil.copy2(DOC, BACKUP)
    try:
        DOC.write_text(mutated, encoding="utf-8")
        print(f"injected: {INJECT.strip()!r}")
        proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        hits = [ln.strip() for ln in out.splitlines()
                if "checks'" in ln or "checks run" in ln]
        for ln in hits[:6]:
            print("  ", ln)
        caught = any("asserts" in ln and "checks'" in ln for ln in hits)
        print("\nRESULT:", "CAUGHT (guard fires)" if caught
              else "NOT CAUGHT  <-- guard is blind")
        return 0 if caught else 1
    finally:
        shutil.copy2(BACKUP, DOC)
        BACKUP.unlink(missing_ok=True)
        print("restored README.md")


if __name__ == "__main__":
    raise SystemExit(main())
