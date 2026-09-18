"""Do the reviewer's fail-open injections now fail the audit?

An adversarial review named ~18 places where a present-but-empty payload makes a
block of checks vanish while the run stays green. Individually fixing 18 guards is
whack-a-mole; the section census is the class-level defence. This runs each
injection the reviewer actually performed against the census and reports whether
the audit's problem count moved off 0.

Each case is a (artifact, path, empty-value) triple. The probe copies the repo,
mutates the copy, runs the audit THERE, and compares. It never touches the tree.
"""
from __future__ import annotations

import io
import json
import pathlib
import shutil
import subprocess
import sys

SRC = pathlib.Path(r"D:\ccc\pro-web-60d-strategy")
WORK = pathlib.Path(r"D:\ccc\pro-web-60d-strategy\.audit_tmp\probe_failopen")


def copy_repo() -> None:
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
    cards = SRC / "data" / "cards_100"
    if cards.exists():
        (WORK / "data").mkdir(parents=True, exist_ok=True)
        shutil.copytree(cards, WORK / "data" / "cards_100")
    for name in ("README.md", "TARGET_70PCT.md", "RESULTS.md", "cordis.yml",
                 "requirements.txt", "REPRODUCIBILITY.md", ".gitignore"):
        s = SRC / name
        if s.exists():
            shutil.copy2(s, WORK / name)


def run() -> tuple[int, int]:
    p = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                       cwd=WORK, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    n_prob = None
    for line in out.splitlines():
        if "checks run," in line:
            try:
                n_prob = int(line.split(",")[1].split("problem")[0].strip())
            except (IndexError, ValueError):
                pass
    if n_prob is None:
        return (p.returncode, -1)         # -1 == crashed before reporting
    return (p.returncode, n_prob)


def set_path(rel: str, path: list[str], value) -> None:
    f = WORK / rel
    d = json.load(io.open(f, encoding="utf-8"))
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    io.open(f, "w", encoding="utf-8").write(
        json.dumps(d, indent=2, ensure_ascii=False))


def set_matched_budget_empty() -> None:
    """The real location: results.fam_hgb_0.matched_budget, not top level."""
    f = WORK / "reports/ml_crosssec_final.json"
    d = json.load(io.open(f, encoding="utf-8"))
    d["results"]["fam_hgb_0"]["matched_budget"] = {}
    io.open(f, "w", encoding="utf-8").write(
        json.dumps(d, indent=2, ensure_ascii=False))


def empty_whole_json(rel: str) -> None:
    io.open(WORK / rel, "w", encoding="utf-8").write("{}\n")


CASES: list[tuple[str, str, list[str], object]] = [
    ("tradeability: worst_by_unfillable=[]", "reports/tradeability.json",
     ["worst_by_unfillable"], []),
    ("concentration: holdout=null", "reports/ml_concentration.json",
     ["holdout"], None),
    ("ceiling: practical_ceiling_by_min_signals={}",
     "reports/ml_precision_ceiling.json",
     ["practical_ceiling_by_min_signals"], {}),
    ("null_tests: permuted_labels={}", "reports/ml_null_tests.json",
     ["permuted_labels"], {}),
    ("null_tests: noise_features={}", "reports/ml_null_tests.json",
     ["noise_features"], {}),
    ("wide: ranked[5:] lose per_fold fields",
     "reports/ml_search_wide.json", ["__CUSTOM_RANKED__"], None),
    ("tradeability: entry has no signals",
     "reports/tradeability.json", ["__CUSTOM_NOSIG__"], None),
]

CUSTOM = {
    "__CUSTOM_RANKED__": None,
    "__CUSTOM_NOSIG__": None,
}


def apply_custom(rel: str, marker: str) -> None:
    f = WORK / rel
    d = json.load(io.open(f, encoding="utf-8"))
    if marker == "__CUSTOM_RANKED__":
        # The reviewer's injection: strip the per-fold fields from every ranked
        # entry past the fifth. Only the first 5 are schema-validated.
        for entry in d["ranked"][5:]:
            entry.pop("per_fold_signals", None)
            entry.pop("per_fold_oos", None)
    elif marker == "__CUSTOM_NOSIG__":
        # The reviewer's injection for line 1263: an entry with no `signals`.
        which = "leader_momentum" if "leader_momentum" in d else "worst_by_unfillable"
        if which == "leader_momentum":
            d["leader_momentum"].pop("signals", None)
            d["leader_momentum"]["signals"] = 0
        else:
            d["worst_by_unfillable"][0]["signals"] = 0
    io.open(f, "w", encoding="utf-8").write(
        json.dumps(d, indent=2, ensure_ascii=False))

WHOLE_FILE = [
    ("whole file {}: causality_audit.json", "outputs/ml/audit/causality_audit.json"),
    ("whole file {}: leakage_audit.json", "outputs/ml/audit/leakage_audit.json"),
    ("whole file {}: null_ceiling.json", "outputs/ml/audit/null_ceiling.json"),
    ("whole file {}: feature_auc_scan.json",
     "outputs/ml/audit/feature_auc_scan.json"),
    ("whole file {}: selection_ceiling.json",
     "outputs/ml/audit/selection_ceiling.json"),
]

print("copying the repository ...")
copy_repo()
base_rc, base_prob = run()
print(f"baseline on the copy: exit={base_rc} problems={base_prob}\n")
if base_prob != 0:
    print("BASELINE IS NOT CLEAN -- the probe's copy is unfaithful, stop here.")
    sys.exit(1)

print(f"{'injection':<52}{'exit':>5}{'probs':>7}  verdict")
print("-" * 78)
caught = missed = crashed = 0
for label, rel, path, value in CASES:
    copy_repo()
    if path and path[0] in CUSTOM:
        apply_custom(rel, path[0])
    else:
        set_path(rel, path, value)
    rc, prob = run()
    if prob == -1:
        v, crashed = "CRASHED (fail-closed)", crashed + 1
    elif prob > 0:
        v, caught = "CAUGHT", caught + 1
    else:
        v, missed = "MISSED (still 0 problems)", missed + 1
    print(f"{label:<52}{rc:>5}{prob:>7}  {v}")

# The real matched_budget location, which my first version of this probe got
# wrong (it is nested under results.fam_hgb_0, so the top-level injection was a
# no-op and the MISS was the probe's fault, not the audit's).
copy_repo()
set_matched_budget_empty()
rc, prob = run()
if prob == -1:
    v, crashed = "CRASHED (fail-closed)", crashed + 1
elif prob > 0:
    v, caught = "CAUGHT", caught + 1
else:
    v, missed = "MISSED (still 0 problems)", missed + 1
print(f"{'crosssec: results.fam_hgb_0.matched_budget={}':<52}{rc:>5}{prob:>7}  {v}")

for label, rel in WHOLE_FILE:
    copy_repo()
    empty_whole_json(rel)
    rc, prob = run()
    if prob == -1:
        v, crashed = "CRASHED (fail-closed)", crashed + 1
    elif prob > 0:
        v, caught = "CAUGHT", caught + 1
    else:
        v, missed = "MISSED (still 0 problems)", missed + 1
    print(f"{label:<52}{rc:>5}{prob:>7}  {v}")

print("-" * 78)
tot = caught + missed + crashed
print(f"{caught}/{tot} caught, {crashed} crashed-closed, {missed} missed")
shutil.rmtree(WORK, ignore_errors=True)
print("RESULT:", "ALL FAIL-OPENS CLOSED" if missed == 0
      else f"{missed} STILL FAIL-OPEN")
sys.exit(0 if missed == 0 else 1)
