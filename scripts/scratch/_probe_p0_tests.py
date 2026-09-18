"""Do the new P0 regression tests actually catch the reported defects?

Re-introduces each P0 defect in a scratch copy of the source and runs the suite.
  P0-A  src/labels.py: first-hit freeze back to `>=`
  P0-B  src/runner.py: warm-up filter made conditional on stride again
A mutation that still passes means the new test is decorative.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

SRC = pathlib.Path(r"D:\ccc\pro-web-60d-strategy")
WORK = pathlib.Path(r"D:\ccc\pro-web-60d-strategy\.audit_tmp\probe_p0_tests")


def copy_repo() -> None:
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    for name in ("src", "experts", "tests", "scripts"):
        s = SRC / name
        if s.exists():
            shutil.copytree(s, WORK / name,
                            ignore=shutil.ignore_patterns("__pycache__"))


def run_tests() -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                       cwd=WORK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


MUTATIONS = [
    # (label, relative file, old, new)
    ("P0-A: first-hit freeze >= (old bug)",
     "src/labels.py",
     "newly = (~hit) & valid & (high_d > target)",
     "newly = (~hit) & valid & (high_d >= target)"),
    ("P0-B: warm-up only when stride>1 (old bug)",
     "src/runner.py",
     "    keep = seq >= min_history\n    if stride > 1:\n        keep &= (seq % stride == 0)",
     "    keep = seq >= min_history\n    if stride > 1:\n        keep &= (seq % stride == 0)"),
]

print("copying ...")
copy_repo()
rc, out = run_tests()
print(f"baseline: exit={rc}  {out.strip().splitlines()[-1]}")
if rc != 0:
    print("BASELINE NOT GREEN -- abort")
    sys.exit(1)

print()
print(f"{'mutation':<44}{'exit':>5}  verdict")
print("-" * 66)
killed = survived = 0

# P0-A
copy_repo()
f = WORK / "src" / "labels.py"
t = f.read_text(encoding="utf-8")
old = "newly = (~hit) & valid & (high_d > target)"
assert t.count(old) == 1, f"anchor count {t.count(old)}"
f.write_text(t.replace(old, "newly = (~hit) & valid & (high_d >= target)"),
             encoding="utf-8")
rc, out = run_tests()
if rc != 0:
    print(f"{'P0-A: freeze back to >=':<44}{rc:>5}  KILLED")
    killed += 1
else:
    print(f"{'P0-A: freeze back to >=':<44}{rc:>5}  SURVIVED")
    survived += 1

# P0-B -- restore the exact old bug: the warm-up filter inside `if stride > 1`.
copy_repo()
f = WORK / "src" / "runner.py"
t = f.read_text(encoding="utf-8")
old = """    keep = seq >= min_history
    if stride > 1:
        keep &= (seq % stride == 0)"""
new = """    if stride > 1:
        keep = (seq >= min_history) & (seq % stride == 0)
    else:
        keep = pd.Series(True, index=panel.index)"""
assert t.count(old) == 1, f"anchor count {t.count(old)}"
f.write_text(t.replace(old, new), encoding="utf-8")
rc, out = run_tests()
if rc != 0:
    print(f"{'P0-B: no warm-up filter at stride=1':<44}{rc:>5}  KILLED")
    killed += 1
else:
    print(f"{'P0-B: no warm-up filter at stride=1':<44}{rc:>5}  SURVIVED")
    survived += 1

print("-" * 66)
print(f"{killed}/{killed+survived} mutations killed")
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(0 if survived == 0 else 1)
