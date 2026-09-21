# Report audit status

_Written automatically every four hours by `scripts/scheduled_report_audit.py`. Do not edit by hand._

| | |
|---|---|
| Last run (local) | 2026-09-22 03:15:01 |
| Verdict | **PASS** |
| Consistency check | exit code 0 |
| Checks | 629 checks run, 0 problem(s) |
| Remote drift | 3 path(s) differ from origin/main |
| Detail log | `logs/report_audit/audit_2026-09-22_031501.log` (local, not committed) |

## Remote drift

3 path(s) differ from origin/main:

- `RESEARCH_QUICKSTART.md`
- `docs/audits/expert-ml/2026-09-22_03-49-55_JST.md`
- `docs/audits/expert-ml/LATEST.md`

## Headline

- holdout precision **13.61%** against a base rate of 2.90% (4.70x lift)
- 6,202 signals, 844 hits

All consistency checks passed.

## Known gaps (12)

_Reported, not failures._

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
- reports/ml_crosssec_hgb0.json is opened only for its provenance fields (stride); no number in it is verified
