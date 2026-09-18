"""Verify the new frontier checks can actually fail.

Perturbs each published figure in turn -- the headline ceiling in README, the
floor-table value in TARGET, and a recall-floor row -- and confirms the audit
flags it. Restores the documents byte-for-byte.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

CASES = [
    ("README.md", "26.78%", "25.99%", "headline ceiling in README",
     "headline ceiling"),
    ("TARGET_70PCT.md", "| 250 | 26.78% |", "| 250 | 25.99% |", "floor table row",
     "floor table states"),
    ("TARGET_70PCT.md", "| ≥ 50% | 11.46% |", "| ≥ 50% | 12.99% |", "recall floor",
     "recall-floor"),
]


def main() -> int:
    failures = 0
    for doc, old, new, label, marker in CASES:
        path = pathlib.Path(doc)
        original = path.read_text(encoding="utf-8")
        if old not in original:
            print(f"SKIP  {label}: anchor {old!r} not found in {doc}")
            continue
        backup = path.with_suffix(path.suffix + ".probe_bak")
        shutil.copy2(path, backup)
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            proc = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                                  capture_output=True, text=True)
            out = proc.stdout + proc.stderr
            fails = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("FAIL")]
            # Match on the check's own identifying text: the FAIL message quotes
            # the EXPECTED value from the report, never the injected one.
            hit = [ln for ln in fails if marker in ln]
            print(f"{'CAUGHT' if hit else 'MISSED'}  {label} ({old} -> {new})")
            if hit:
                print(f"          {hit[0][:120]}")
            else:
                failures += 1
                print(f"          no FAIL matched {marker!r}")
        finally:
            shutil.copy2(backup, path)
            backup.unlink(missing_ok=True)
            restored = path.read_text(encoding="utf-8")
            if restored != original:
                print(f"          RESTORE MISMATCH for {doc}")
                failures += 1
    print("\nRESULT:", "PASS" if failures == 0 else f"{failures} problem(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
