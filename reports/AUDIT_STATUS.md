# Report audit status

_Written automatically every four hours by `scripts/scheduled_report_audit.py`. Do not edit by hand._

| | |
|---|---|
| Last run (local) | 2026-09-18 13:22:12 |
| Verdict | **ATTENTION** |
| Consistency check | exit code 1 |
| Checks | 373 checks run, 2 problem(s) |
| Remote drift | 0 path(s) differ from origin/main |
| Detail log | `logs/report_audit/audit_2026-09-18_132212.log` (local, not committed) |

## Failures

```
  FAIL  search reports share one grid: median base rate over full-fold configs spans 1.644e-05 ({'ml_search_models.json': 0.040894451, 'ml_search_wide.json': 0.04087800958, 'ml_search_ablation.json': 0.040894451})
  FAIL  ml_search_wide.json records the stride it was measured on
  - search reports share one grid: median base rate over full-fold configs spans 1.644e-05 ({'ml_search_models.json': 0.040894451, 'ml_search_wide.json': 0.04087800958, 'ml_search_ablation.json': 0.040894451})
  - ml_search_wide.json records the stride it was measured on
  - webpro_baselines.json:webpro carries no `population` block yet, so its base rate is not labelled as the 'scanned' population; regenerate to arm this check
  - webpro_baselines.json:low60 carries no `population` block yet, so its base rate is not labelled as the 'scanned' population; regenerate to arm this check
  - webpro_baselines.json:low504 carries no `population` block yet, so its base rate is not labelled as the 'scanned' population; regenerate to arm this check
  - lowzone_baselines.json:webpro carries no `population` block yet, so its base rate is not labelled as the 'panel' population; regenerate to arm this check
  - lowzone_baselines.json:low60 carries no `population` block yet, so its base rate is not labelled as the 'panel' population; regenerate to arm this check
  - lowzone_baselines.json:low504 carries no `population` block yet, so its base rate is not labelled as the 'panel' population; regenerate to arm this check
  - ml_search_models.json has no `stride` field but is stride-1 (median full-fold base=0.04089445); regenerate to stamp it
  - ml_search_ablation.json has no `stride` field but is stride-1 (median full-fold base=0.04089445); regenerate to stamp it
  - ml_crosssec_final.json has no `stride` field but is stride-5 (n_rows=281,227, base=0.04087801); regenerate to stamp it
  - ml_crosssec_hgb0.json has no `stride` field but is stride-5 (same run as ml_crosssec_final); regenerate to stamp it
  - ml_null_tests.json has no `stride` field but is stride-1 (n_rows=2,680,715 = the dense matrix); regenerate to stamp it
  - reports/lowzone_baselines.json is published but no check reads it
  - reports/ml_crosssec_final.json is published but no check reads it
  - reports/ml_crosssec_hgb0.json is published but no check reads it
  - reports/ml_null_tests.json is published but no check reads it
  - reports/ml_precision_frontier_insample.csv is published but no check reads it
  - reports/ml_precision_frontier_oos.csv is published but no check reads it
  - reports/ml_search_ablation.json is published but no check reads it
  - reports/webpro_baselines.json is published but no check reads it
```
