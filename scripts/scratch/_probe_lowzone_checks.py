"""Mutation test for the lowzone_hit_rates.csv checks in scripts/audit_reports.py.

Perturbs `lift_vs_baseline` in one row so it no longer equals
precision / baseline, runs the audit, and restores the file. Exits non-zero if
the audit does not notice.
"""
from __future__ import annotations

import csv
import io
import pathlib
import shutil
import subprocess
import sys

TARGET = pathlib.Path("reports/lowzone_hit_rates.csv")
BACKUP = pathlib.Path("scripts/scratch/_lowzone_backup.csv")


def main() -> int:
    if not TARGET.exists():
        sys.exit("probe: lowzone CSV not found")
    shutil.copy2(TARGET, BACKUP)
    rows = list(csv.DictReader(io.open(TARGET, encoding="utf-8", newline="")))
    if not rows:
        sys.exit("probe: no rows")
    fields = list(rows[0].keys())

    victim = rows[0]
    before = victim["lift_vs_baseline"]
    victim["lift_vs_baseline"] = str(float(before) + 0.5)
    print(f"perturbed {victim.get('version')}/{victim.get('regime')}: "
          f"lift {before} -> {victim['lift_vs_baseline']}")

    try:
        with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        hits = [ln.strip() for ln in out.splitlines()
                if "lowzone lift" in ln or "checks run" in ln]
        for ln in hits:
            print("  ", ln)
        caught = any("lowzone lift" in ln and "FAIL" in ln for ln in hits)
        print("\nRESULT:", "CAUGHT (check works)" if caught
              else "NOT CAUGHT  <-- the check is blind")
        return 0 if caught else 1
    finally:
        shutil.copy2(BACKUP, TARGET)
        BACKUP.unlink(missing_ok=True)
        print("restored", TARGET)


if __name__ == "__main__":
    raise SystemExit(main())
