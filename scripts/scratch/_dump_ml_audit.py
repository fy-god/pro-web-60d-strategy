"""What load-bearing values do the four unverified ML artifacts hold?

`causality_audit.json`, `leakage_audit.json`, `null_ceiling.json` and
`feature_auc_scan.json` are the ADVERSARIAL AUDIT 1/4-4/4 leakage/causality
evidence. The audit only asserts they are PRESENT; not one field is compared to
anything. This dumps the values that would matter if they were wrong.
"""
from __future__ import annotations

import io
import json

BASE = "outputs/ml/audit/"


def load(n):
    return json.load(io.open(BASE + n + ".json", encoding="utf-8"))


print("=" * 72)
print("causality_audit.json -- the T_* battery")
c = load("causality_audit")
print(f"  matrix_rows = {c['matrix_rows']}   panel_rows = {c['panel_rows']}")
print("  T_A_beta (production_order_alignment vs unsorted_frame_divergence):")
for k, v in c["T_A_beta"].items():
    print(f"     {k}: {json.dumps(v)[:300]}")
print("  T_A_beta_reconstruction_max_abs_diff:")
for k, v in c["T_A_beta_reconstruction_max_abs_diff"].items():
    print(f"     {k}: {json.dumps(v)[:200]}")
print("  T_B_artifact_vs_source:")
for k, v in c["T_B_artifact_vs_source"].items():
    if k == "worst":
        print(f"     worst: {json.dumps(v)[:300]}")
    else:
        print(f"     {k}: {v}")
print("  T_E_rolling_windows:")
print(f"     verdict: {json.dumps(c['T_E_rolling_windows'].get('verdict'))[:400]}")
print(f"     sites: {len(c['T_E_rolling_windows'].get('sites') or [])} entries, "
      f"first={json.dumps((c['T_E_rolling_windows'].get('sites') or [None])[0])[:220]}")
print(f"  T_D_kdj: rows={c['T_D_kdj'].get('rows_compared')} "
      f"seed50={c['T_D_kdj'].get('first_bar_uses_seed_50')} "
      f"maxdiff={c['T_D_kdj'].get('independent_reimpl_max_abs_diff')}")

print()
print("=" * 72)
print("leakage_audit.json -- the T1-T3 battery")
lk = load("leakage_audit")
print(f"  cutoff={lk['cutoff']} universe_rows={lk['universe_rows']} "
      f"truncated_rows={lk['truncated_rows']} stocks={lk['universe_stocks']}")
print(f"  T1_verdict: {json.dumps(lk['T1_verdict'])}")
print(f"  T1_truncation: {len(lk['T1_truncation'])} entries; "
      f"first={json.dumps(lk['T1_truncation'][0])[:260]}")
worst1 = max(lk["T1_truncation"], key=lambda r: abs(r.get("max_abs_diff") or 0))
print(f"  T1_truncation worst max_abs_diff = {worst1.get('max_abs_diff')} "
      f"({worst1.get('feature')})")
print(f"  T2_alignment: {json.dumps(lk['T2_alignment'])}")
print(f"  T3_max_abs_diff: {json.dumps(lk['T3_max_abs_diff'])}")
print(f"  T3_beta_reconstruction: {len(lk['T3_beta_reconstruction'])} entries")

print()
print("=" * 72)
print("null_ceiling.json -- the chance/lift evidence")
nc = load("null_ceiling")
print("  chance_at_observed_publication:")
for k, v in nc["chance_at_observed_publication"].items():
    print(f"     {k}: {v}")
print("  chance_at_target_2pct_publication:")
for k, v in nc["chance_at_target_2pct_publication"].items():
    print(f"     {k}: {v}")
print("  empirical_null:")
for k, v in nc["empirical_null"].items():
    print(f"     {k}: {v}")
print("  real_baseline:")
for k, v in nc["real_baseline"].items():
    print(f"     {k}: {json.dumps(v)[:200]}")
print("  real_vs_null:")
for k, v in nc["real_vs_null"].items():
    print(f"     {k}: {json.dumps(v)[:300]}")

print()
print("=" * 72)
print("feature_auc_scan.json -- per-feature leakage scan")
fa = load("feature_auc_scan")
print(f"  n_features={fa['n_features']} n_rows={fa['n_rows']} "
      f"base_rate={fa['base_rate']}")
print(f"  flagged_auc_gt_0.75: {fa['flagged_auc_gt_0.75']}")
print(f"  flagged_auc_lt_0.25: {fa['flagged_auc_lt_0.25']}")
print(f"  top25: {len(fa['top25'])} entries; first 3:")
for r in fa["top25"][:3]:
    print(f"     {json.dumps(r)[:200]}")
print("  permutation_null:")
for k, v in fa["permutation_null"].items():
    print(f"     {k}: {json.dumps(v)[:200]}")
print(f"  note: {fa['note'][:200]}")
