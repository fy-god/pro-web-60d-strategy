# Review response: the 2026-09-17 external audit

An external review (`docs/reviews/2026-09-17_ML_update_review.md`) audited commit
`c97de8c` and raised two P0 findings plus several P1s. This document records what
was verified, what was fixed, and what the corrected numbers are. Every claim
below was reproduced locally before being accepted.

## Summary

Five findings were confirmed and fixed. Two were substantive enough to change
published figures. The review's central P0 — that the precision frontier does not
prove 70% is unreachable in general — is **correct and the claim is withdrawn**.

| # | Finding | Verdict | Effect |
| --- | --- | --- | --- |
| P0-1 | Frontier bounds only one model's ranking, not all models | **Confirmed** | Claim withdrawn; scope now stated in code and docs |
| P0-2 | Final holdout leaked: training labels crossed the cutoff | **Confirmed** | 12.14% → 11.05% before other fixes |
| P1-3 | Label layer compared against a float32 entry price | **Confirmed** | Boundary rows flipped; now compares raw prices |
| P1-4 | `iloc[::stride]` sampling phase depends on other stocks | **Confirmed** | Rebuilt matrix; holdout improved to 13.61% |
| P1-5 | Tie-split prefixes are not realisable scalar thresholds | **Confirmed** | Tie-aware frontier; no numeric change (scores near-continuous) |
| P1-6 | Still a 10-session bull target, not the 504-session low-zone task | **Accepted, not fixed** | Out of scope for this commit; see "Not done" |

---

## P0-1: the "mathematical ceiling" was overstated

**The review is right.** `precision_ceiling.py` fits one HGB model, takes its
out-of-sample scores, and computes the best precision over prefixes of *that*
ranking. The printed conclusion said "No threshold, model or hyperparameter
choice can exceed the oracle rows above", which does not follow. A different
feature set produces a different ordering with a different frontier.

The review's counterexample is valid and minimal: with the same 10 labels and 2
positives, an ordering placing both positives first reaches 100% at k=2, while an
ordering placing them last reaches 20%. Nothing about ordering A constrains
ordering B.

**Fixed.** The module docstring, the printed output, and the JSON now state the
scope explicitly. What survives is the arithmetic, which needs no model:

```
PPV = pi*r / (pi*r + (1-pi)*f)        f <= pi*r*(1-p*) / ((1-pi)*p*)
```

These are identities describing what false-positive rate a 70% target *demands*
(0.18% at 10% recall, against a 95.9%-negative population). They do not bound
what any model can achieve. Establishing 70% is unreachable in general would
require bounding the achievable ROC corner over all feature sets, which this
project does not do.

**The honest statement now:** across the 82-feature set, four model families, 58
hyperparameter configurations, nine feature-group ablations and a cross-sectional
ranking experiment, the best out-of-sample precision observed at a useful signal
count is ~27%, and the 2026 holdout gives 13.61%. 70% was not reached and no
configuration came close, but that is an empirical result over a finite search,
not a proof.

## P0-2: the final holdout leaked

**Confirmed, and it was a real defect.** The code did:

```python
train = frame[frame["date"] < cutoff]
```

A row's label looks forward 10 sessions, so the last 10 pre-cutoff sessions carry
labels whose outcome window extends into the holdout. Training on them leaks
holdout prices into the fitted model. This file explicitly claimed to be the one
clean out-of-sample measurement, so the defect mattered.

Measured impact on the stride-5 grid: **6,333 of 434,383 training rows (1.46%)**
were in the leak zone and all were being fitted on.

**Fixed** with `purge_by_label_end()`, which removes the last `horizon` distinct
**market sessions** before the cutoff — in sessions, not rows, so the boundary is
correct regardless of how many stocks traded on a day or how the matrix was
resampled. A runtime assertion recomputes the last reachable label-end session and
fails loudly if it is not strictly before the cutoff.

Also accepted: the review's point that "the script runs once" does not mean the
2026 period was never observed by the project. Other analyses in this repository
(rule backtests, charts, expectancy tables) already covered 2026. The holdout is
therefore relabelled **`historical_holdout_with_prior_project_exposure`** in the
report, and is no longer described as pristine.

## P1-3: float32 entry price in label arithmetic

**Confirmed.** `entry_open` was stored float32, then read back as float64 for the
close-label comparison. Casting back does not restore precision: `float32(9.99)`
is `9.989999771118164`.

Verified with the review's exact numbers (entry 9.99, close 39.96, strict 4x):

| | Result |
| --- | --- |
| Old: `close / float64(float32(entry)) > 4` | **True** (wrong) |
| New: `close > entry * 4` | **False** (correct — exactly equal, strict `>` fails) |

**Fixed** by keeping a full-precision `entry_f64` for all label arithmetic and
comparing raw prices (`future_max > entry * (1 + target)`) instead of dividing.
The `EPS` fudge in the denominator is gone: it silently shifted every boundary to
guard against a zero entry price. A finite non-positive entry is now reported, and
genuinely missing entries (the final bar of each stock) are counted separately —
a first version of that check used `~(entry > 0)`, which is True for NaN and
therefore reported 3,193 "bad" rows that were simply the end of each series.

## P1-4: stride sampling was phase-dependent

**Confirmed.** `iloc[::stride]` on a stock-concatenated frame means each stock's
sampling phase is determined by how many rows preceding stocks contributed.
Reproduced exactly (`scripts/scratch/check_stride_phase.py`): stock A sampled on
`[01-01, 01-06]` became `[01-05, 01-10]` after an unrelated stock gained a single
row, with A's own prices untouched.

This also weakened the cross-sectional result: if stocks are sampled on different
phases, "top-1 per day" selects from whatever subset happened to be retained that
day, not from the day's full cross-section.

**Fixed** in two steps. First the rule became a global session grid
(`sessions[::stride]`), verified phase-stable. But that exposed a second problem:
session striding keeps only 178 of 887 sessions, which is below the 150-session
warm-up, so **the walk-forward could not be built at all**. Rather than lower the
warm-up to fit the sampling, the harness now runs on the **full session grid**
(`stride=1`, 2,680,715 rows, 887 sessions). The stride-5 matrix was an
optimisation that cost more validity than it saved.

## P1-5: tie-split prefixes are not reachable thresholds

**Confirmed as a correctness issue.** `score >= t` always selects whole groups of
equal scores, so a prefix that cuts inside a tie group is a property of the
ranking, not an operating point any threshold realises. The review's
counterexample (ten samples at 0.5, first two positive → reported 100% at k=2
where the only non-empty scalar threshold gives 20%) is valid.

**Fixed.** The frontier now carries `is_scalar_threshold`, true only where the cut
falls on a score boundary, and all reported bounds are restricted to realisable
cuts. On this data the HGB scores are effectively continuous, so the rejected
count is small and no headline number moved — but the reported frontier no longer
asserts reachability it cannot support.

---

## Corrected numbers

All figures below are from the full session grid with the purge, the float64
labels and the realisable-threshold frontier applied.

> The base rate in this table is the **ML walk-forward fold** population (the
> training/holdout split produced by `src/ml/*`) — it is not either of the two
> base rates published under `reports/`. `reports/webpro_baselines.json` gives
> 3.0348% for the same `webpro` contract on the scanned grid and
> `reports/lowzone_baselines.json` gives 3.0893% on the full resolved panel; all
> three are different row sets. Do not carry a lift across them. Every base-rate
> payload now names its population.

| Quantity | Before | **After** |
| --- | ---: | ---: |
| 2026 holdout precision | 12.14% | **13.61%** |
| 2026 holdout signals | 1,614 | **6,202** |
| 2026 holdout hits | 196 | **844** |
| 2026 holdout lift | 4.17× | **4.70×** |
| Holdout date-clustered 95% CI | [8.82%, 16.48%] | **[10.24%, 17.59%]** |
| Holdout distinct stocks / dates | 802 / 146 | **1,194 / 150** |
| Best precision for this model, ≥250 signals | 24.54% | **26.78%** |
| Best precision at recall ≥10% | 13.08% | **14.31%** |
| Out-of-sample base rate | 4.0878% | **4.0894%** |

The holdout **improved** because the phase-stable grid evaluates every session
against the full cross-section instead of a per-stock subsample. The purge, which
removes leakage, was pushing the number *down* (12.14% → 11.05%) while the grid
fix pushed it up; both are correct and both are applied.

The one intermediate figure worth flagging: measured on the stride-5 grid *with*
the purge, precision was **11.05%**. Anyone reproducing the old 12.14% should
expect 11.05% on the old grid and 13.61% on the corrected one.

Net of all fixes the signal remains real: 6,202 signals over 1,194 stocks and 150
distinct dates, 4.70× lift, date-clustered interval excluding the base rate, and
precision *rising* to 14.13% when the busiest date is removed. The null battery
still returns TRUSTWORTHY on the rebuilt matrix — permuted labels 3.11% vs 3.08%
base, noise features 4.06% vs 4.09%, and zero features above 0.68 AUC (the highest
single-feature AUC is 0.675, on `atr14_pct`).

**70% is still not reached.** The best figure anywhere in this project remains
~27% (an oracle over one model's ranking, at 250+ signals) and 13.61% on the only
genuinely out-of-sample block. What has changed is the *claim*: this is now
reported as a finite empirical search, not a mathematical impossibility.

---

## Not done, and why

The review's P1-6 is correct and is **not** addressed here: the ML track predicts
a 10-session +30% move (`label_high`), which is not the same task as the original
"504 sessions, close > 4×, with low ≥ 0.8E before the target". A good short-horizon
result does not transfer to the long-horizon one, and a negative short-horizon
result does not refute the long-horizon task. That re-scoping needs a `TaskSpec`
threaded through build/train/evaluate, explicit feature whitelists instead of the
current blacklist, and physical separation of feature and label tables. It is a
larger change than a defect fix and is left for the next round rather than
half-done here.

Also not adopted: the review's suggested file renames (`fixed_score_frontier.py`)
and its full TaskSpec/ledger architecture. The scope statements and the
realisable-threshold flag capture the correctness value without a rename that
would invalidate every link in the audit trail.

## Reproduce

```powershell
$env:PYTHONPATH='.'
python -m src.ml.build_matrix --stride 1      # full session grid, 2.68M rows
python -m src.ml.precision_ceiling            # scoped frontier
python -m src.ml.final_holdout                # purged, one-shot 2026
python -m src.ml.null_tests                   # harness validation
python scripts/audit_reports.py               # consistency of published numbers
python scripts/scratch/check_stride_phase.py  # the stride counterexample
```
