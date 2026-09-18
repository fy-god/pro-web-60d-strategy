"""Negative test for the strict_* direction guard.

Restores the ORIGINAL false claim in one LOOSER module (in a copy) and requires the
audit to go red; then removes BASE_STRATEGY_ID and requires red again. Also
re-introduces the annotated-declaration form that defeated the first version of the
regex, to confirm the `unparsed` check now catches it.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(".").resolve()
TMP = pathlib.Path(tempfile.mkdtemp(prefix="strictprobe_"))
WORK = TMP / "repo"


def run_audit(cwd):
    env = dict(os.environ, PYTHONPATH=str(cwd))
    p = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                       cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"(\d+) problem\(s\)", p.stdout or "")
    return (int(m.group(1)) if m else -1), (p.stdout or "")


def copy_repo():
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    for name in ("scripts", "reports", "src", "experts", "tests", "audit",
                 "outputs", "docs"):
        s = SRC / name
        if s.exists():
            shutil.copytree(s, WORK / name,
                            ignore=shutil.ignore_patterns(
                                "__pycache__", "*.parquet", "*.npz"))
    for name in ("README.md", "TARGET_70PCT.md", "RESULTS.md"):
        s = SRC / name
        if s.exists():
            shutil.copy2(s, WORK / name)


copy_repo()
base_n, out = run_audit(WORK)
print(f"baseline on a fresh copy: {base_n} problem(s)")
if base_n != 0:
    print("!! copy baseline not clean; cannot compare")
    print("\n".join(out.splitlines()[-20:]))
    sys.exit(2)

CASES = [
    # (name, file, pattern, replacement)
    ("restore false 'higher cutoff' claim",
     "experts/strategies/strict_oversold_rebound_v2.py",
     r'THESIS = \(\n(.*?)\n\)',
     'THESIS = "A higher cutoff keeps only oversold rebounds with the clearest '
     'exhaustion and recovery signals."'),
    ("restore 'high-precision' docstring",
     "experts/strategies/strict_leader_momentum_v2.py",
     r'^"""Fixed-cutoff [^"]*"""',
     '"""Development-only high-precision leader-momentum selector."""'),
    ("drop BASE_STRATEGY_ID",
     "experts/strategies/strict_washout_complete.py",
     r'^BASE_STRATEGY_ID = "washout_complete"\n', ''),
    ("point BASE_STRATEGY_ID at a missing base",
     "experts/strategies/strict_platform_breakout.py",
     r'^BASE_STRATEGY_ID = "platform_breakout"',
     'BASE_STRATEGY_ID = "no_such_strategy"'),
    # NOTE: washout_complete's base ALREADY uses the annotated form
    # `THRESHOLD: float = 0.82`, which is what defeated the first version of the
    # audit's regex -- so it is not a mutation, it is the baseline. The mutation
    # that tests the `unparsed` guard is making a declaration unparseable.
    ("convert base to an UNPARSEABLE declaration",
     "experts/strategies/washout_complete.py",
     r'^THRESHOLD: float = 0\.82$',
     'THRESHOLD: float = get_default()  # no literal'),
    ("remove BASE_STRATEGY_ID from __all__",
     "experts/strategies/strict_bollinger_release_v2.py",
     r'\n\s*"BASE_STRATEGY_ID",', ''),
]

print(f"\n{'case':<48}{'base':>6}{'mut':>6}{'delta':>7}  verdict")
print("-" * 76)
missed = []
for name, rel, pat, rep in CASES:
    copy_repo()
    t = WORK / rel
    text = t.read_text(encoding="utf-8")
    new, n = re.subn(pat, rep, text, flags=re.M | re.S)
    if n == 0:
        print(f"{name:<48}{base_n:>6}{'--':>6}{'--':>7}  PATTERN NOT FOUND")
        missed.append(name)
        continue
    t.write_text(new, encoding="utf-8")
    got, gout = run_audit(WORK)
    verdict = "CAUGHT" if got > base_n else "MISSED"
    if got <= base_n:
        missed.append(name)
    print(f"{name:<48}{base_n:>6}{got:>6}{got - base_n:>+7}  {verdict}")

shutil.rmtree(WORK, ignore_errors=True)
print("-" * 76)
print(f"{len(CASES) - len(missed)}/{len(CASES)} cases caught")
for m in missed:
    print("  MISSED:", m)
print("RESULT:", "GUARD IS LIVE" if not missed else "GUARD HAS HOLES")
