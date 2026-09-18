"""Verify the P0 finding: a corrupt report must not yield a green audit.

Truncates one small report, runs the audit, reports the exit code, then restores
the file byte-for-byte. Exits non-zero if the audit reported success (exit 0),
which is the bug.

Deliberately NOT ml_search_wide.json: a regeneration job is running and may write
that file at any moment, so truncating it could corrupt real work.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys

TARGET = pathlib.Path("reports/webpro_scan_summary.json")
BACKUP = pathlib.Path("scripts/scratch/_scan_backup.json")


def main() -> int:
    original = TARGET.read_bytes()
    digest = hashlib.sha256(original).hexdigest()[:12]
    print(f"original: {len(original):,} bytes, sha256[:12]={digest}")
    shutil.copy2(TARGET, BACKUP)
    try:
        # A truncated JSON file: valid prefix, no closing braces.
        TARGET.write_bytes(original[: len(original) // 2])
        print(f"truncated to {TARGET.stat().st_size:,} bytes")
        proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        tail = [ln.strip() for ln in out.splitlines()
                if "checks run" in ln or "problem" in ln]
        for ln in tail[-4:]:
            print("  ", ln)

        # The distinction that matters: was the corrupt file RECORDED as a
        # problem, or merely printed and forgotten? The summary block after the
        # separator lists only recorded problems.
        summary = out.rsplit("=" * 70, 1)[-1]
        printed = "is not valid JSON" in out
        recorded = "webpro_scan_summary" in summary
        print(f"\nprinted a FAIL for the corrupt file : {printed}")
        print(f"recorded it in the problem list     : {recorded}")
        print(f"audit exit code                     : {proc.returncode}")
        print("--- summary block ---")
        print(summary.strip()[:400])
        if not recorded:
            print("\nRESULT: BUG CONFIRMED -- load() prints FAIL but records nothing,")
            print("        so a corrupt report leaves the problem list empty.")
            return 1
        print("\nRESULT: correct -- corruption is recorded")
        return 0
    finally:
        TARGET.write_bytes(original)
        BACKUP.unlink(missing_ok=True)
        restored = TARGET.read_bytes()
        print("restored:", "byte-identical" if restored == original else "MISMATCH!")


if __name__ == "__main__":
    raise SystemExit(main())
