"""Do the new tests actually kill the mutations the reviewer used?

An adversarial review found four mutations that the OLD suite did not catch:
  M1  labels.py:186 `>` -> `>=` on the target_return bull comparison
  M2  labels.py:226 remove the per-stock cluster boundary
  M3  labels.py:229 `>=` -> `>` at the cooldown boundary
  M4  labels.py:314 replace the Wilson upper return with a constant

For each, this rewrites src/labels.py in a scratch copy, runs the suite, and
reports whether it fails. A mutation that still passes means the test is
decorative. It also re-runs the four mutations the reviewer said were ALREADY
caught, so a regression in those is visible too.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

SRC = pathlib.Path(r"D:\ccc\pro-web-60d-strategy")
WORK = pathlib.Path(r"D:\ccc\pro-web-60d-strategy\.audit_tmp\probe_tests")


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


def mutate(old: str, new: str) -> None:
    f = WORK / "src" / "labels.py"
    t = f.read_text(encoding="utf-8")
    if old not in t:
        raise SystemExit(f"MUTATION ANCHOR NOT FOUND: {old[:70]!r}")
    if t.count(old) != 1:
        raise SystemExit(f"MUTATION ANCHOR NOT UNIQUE ({t.count(old)}x): "
                         f"{old[:70]!r}")
    f.write_text(t.replace(old, new), encoding="utf-8")


MUTATIONS = [
    # (label, old, new, reviewer_said_already_caught)
    ("NEW: target_return > -> >=",
     "bull = np.where(np.isfinite(forward_high), (forward_high > entry * (1.0 + target_return)).astype(float), np.nan)",
     "bull = np.where(np.isfinite(forward_high), (forward_high >= entry * (1.0 + target_return)).astype(float), np.nan)",
     False),
    ("NEW: drop per-stock cluster boundary",
     "if i == len(out) or codes[i] != codes[start]:",
     "if i == len(out):",
     False),
    ("NEW: cooldown >= -> >",
     "if last is None or (positions[j] - last) >= cooldown:",
     "if last is None or (positions[j] - last) > cooldown:",
     False),
    ("NEW: Wilson upper = constant 0.80",
     "return float(max(0.0, centre - half)), float(min(1.0, centre + half))",
     "return float(max(0.0, centre - half)), 0.80",
     False),
    ("OLD: 4x path > -> >=",
     "bull = np.where(np.isfinite(forward_high), (forward_high > target).astype(float), np.nan)",
     "bull = np.where(np.isfinite(forward_high), (forward_high >= target).astype(float), np.nan)",
     True),
    ("OLD: censoring mask removed",
     "    for arr in (bull, strict_low, joint):\n        arr[~resolved] = np.nan",
     "    pass",
     True),
    ("OLD: strict-low >= -> >",
     "np.isfinite(gate_low), (gate_low >= strict_low_ratio * entry).astype(float), np.nan",
     "np.isfinite(gate_low), (gate_low > strict_low_ratio * entry).astype(float), np.nan",
     True),
    ("OLD: entry is same-bar close",
     "out[\"entry_open\"] = entry",
     "out[\"entry_open\"] = out[\"close\"]",
     True),
]

print("copying ...")
copy_repo()
rc, out = run_tests()
print(f"baseline: exit={rc}  {out.strip().splitlines()[-1]}")
if rc != 0:
    print("BASELINE NOT GREEN -- abort")
    sys.exit(1)

print()
print(f"{'mutation':<40}{'exit':>5}  verdict")
print("-" * 62)
killed = survived = 0
for label, old, new, was_caught in MUTATIONS:
    copy_repo()
    mutate(old, new)
    rc, out = run_tests()
    if rc != 0:
        v, killed = "KILLED", killed + 1
    else:
        exp = "(regression! was caught before)" if was_caught else "(NEW TEST FAILED)"
        v, survived = f"SURVIVED {exp}", survived + 1
    print(f"{label:<40}{rc:>5}  {v}")

print("-" * 62)
print(f"{killed}/{killed+survived} mutations killed")
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(0 if survived == 0 else 1)
