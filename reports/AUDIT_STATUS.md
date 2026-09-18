# Report audit status

_Written automatically every four hours by `scripts/scheduled_report_audit.py`. Do not edit by hand._

| | |
|---|---|
| Last run (local) | 2026-09-18 09:22:02 |
| Verdict | **ATTENTION** |
| Consistency check | exit code 1 |
| Checks | 132 checks run, 1 problem(s) |
| Remote drift | 0 path(s) differ from origin/main |
| Detail log | `logs/report_audit/audit_2026-09-18_092202.log` (local, not committed) |

## Failures

```
  FAIL  search reports share one grid: median base rate over full-fold configs spans 1.644e-05 ({'ml_search_models.json': 0.040894451, 'ml_search_wide.json': 0.04087800958, 'ml_search_ablation.json': 0.040894451})
  - search reports share one grid: median base rate over full-fold configs spans 1.644e-05 ({'ml_search_models.json': 0.040894451, 'ml_search_wide.json': 0.04087800958, 'ml_search_ablation.json': 0.040894451})
```
