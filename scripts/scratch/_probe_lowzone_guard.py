"""Confirm the lowzone threshold guard catches a reintroduced fallback.

The audit binds src/backtest_lowzone.py at the source level because the published
CSV cannot show the defect until it is regenerated. A guard that never fires is
worthless, so this probe restores the exact buggy expression, requires the audit to
FAIL naming it, and restores the file byte-for-byte.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

SRC = pathlib.Path("src/backtest_lowzone.py")
ORIG = SRC.read_bytes()


def audit_problems():
    r = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    n = 0
    for ln in out.splitlines():
        m = re.search(r"(\d+) problem\(s\)", ln)
        if m:
            n = int(m.group(1))
    named = [ln.strip() for ln in out.splitlines()
             if ln.strip().startswith("FAIL") and "backtest_lowzone" in ln]
    return n, named


base_n, _ = audit_problems()
print(f"baseline: {base_n} problem(s)\n")

text = ORIG.decode("utf-8")
# Reintroduce exactly the retired line, in executable position.
old_block = """                prior = _prior_year_scores(pool, year, version, regime)
                if prior is None or len(prior) < 50:
                    skipped.append({"""
new_block = """                prior = _prior_year_scores(pool, year, version, regime)
                source = prior if prior is not None and len(prior) >= 50 else score
                if prior is None or len(prior) < 50:
                    skipped.append({"""
assert old_block in text, "anchor block not found -- probe is stale"
SRC.write_text(text.replace(old_block, new_block, 1), encoding="utf-8")

try:
    n, named = audit_problems()
    print(f"with the fallback reintroduced: {n} problem(s) (+{n - base_n})")
    for x in named:
        print(f"  {x}")
    ok = n > base_n and named
    print(f"\n{'CAUGHT' if ok else 'MISSED'}: the guard "
          f"{'fires' if ok else 'DOES NOT fire'} on the retired expression")
finally:
    SRC.write_bytes(ORIG)
    assert SRC.read_bytes() == ORIG, "source not restored byte-for-byte"

after_n, _ = audit_problems()
print(f"after restore: {after_n} problem(s) -- back to baseline: "
      f"{after_n == base_n}")
raise SystemExit(0 if (ok and after_n == base_n) else 1)
