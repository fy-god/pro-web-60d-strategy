"""Verify the tightened cross-module base-rate tolerance detects a grid change.

Rewrites ml_precision_ceiling.json's base_rate to the stride-5 value (a 4.02e-04
relative shift -- the exact difference between the two grids), runs the audit, and
restores the file byte-for-byte. The previous 5e-3 tolerance accepted this.
Exits non-zero if the audit does not notice.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

TARGET = pathlib.Path("reports/ml_precision_ceiling.json")
BACKUP = pathlib.Path("scripts/scratch/_ceiling_backup.json")
STRIDE5_BASE = 11496 / 281227  # 0.04087800958, the stride-5 grid


def main() -> int:
    original = TARGET.read_bytes()
    doc = json.loads(original)
    live = doc.get("base_rate")
    print(f"live base_rate (dense): {live!r}")
    print(f"substituting stride-5 : {STRIDE5_BASE!r}")
    rel = abs(STRIDE5_BASE - live) / live
    print(f"relative shift        : {rel:.3e}  "
          f"(old tolerance 5e-3 would accept: {rel < 5e-3})")

    shutil.copy2(TARGET, BACKUP)
    try:
        doc["base_rate"] = STRIDE5_BASE
        TARGET.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                              capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        hits = [ln.strip() for ln in out.splitlines()
                if "agrees across modules" in ln or "checks run" in ln]
        for ln in hits:
            print("  ", ln)
        caught = any("agrees across modules" in ln and "FAIL" in ln for ln in hits)
        print("\nRESULT:", "CAUGHT (tolerance detects a grid change)" if caught
              else "NOT CAUGHT  <-- still too loose")
        return 0 if caught else 1
    finally:
        TARGET.write_bytes(original)
        BACKUP.unlink(missing_ok=True)
        print("restored:", "byte-identical"
              if TARGET.read_bytes() == original else "MISMATCH!")


if __name__ == "__main__":
    raise SystemExit(main())
