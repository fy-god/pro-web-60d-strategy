"""Verify the new lowzone/audit-README and inventory guards actually fail.

Each guard was written to catch a specific defect. This injects the defeating
state, runs the audit, asserts the guard fires, then restores the file
byte-for-byte. Guards that cannot fail are worse than no guard, because they read
as coverage.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(".")
RESULTS = []


def run_audit():
    r = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                       capture_output=True, text=True, cwd=REPO)
    return r.stdout + r.stderr


def probe(label, path, mutate, expect_substr):
    p = REPO / path
    orig = p.read_text(encoding="utf-8")
    bak = p.with_suffix(p.suffix + ".probe_bak")
    shutil.copy2(p, bak)
    try:
        new = mutate(orig)
        if new == orig:
            print(f"  SKIP {label}: mutation changed nothing")
            RESULTS.append((label, None))
            return
        p.write_text(new, encoding="utf-8")
        out = run_audit()
        hits = [ln.strip() for ln in out.splitlines()
                if ln.strip().startswith("FAIL") and expect_substr in ln]
        caught = bool(hits)
        print(f"  {'CAUGHT' if caught else 'MISSED'} {label}")
        for h in hits[:2]:
            print(f"        {h}")
        RESULTS.append((label, caught))
    finally:
        shutil.copy2(bak, p)
        bak.unlink(missing_ok=True)
        assert p.read_text(encoding="utf-8") == orig, f"{path} not restored"


print("=" * 74)
print("guard probes")
print("=" * 74)

# 1. audit/README.md cites a wrong V03 figure.
probe("audit/README.md wrong V03 figure", "audit/README.md",
      lambda t: t.replace("V03 (4.37%)", "V03 (9.99%)", 1),
      "audit/README.md cites V03")

# 2. audit/README.md's claim flipped so V07 now appears to beat V03.
probe("audit/README.md V07 appears to beat V03", "audit/README.md",
      lambda t: t.replace("(4.23%/4.08%) do not beat", "(9.23%/9.08%) do not beat", 1),
      "V07")

# 3. The 0.15% figure removed from the ledger's reach by editing the CSV.
probe("lowzone ledger loses its low60 rows", "reports/lowzone_hit_rates.csv",
      lambda t: "\n".join(ln for ln in t.splitlines()
                          if "low60" not in ln) + "\n",
      "rows carry the fields")

# 4. A malformed row that the old code silently skipped.
def break_a_row(t):
    lines = t.splitlines()
    parts = lines[1].split(",")
    parts[2] = "0.99"          # bull_precision -> float() fails on purpose? no: it parses
    parts[4] = "NOT_A_NUMBER"  # lift_vs_baseline -> unparseable
    lines[1] = ",".join(parts)
    return "\n".join(lines) + "\n"


probe("lowzone row with an unparseable field", "reports/lowzone_hit_rates.csv",
      break_a_row, "unparseable")

# 5. The lowzone table truncated to its header.
probe("lowzone table truncated to header", "reports/lowzone_hit_rates.csv",
      lambda t: t.splitlines()[0] + "\n", "carry the fields")

print()
bad = [lbl for lbl, ok in RESULTS if ok is False]
skip = [lbl for lbl, ok in RESULTS if ok is None]
caught = [lbl for lbl, ok in RESULTS if ok is True]
print(f"caught {len(caught)}  missed {len(bad)}  skipped {len(skip)}")
if bad:
    for lbl in bad:
        print(f"  MISSED: {lbl}")
print("\nRESULT:", "PASS -- every guard fires" if not bad and not skip
      else "ATTENTION REQUIRED")
raise SystemExit(0 if not bad and not skip else 1)
