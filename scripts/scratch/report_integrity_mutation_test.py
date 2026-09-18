"""Throwaway: mutation test - does report_integrity_extra.py actually catch errors?"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "scripts/scratch/report_integrity_extra.py"

MUTATIONS = [
    ("A", "tradeability.json", lambda d: d["overall"].__setitem__(
        "tradeable_signals", d["overall"]["tradeable_signals"] + 7)),
    ("A", "tradeability.json", lambda d: d["overall"].__setitem__(
        "unfillable", d["overall"]["unfillable"] + 5)),
    ("A", "ml_precision_ceiling.json", lambda d: d["requirement_70pct"].__setitem__(
        "recall_0.5", d["requirement_70pct"]["recall_0.5"] * 1.5)),
    ("A", "ml_precision_ceiling.json", lambda d: d.__setitem__(
        "practical_ceiling_250plus_raw", 0.99)),
    ("A", "ml_concentration.json", lambda d: d.__setitem__(
        "walkforward_total_signals", d["walkforward_total_signals"] + 3)),
    ("A", "ml_concentration.json", lambda d: d.__setitem__(
        "walkforward_largest_fold_share", 0.5)),
    ("A", "ml_null_tests.json", lambda d: d["permuted_labels"].__setitem__(
        "mean_precision", 0.99)),
    ("A", "ml_search_models.json", lambda d: d["ranked"][0].__setitem__(
        "per_fold_base", [0.03, 0.08, 0.026, 0.028])),
    ("A", "ml_search_models.json", lambda d: d.__setitem__("n_configs", 9)),
    ("A", "hitrate_vs_expectancy.json", lambda d: d.__setitem__(
        "spearman_hit_rate_vs_net_expectancy", 0.5)),
    ("A", "hitrate_vs_expectancy.json", lambda d: d.__setitem__(
        "positive_expectancy_count", 99)),
    ("A", "webpro_cards_100_reproduction.csv", "csv_tp"),
]


def run_with(reports_dir: Path) -> list[tuple[str, str]]:
    spec = importlib.util.spec_from_file_location("extra_check", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.REPORTS = reports_dir
    mod.ROWS.clear()
    mod.NOTES.clear()
    for fn in (mod.check_ceiling_requirement, mod.check_concentration,
               mod.check_search_failures_and_fold_bases, mod.check_null_test_summaries,
               mod.check_tradeability_overall, mod.check_tradeable_subset,
               mod.check_live_readiness_cost, mod.check_hitrate_correlations,
               mod.check_cards, mod.check_baseline_agreement,
               mod.check_frontier_identity, mod.check_signal_count_bases):
        fn()
    return [(r[0], r[1]) for r in mod.ROWS]


print("=== baseline (unmutated copy)")
with tempfile.TemporaryDirectory() as td:
    clean = Path(td) / "reports"
    shutil.copytree(REPO / "reports", clean)
    base = run_with(clean)
    print(f"  findings on the unmutated copy: {len(base)}")
    for sev, where in base:
        print(f"    [{sev}] {where}")

print("\n=== mutation test")
caught = 0
for sev_expect, fname, mut in MUTATIONS:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "reports"
        shutil.copytree(REPO / "reports", tmp)
        target = tmp / fname
        if fname.endswith(".json"):
            d = json.loads(target.read_text(encoding="utf-8"))
            mut(d)
            target.write_text(json.dumps(d, indent=2), encoding="utf-8")
            label = fname
        else:
            lines = target.read_text(encoding="utf-8").splitlines()
            hdr = lines[0].split(",")
            i = hdr.index("tp")
            f = lines[1].split(",")
            f[i] = str(int(f[i]) + 5)
            lines[1] = ",".join(f)
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
            label = fname + " (tp+5)"
        found = run_with(tmp)
        new = [x for x in found if x not in base]
        if new:
            caught += 1
            print(f"  CAUGHT  {label}: {new[0][0]} - {new[0][1][:95]}")
        else:
            print(f"  MISSED  {label}  <-- checker has a blind spot")

print(f"\n{caught}/{len(MUTATIONS)} mutations caught")
