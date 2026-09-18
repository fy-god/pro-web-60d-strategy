"""Mutation test for the CSV denominator checks in scripts/audit_reports.py.

Copies reports/tradeability_by_strategy.csv, perturbs one row so that
`signals != raw + censored`, runs the audit, and restores the file. Exits
non-zero if the audit fails to notice, which would mean the new checks are
decorative.
"""
from __future__ import annotations

import csv
import io
import pathlib
import shutil
import subprocess
import sys

TARGET = pathlib.Path("reports/tradeability_by_strategy.csv")
BACKUP = pathlib.Path("scripts/scratch/_trade_backup.csv")


def main() -> int:
    if not TARGET.exists():
        sys.exit("probe: tradeability CSV not found")
    shutil.copy2(TARGET, BACKUP)

    rows = list(csv.DictReader(io.open(TARGET, encoding="utf-8", newline="")))
    if not rows:
        sys.exit("probe: no rows to perturb")
    fieldnames = list(rows[0].keys())

    victim = rows[0]
    before = victim["signals"]
    victim["signals"] = str(int(victim["signals"]) + 12345)
    print(f"perturbed {victim['label']}: signals {before} -> {victim['signals']}")

    try:
        with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        hits = [ln.strip() for ln in out.splitlines()
                if "tradeability signals" in ln or "checks run" in ln]
        for ln in hits:
            print("  ", ln)
        caught = any("tradeability signals" in ln and "FAIL" in ln for ln in hits)
        print("\nRESULT:", "CAUGHT (check works)" if caught
              else "NOT CAUGHT  <-- the check is blind")
        return 0 if caught else 1
    finally:
        shutil.copy2(BACKUP, TARGET)
        BACKUP.unlink(missing_ok=True)
        print("restored", TARGET)


if __name__ == "__main__":
    raise SystemExit(main())
