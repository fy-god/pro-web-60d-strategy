"""Verify the RESULTS.md checks fail on injected drift.

RESULTS.md was the review's largest coverage gap: all 35 rows, the base-rate
table and the headline row were compared to nothing. Each perturbation below must
be caught. Restores the file byte-for-byte.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

DOC = pathlib.Path("RESULTS.md")
BACKUP = pathlib.Path("scripts/scratch/_results_backup.md")

CASES = [
    ("| 1 | `leader_momentum` | 553 | 106 |", "| 1 | `leader_momentum` | 599 | 106 |",
     "a signal count in the main table"),
    ("**19.17%**", "**18.17%**", "the headline hit rate"),
    ("6.32x", "5.32x", "the headline lift"),
    ("| 493,246 | 3.0348% |", "| 493,246 | 3.1348% |", "the webpro base rate"),
]


def main() -> int:
    original = DOC.read_text(encoding="utf-8")
    failures = 0
    for old, new, label in CASES:
        if old not in original:
            print(f"SKIP  {label}: anchor {old!r} not found")
            continue
        shutil.copy2(DOC, BACKUP)
        try:
            DOC.write_text(original.replace(old, new, 1), encoding="utf-8")
            proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                                  capture_output=True, text=True)
            out = proc.stdout + proc.stderr
            fails = [ln.strip() for ln in out.splitlines()
                     if ln.strip().startswith("FAIL") and "RESULTS.md" in ln]
            print(f"{'CAUGHT' if fails else 'MISSED'}  {label}  ({old[:34]}...)")
            if fails:
                print(f"          {fails[0][:118]}")
            else:
                failures += 1
        finally:
            shutil.copy2(BACKUP, DOC)
            BACKUP.unlink(missing_ok=True)
            if DOC.read_text(encoding="utf-8") != original:
                print("          RESTORE MISMATCH")
                failures += 1
    print("\nRESULT:", "PASS" if failures == 0 else f"{failures} problem(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
