"""Reproduce the automation reviewer's five fail-open mutations and require a FAIL.

The reviewer showed the audit could go GREEN after these five mutations, because
every dependent check is written `if not report: continue` / `if not rows:
continue` and a present-but-wrong payload is falsy or empty. Each mutation is
applied to a byte-for-byte backup, the audit run, the guard asserted, and the file
restored. The audit must never return exit 0 with the mutation in place.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(".")
RESULTS = []


def run_audit():
    r = subprocess.run([sys.executable, "scripts/audit_reports.py"],
                       capture_output=True, text=True, cwd=REPO)
    out = r.stdout + r.stderr
    tail = [ln.strip() for ln in out.splitlines() if "checks run" in ln]
    nprob = None
    for ln in out.splitlines():
        m = re.search(r"(\d+) problem\(s\)", ln)
        if m:
            nprob = int(m.group(1))
    return r.returncode, out, (tail[-1] if tail else "?"), (nprob or 0)


def probe(label, path, new_text, baseline_problems):
    p = REPO / path
    orig = p.read_bytes()
    p.write_text(new_text, encoding="utf-8")
    try:
        code, out, summary, nprob = run_audit()
        # The run legitimately has unrelated failures (the wide regeneration), so
        # "exit != 0" alone proves nothing -- the first version of this probe
        # marked every mutation CAUGHT for exactly that reason. A mutation counts
        # only if it ADDS a problem or produces a failure naming the artifact.
        added = nprob - baseline_problems
        snippet = path.split("/")[-1]
        named = [ln.strip() for ln in out.splitlines()
                 if ln.strip().startswith(("FAIL", "-")) and snippet in ln]
        caught = added > 0 or bool(named)
        print(f"  {'CAUGHT' if caught else 'MISSED'} {label}")
        print(f"        exit={code}  {summary}  problems {baseline_problems} -> "
              f"{nprob} (+{added})")
        for f in named[:2]:
            print(f"        {f}")
        RESULTS.append((label, caught))
    finally:
        p.write_bytes(orig)
        assert p.read_bytes() == orig, f"{path} not restored byte-for-byte"


print("=" * 78)
print("reviewer's fail-open mutations")
print("=" * 78)
_, _, base_summary, base_problems = run_audit()
print(f"baseline: {base_summary}, {base_problems} problem(s)\n")

# 1. CSV truncated to its header -- dropped 20 checks including recall floors.
p = REPO / "reports/ml_precision_frontier_oos.csv"
header = p.read_text(encoding="utf-8").splitlines()[0] + "\n"
probe("ml_precision_frontier_oos.csv truncated to header",
      "reports/ml_precision_frontier_oos.csv", header, base_problems)

# 2. JSON replaced with an empty list.
probe("ml_concentration.json replaced by []",
      "reports/ml_concentration.json", "[]\n", base_problems)

# 3. JSON replaced with an empty object.
probe("tradeability.json replaced by {}",
      "reports/tradeability.json", "{}\n", base_problems)

# 4. JSON replaced with a bare string (used to crash with AttributeError).
probe('ml_precision_ceiling.json replaced by "x"',
      "reports/ml_precision_ceiling.json", '"x"\n', base_problems)

# 5. Search report stripped of the sub-fields 82 pooling checks read.
p = REPO / "reports/ml_search_models.json"
d = json.loads(p.read_text(encoding="utf-8"))
for row in d.get("ranked") or []:
    row.pop("per_fold_signals", None)
    row.pop("per_fold_oos", None)
probe("ml_search_models.json loses per_fold_signals/per_fold_oos",
      "reports/ml_search_models.json", json.dumps(d, indent=2), base_problems)

# 6. The lowzone CSV with its key column renamed (the vacuous except branch).
p = REPO / "reports/lowzone_hit_rates.csv"
t = p.read_text(encoding="utf-8").replace("bull_precision", "bull_precisionX", 1)
probe("lowzone_hit_rates.csv loses bull_precision",
      "reports/lowzone_hit_rates.csv", t, base_problems)

# 7. scan summary emptied.
probe("webpro_scan_summary.json replaced by {}",
      "reports/webpro_scan_summary.json", "{}\n", base_problems)

print()
bad = [lbl for lbl, ok in RESULTS if not ok]
print(f"caught {sum(1 for _, ok in RESULTS if ok)} of {len(RESULTS)}")
for lbl in bad:
    print(f"  STILL OPEN: {lbl}")
print("\nRESULT:", "PASS -- every fail-open path is closed" if not bad
      else "ATTENTION REQUIRED")
raise SystemExit(0 if not bad else 1)
