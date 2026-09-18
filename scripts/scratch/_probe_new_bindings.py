"""Negative test: do the new bindings actually fail when the data is wrong?

A check that passes on both correct and corrupted input is worthless. This
mutates each newly-added binding's target in a COPY of the repo, runs the audit,
and requires the problem count to RISE. The baseline is measured, not assumed.
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
TMP = pathlib.Path(tempfile.mkdtemp(prefix="auditprobe_"))
WORK = TMP / "repo"


def run_audit(cwd: pathlib.Path) -> tuple[int, str]:
    env = dict(os.environ, PYTHONPATH=str(cwd))
    p = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                       cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"(\d+) problem\(s\)", p.stdout or "")
    n = int(m.group(1)) if m else -1
    return n, (p.stdout or "")


def copy_repo() -> None:
    """Copy only what the audit reads: text, reports and CSVs."""
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
    for name in ("README.md", "TARGET_70PCT.md", "RESULTS.md", "cordis.yml"):
        s = SRC / name
        if s.exists():
            shutil.copy2(s, WORK / name)


copy_repo()
base, out = run_audit(WORK)
print(f"baseline on the copy: {base} problem(s)")
if base != 0:
    print("!! baseline is not clean; the copy is not comparable. Output tail:")
    print("\n".join(out.splitlines()[-25:]))
    sys.exit(2)

MUTATIONS = [
    ("9.2 signals cell",
     "README.md",
     r"(\| `leader_momentum` \| )616( \| 98 \|)",
     r"\g<1>999\g<2>"),
    ("9.2 hit_rate cell",
     "README.md",
     r"(\| `leader_momentum` \| 616 \| 98 \| \*\*15\.91%\*\* \| 32 \| )20\.62(%)",
     r"\g<1>99.99\g<2>"),
    ("9.2 excluding cell",
     "README.md",
     r"(\| `leader_momentum` \| 616 \| 98 \| \*\*15\.91%\*\* \| 32 \| 20\.62% \| \*\*)18\.34(%)",
     r"\g<1>1.11\g<2>"),
    ("9.2 unfillable cell",
     "README.md",
     r"(\| `gap_follow_through` \| 3,978 \| )480( \|)",
     r"\g<1>999\g<2>"),
    ("9.2 family-wide total",
     "README.md",
     r"10,410 of 637,499 resolved signals \(1\.63%\)",
     "10,411 of 637,499 resolved signals (1.63%)"),
    ("9.2 obsolete framing",
     "README.md",
     r"\*\*The two signal-count files now reconcile",
     "**The two signal-count files disagree: the second count is larger"),
    ("tradeability censored",
     "reports/tradeability.json",
     r'"censored": 9219',
     '"censored": 9000'),
    ("wide stride",
     "reports/ml_search_wide.json",
     r'"stride": 1',
     '"stride": 5'),
    ("label_pairs vintage",
     "outputs/ml/audit/label_pairs_audit.json",
     r'"shipped_matrix_value_for_stale_field": 0',
     '"shipped_matrix_value_for_stale_field": 5747'),
    ("label_pairs prose",
     "outputs/ml/audit/label_pairs_audit.json",
     r"is a PRE-FIX measurement",
     r"> 0 is a genuine defect"),
]

print(f"\n{'mutation':<28}{'base':>6}{'mutated':>9}{'delta':>7}  verdict")
print("-" * 66)
failures = []
for name, rel, pattern, repl in MUTATIONS:
    copy_repo()
    target = WORK / rel
    text = target.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text)
    if n == 0:
        print(f"{name:<28}{base:>6}{'--':>9}{'--':>7}  PATTERN NOT FOUND")
        failures.append(name)
        continue
    target.write_text(new, encoding="utf-8")
    got, gout = run_audit(WORK)
    verdict = "CAUGHT" if got > base else "MISSED"
    if got <= base:
        failures.append(name)
    print(f"{name:<28}{base:>6}{got:>9}{got - base:>+7}  {verdict}")

shutil.rmtree(WORK, ignore_errors=True)
print("-" * 66)
print(f"{len(MUTATIONS) - len(failures)}/{len(MUTATIONS)} mutations caught")
for name in failures:
    print("  MISSED:", name)
print("RESULT:", "ALL BINDINGS ARE LIVE" if not failures else "SOME BINDINGS VACUOUS")
