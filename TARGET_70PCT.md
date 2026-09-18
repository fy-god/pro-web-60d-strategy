# Can the 70% target be reached?

**Short answer: no configuration reached it, and the reason is now measured —
but an earlier version of this document overstated what was proven. That
overstatement is corrected here.**

The requested target was "tune it to 70%, and don't report back below 60%." An
external review (`docs/reviews/2026-09-17_ML_update_review.md`) correctly showed
that my earlier claim — that a computed "ceiling" proved 70% is mathematically
unreachable — did not follow from the computation. The frontier I measured bounds
the threshold choice on **one fitted model's ranking**, not the achievable
performance of all models. That claim is **withdrawn**.

What remains is an empirical result over a large but finite search: 82 features,
four model families, 58 hyperparameter configurations, nine feature-group
ablations, a cross-sectional ranking experiment — and no configuration came close
to 70%. The best out-of-sample precision observed at a useful signal count is
~27%, and the one genuinely out-of-sample block gives **13.61%**.

Full account of the review findings and their fixes: `docs/REVIEW_RESPONSE.md`.

> **Which population the base rates in this document come from.** There are three
> distinct base rates in this repository and they are not interchangeable:
>
> | Where | Population | `webpro` base rate |
> | --- | --- | ---: |
> | `reports/webpro_baselines.json` | scanned grid (stride 5, `_seq >= 60`) | 3.0348% |
> | `reports/lowzone_baselines.json` | full resolved panel (no stride, no min-history) | 3.0893% |
> | **this document** | **ML walk-forward folds** (train/holdout split, per-fold rates) | **4.09%** pooled, **2.8958%** on the 2026 holdout |
>
> The §1 arithmetic uses π = 4.09% and the holdout table below uses 2.8958%; both
> are fold populations, produced by `src/ml/*`, and neither is the whole-panel or
> scanned-grid figure. Nothing in this document should be read as a lift against
> either of the two `reports/` base rates. See §5 of the README for the other two.

---

## 1. The arithmetic that decides the difficulty

This part needs no model and is not affected by the correction above. Precision at
a threshold is not a free parameter. For base rate π, recall *r* and
false-positive rate *f*:

```
PPV = πr / (πr + (1-π)f)
```

Requiring `PPV >= 0.70` forces

```
f <= πr(1-p*) / ((1-π)p*)
```

With π = 4.09% (the measured out-of-sample base rate of the walk-forward folds)
the permitted false-positive rate is:

| Recall required | Permitted false-positive rate |
| ---: | ---: |
| 50% | 0.913% |
| 30% | 0.548% |
| 20% | 0.365% |
| 10% | 0.183% |
| 5% | 0.091% |
| 1% | 0.018% |

To publish at 70% precision while catching even 10% of real events, the model may
mis-fire on only **0.18% of the 95.9% of rows that are negative**. That is a
ROC corner this problem does not have.

---

## 2. What the frontier actually measures — and its scope

`src/ml/precision_ceiling.py` fits the standard model on each purged walk-forward
fold and then computes, **on the true out-of-sample labels**, the best precision
achievable at any threshold **on that model's ranking**. Because it uses the true
labels, no *threshold choice* can beat it.

**Scope, stated precisely because an earlier version got this wrong.** This is the
best prefix of one fitted model's ordering. It is **not** a bound on all models,
all feature sets, or all algorithms. A different feature set produces a different
ordering, and a different ordering has a different frontier. The minimal
counterexample: with the same 10 labels and 2 positives, an ordering that puts
both positives first reaches 100% at k=2, while one that puts them last reaches
20%. Ordering A constrains nothing about ordering B.

So this section answers "how good is this model at its best operating point", not
"what is achievable in principle". The distinction is the difference between an
empirical result and a proof, and only the former is on offer.

Out-of-sample, full session grid: 1,406,181 rows, 57,505 positives, base rate
4.0894%.

Because raw probabilities from separately-fitted fold models are not on a common
scale, the figure is computed twice: once pooling raw scores, once ranking scores
within each fold. The rank-normalised column is the fairer of the two. Bounds are
restricted to cuts a scalar threshold can realise — a prefix that splits a group
of equal scores is a property of the ranking, not an operating point.

| Minimum signals | Max precision (pooled raw) | Max precision (per-fold rank) |
| ---: | ---: | ---: |
| 250 | 26.78% | 28.64% |
| 1,000 | 23.57% | 26.67% |
| 2,000 | 22.35% | 24.10% |
| 5,000 | 18.55% | 19.58% |
| 10,000 | 16.66% | 17.51% |

And by required recall (realisable threshold cuts only):

| Recall floor | Max precision available | Signals published |
| ---: | ---: | ---: |
| ≥ 50% | 11.46% | 43,989 |
| ≥ 30% | 13.42% | 23,834 |
| ≥ 20% | 14.15% | 15,436 |
| ≥ 10% | 16.64% | 7,493 |
| ≥ 5% | 19.42% | 3,831 |
| ≥ 2% | 28.57% | 735 |

**Best precision for this model at ≥250 signals: 26.78% pooled, 28.64%
rank-normalised.** At a ≥10% recall floor it reaches 16.64%. Those are 2.6× and
4.2× short of 70% respectively.

> **Corrections to this section, in order of discovery.**
>
> 1. An earlier run reported **20.23%**. The sampling grid spanned only 200 points,
>    so it jumped from 1 published row to ~338 and could not represent the
>    small-count region. Densified below 2,000 signals; corrected to 24.54%.
> 2. A later run on the phase-corrected full grid gives **26.78%**. The stride-5
>    matrix that produced 24.54% sampled every fifth session, so each row's
>    features came from a different cross-section than the one being scored.
> 3. **The claim built on these numbers is withdrawn.** I previously wrote that "no
>    amount of feature engineering, hyperparameter search, ensembling or stacking
>    can cross a bound computed from the labels themselves." That does not follow:
>    the bound is computed from one model's *ranking*, and better features would
>    change the ranking. The review that caught this is correct. What can be said
>    is the weaker, defensible thing: across every configuration actually tried,
>    nothing approached 70%.

---

## 3. Why "70%" appeared reachable in the source material

Three mechanisms, none of which requires any bound to be understood:

1. **Publishing almost nothing.** The absolute maximum precision on the frontier is
   **100%** — achieved by publishing a single row that happened to be a hit. The
   source project's headline numbers rest on **5–22 hand-picked yes-predictions**.
   A 100% figure on one row is not a strategy, and 70% on 13 signals is the same
   artifact one order of magnitude up.
2. **Measuring in-sample.** The in-sample frontier in the same run also reaches
   100%. The standard model scores **49–57% in-sample** on the exact folds where
   it scores **11–18% out-of-sample**. That gap *is* the source project's 70–80%:
   thresholds were tuned on the same 100 cards that were reported.
3. **Selection over many configurations.** Scanning hundreds of configs and
   reporting the maximum buys the spread of the distribution, not skill. The
   search below reports that spread explicitly so the bias is visible.

---

## 4. What the parallel search did find

Full results in `reports/ml_search_wide.json` (58 configurations, 5 workers). The
consistent picture, showing **both** numbers per configuration so the gap is
visible:

| Configuration | In-sample | **Out-of-sample** | Signals | Folds above base |
| --- | ---: | ---: | ---: | ---: |
| ExtraTrees, 0.5% publication | 56.26% | **18.21%** | 368 | 3/4 |
| ExtraTrees, 0.5% publication | 47.05% | **16.50%** | 515 | 3/4 |
| HGB (baseline), 2% publication | 50.60% | **15.98%** | 1,790 | 4/4 |
| ExtraTrees, 2% publication | 40.89% | **15.72%** | 3,913 | 4/4 |
| HGB wide, 2% publication | 68.57% | 15.26% | 996 | 4/4 |
| RF, 2% publication | 42.07% | 14.70% | 3,892 | 4/4 |

Three things stand out.

1. **The best configuration is 18.21% at 368 signals, and it is 3/4 folds — worse
   on consistency than the baseline's 4/4.** It is not a better strategy; it is a
   luckier draw on a smaller sample. The baseline is the more trustworthy result.
2. **The in-sample/OOS gap is 1.2×–5.8×.** The very configuration that reaches
   68.57% in-sample delivers 15.26% out-of-sample (4.5×); the widest ratio in the
   56 ranked configurations is 5.8×, and the narrowest 1.2×. This ratio *is* the
   mechanism behind every published "70%".
3. **The search's top row is a trap.** A configuration scored **33.33%** — on
   **3 signals**. In-sample it was 91.60%. Reporting that as a 33% strategy would
   be the same error as reporting 70% on 13 cases.

Feature-group ablations were also run, with the group table corrected after an
initial bug (prefix matching made seven "different" ablations resolve to the same
ten columns — they are now exact, disjoint sets covering all 82 features, with a
`check_groups` guard).

| Feature set | OOS precision | Signals | Lift |
| --- | ---: | ---: | ---: |
| **all 82 features** (baseline) | 16.44% | 12,143 | 4.02× |
| drop `cross` | **18.53%** | 16,838 | 4.53× |
| drop `momentum` | 17.39% | 13,376 | 4.25× |
| drop `limitup` | 16.59% | 11,497 | 4.06× |
| drop `kdj` | 16.38% | 12,550 | 4.01× |
| drop `candle` | 16.18% | 11,070 | 3.96× |
| drop `volume` | 15.80% | 11,205 | 3.86× |
| drop `position` | 15.07% | 9,832 | 3.69× |
| drop `volatility` | 15.01% | 8,108 | 3.67× |
| drop `market` | 14.89% | 16,798 | 3.64× |

Single groups, alone: `volatility` 15.15% (38,378 signals), `cross` 15.14%
(21,149), `momentum` 13.56% (19,338), `candle` 13.49% (41,436), `limitup` 12.23%
(40,195).

Two conclusions. First, the cross-sectional and raw-volatility families carry the
most standalone information. Second, **the KDJ/expert-style indicator family is
among the weakest** — the opposite of what the original expert library assumed.

> **A finding that did not survive the grid fix.** On the stride-5 matrix,
> dropping the `position` family looked like the best single change anywhere in
> this project (17.10%, lifting all four folds). On the corrected full grid it is
> **15.07% — worse than baseline**. The earlier result was an artifact of sampling
> every fifth session, which put each row's position features on a different
> cross-section than the one being scored. This is exactly why the ablation table
> is regenerated rather than quoted: a plausible, fold-consistent improvement
> turned out to be a property of the bug. The current best single change is
> dropping `cross` (18.53%), and the strongest model overall is Random Forest at
> 20.84%.

---

## 5. Cross-sectional selection — and why 23.81% is not better than 15.98%

An independent agent tested per-session top-K selection (ranking stocks against
each other within each day) rather than a global probability threshold. Its
headline numbers look much better than the baseline:

| Rule | Signals | OOS precision | Date-clustered 95% CI |
| --- | ---: | ---: | --- |
| Top-1 per session | 462 | **23.81%** | [20.13%, 27.71%] |
| Top-3 per session | 1,386 | 19.41% | [17.24%, 21.65%] |
| Top-5 per session | 2,310 | 17.97% | [16.23%, 19.74%] |
| Top-10 per session | 4,620 | 15.45% | — |
| Global threshold (baseline) | 1,790 | 15.98% | — |

Every interval excludes the 4.09% base rate, and the top-1 result is robust: 462
signals on exactly 462 distinct dates, 365 distinct stocks, HHI 0.0022, and
dropping the busiest date moves precision to 23.86%. The within-day ranking is
genuinely informative (mean per-fold pooled AUC 0.699 across the four folds:
0.783 / 0.563 / 0.721 / 0.729; mean within-session AUC 0.725, above 0.5 in 98% of
sessions).

**But it is not an improvement, and the test that shows this is the important
part.** Comparing top-K against an *oracle global threshold allowed to tune itself
on the test block* — an upper bound no global rule can beat — at the same signal
budget:

| K | Top-K precision | Oracle global threshold | Ratio |
| ---: | ---: | ---: | ---: |
| 1 | 23.81% | 23.38% | 1.02 |
| 3 | 19.41% | 20.35% | 0.95 |
| 5 | 17.97% | 18.31% | 0.98 |
| 10 | 15.45% | 15.67% | 0.99 |
| 20 | 13.32% | 13.19% | 1.01 |
| 50 | 10.54% | 10.96% | 0.96 |

Ratios cluster at 1.00 and the paired date-clustered confidence intervals for the
difference all include zero. **Per-session top-K is statistically
indistinguishable from simply tightening a global threshold to the same
strictness.** The apparent gain from 15.98% to 23.81% is entirely an
operating-point effect: top-1 publishes 462 signals where the baseline publishes
1,790.

This is consistent with the §2 frontier: on the current full-session grid the
oracle at a 500-signal floor reaches **26.78%**, and that same 26.78% is the
maximum for every floor from 50 to 500 signals (it is attained at 534 published
rows); top-1 achieves 23.81% at 462, so the model sits *below* its own frontier
rather than beyond it. Any rule that publishes fewer signals will report higher
precision, and that is not skill.

---

## 6. The one-shot 2026 holdout — the only real out-of-sample evidence

`src/ml/final_holdout.py` evaluates **one pre-committed configuration, once**, on
the 160 sessions from 2026-01-01 onward that no other script touches.

Two defects in this entry point were found by review and fixed; both are described
in `docs/REVIEW_RESPONSE.md`.

* **Leakage.** Training was filtered on `date < cutoff` only, but labels look
  forward 10 sessions, so the last 10 pre-cutoff sessions carried labels whose
  outcome window reached into the holdout. On the old grid that was 6,333 rows
  (1.46% of training) and all of them were fitted on. The purge now removes the
  last `horizon` **market sessions** before the cutoff, with a runtime assertion.
* **Exposure.** This is not pristine data. Other analyses in this repository —
  rule backtests, charts, expectancy tables — already covered 2026 before this
  script existed, so it is labelled
  **`historical_holdout_with_prior_project_exposure`** rather than "untouched".

| | Value |
| --- | ---: |
| Purged sessions before cutoff | 10 (removed from training) |
| Holdout sessions | 160 (476,860 usable rows) |
| Threshold (from pre-2026 scores only) | 0.165810 |
| Holdout base rate | 2.8958% |
| Signals published | 6,202 |
| Hits | 844 |
| **Precision** | **13.61%** |
| Lift over base rate | **4.70×** |
| Wilson 95% interval | [12.78%, 14.48%] |
| **Date-clustered 95% interval** | **[10.24%, 17.59%]** |
| Distinct stocks / dates | 1,194 / 150 |
| Date HHI | 0.0264 (≈37.9 effective dates) |
| Precision excluding busiest date | 14.13% (5,781 signals) |

The date-clustered interval **excludes the base rate**, so the effect is real and
not an artifact of clustering — 6,202 signals across 1,194 stocks and 150 distinct
dates, and dropping the single busiest date *raises* precision rather than
destroying it. This is a genuine but modest edge of roughly 4.7× the base rate.

It is also **13.61%, not 70%.**

> **How this number changed.** 12.14% on the old stride-5 grid with no purge →
> **11.05%** with the purge applied (the leak had been inflating it) → **13.61%**
> on the phase-corrected full session grid (the subsample had been evaluating each
> row against a different cross-section than the one scored). The two fixes push
> in opposite directions and both are correct. Anyone reproducing the original
> 12.14% should expect 11.05% on that grid, and 13.61% on the corrected one.

---

## 7. Is the measurement itself trustworthy?

> **Grid provenance for this section.** Every figure below was measured on the
> **stride-5** grid (`outputs/ml/matrix_h10_t30_s5.parquet`, 536,143 rows, of
> which 281,227 fall in the four out-of-sample test blocks). `nulls_audit.json`
> records that matrix explicitly; `null_ceiling.json`, `selection_ceiling.json`,
> `feature_auc_scan.json` and `leakage_audit.json` carry no provenance field but
> their row counts and per-fold test sizes (67,248 / 68,438 / 72,262 / 73,279) are
> the stride-5 fold totals. Sections 5 and 6 use the **dense stride-1** grid
> (2,680,715 rows). Both grids are valid and their base rates differ by 0.04%
> relative (4.0878% stride-5 vs 4.0894% dense), so no conclusion here turns on the
> choice — but a reader comparing this section's 281,227 rows against section 5's
> dense framing should know they are different populations.

Two independent null batteries were run. The larger one
(`outputs/ml/audit/nulls_audit.json`, 2,906 s, 1 real control + 11 null variants +
2 positive controls) destroys the feature–label relationship in eleven different
ways and confirms the harness cannot
manufacture precision where none exists. It also includes two **positive
controls** that prove the harness *can* detect a real signal when one is planted.

| Variant | OOS precision | Base rate | Lift | Folds above base |
| --- | ---: | ---: | ---: | ---: |
| **real (control)** | **15.98%** | 4.09%† | **3.91×**† | **4/4** |
| permuted labels, global (3 seeds) | 2.99–3.32% | ~3.1% | 0.98–1.08× | 1–3/4 |
| permuted within each session | 6.28% | 5.48% | 1.15× | 1/2 |
| i.i.d. Bernoulli labels | 3.38% | 3.06% | 1.10× | 4/4 |
| Gaussian-noise features (2 seeds) | 3.63–4.45% | 4.12% | 0.88–1.08× | 1–2/4 |
| Gaussian features + Bernoulli labels | 3.27% | 3.11% | 1.05× | 4/4 |
| each feature independently row-permuted | 4.04% | 4.12% | 0.98× | 2/4 |
| labels shuffled in TRAIN block only | 4.96% | 4.12% | 1.20× | 3/4 |
| test labels shuffled only | 4.97% | 4.12% | 1.21× | 3/4 |
| **POSITIVE CONTROL: `fwd_max_high` + noise** | **39.05%** | 4.12% | **9.47×** | **4/4** |
| **POSITIVE CONTROL: `label_high` + noise** | **19.42%** | 4.12% | **4.71×** | **4/4** |

† The real control's base rate and lift use the **ratio-of-sums** pooling (total
positives / total test rows, 4.0878%), which the correction blockquote below
establishes as the right one; the null rows and both positive controls below use
the report's per-variant `oos_base_rate` (unweighted mean of per-fold rates,
4.1243% for the real row). The two bases differ by 0.036 pp and the two lifts by
0.04, so the distinction does not change any conclusion — but the two must not be
read as one column. `nulls_audit.json` carries both as `pooled_base_rate` and
`oos_base_rate`.

**Every null collapses to the base rate (lift 0.88–1.21), and both positive
controls fire strongly (9.47× and 4.71× with 4/4 folds).** This is the decisive
validation: the harness detects a planted signal and finds nothing where nothing
was planted. The baseline is therefore measuring a real relationship, not an
artifact of the purge, the folds, the stride sampling or the feature scaling.

Two further results sharpen this. The auditor's chance-ceiling calculation
(`outputs/ml/audit/null_ceiling.json`) puts 2% publication at 5,625 signals on
281,227 rows with a null mean of 4.12% and SD 0.262 pp; the observed baseline
publishes fewer, 1,790 signals, so its null SD is wider at 0.469 pp. Against its
own publication budget the observed 15.98% therefore sits **25 standard
deviations** above chance (against the 2% budget it is 45), and the best of 1,000
null draws on the 2% budget is 5.10%. A date-block bootstrap over 299 distinct
signal dates gives a **95% interval of [13.6%, 18.7%]**. Row-level intervals
would be wrong here (3.2–5.1%) because same-day signals share a 10-session forward
window.

A smaller independent battery (`reports/ml_null_tests.json`) reached the same
conclusion by different means: permuted labels 3.11% vs 3.08% base, noise features
4.06% vs 4.09%, and no feature exceeding AUC 0.68. **Both verdicts:
trustworthy.**

> **Corrections the audit forced, all now applied.** The pooled base rate was
> computed three different ways at three different times, and the first two were
> wrong:
>
> | Pooling of the base rate | Value | Lift reported |
> | --- | ---: | ---: |
> | Unweighted mean of per-fold rates | 4.1243% | 3.87× (original) |
> | Weighted by signal count | 4.4631% | 3.58× (first "fix") |
> | **Total positives / total test rows** | **4.0878%** | **3.91× (correct)** |
>
> The correct pooling is the ratio of sums — the value you would get by
> concatenating every out-of-sample row into one frame — because the folds are
> not the same size (67,248 / 68,438 / 72,262 / 73,279 rows) and the per-fold
> base rates differ threefold (2.67%–8.02%). Averaging is wrong under either
> weighting. As an independent check, the corrected 4.0878% equals
> `outputs/ml/audit/selection_ceiling.json`'s own 11,496 / 281,227 exactly, and
> that figure is produced by a different module that shares only the fold
> definitions — so the two agree not by construction but by agreement about which
> rows are out-of-sample. (`reports/ml_precision_ceiling.json` counts the same
> folds a different way — 57,505 positives over 1,406,181 rows, the full
> un-thinned test blocks rather than the signal-bearing subset — and agrees to
> 0.0016 pp: 4.0894% against 4.0878%.) `summarise()` now reports the exact value
> plus both approximations, so the spread (0.38 pp) is visible rather than hidden.
>
> Second, `label_close` was censored on "saw at least one future bar" instead of
> "has a full 10-bar window", so 5,747 rows at the very end of the panel carried
> a label computed from a partial window. Censoring is now on the full window,
> and the label ratio is compared in float64 to remove 3 rows where a float32
> round-trip flipped the comparison. Neither defect touches `label_high`, and a
> full rebuild confirms `entry_open`, `fwd_max_high`, `label_high`, `resolved`
> and all 82 feature columns are **bit-identical** (max absolute difference
> 0.000e+00).

---

## 8. How much does any single period carry?

A pooled precision can be carried by a handful of observations, so both headline
numbers were stress-tested for concentration (`src/ml/concentration.py`).

**Walk-forward baseline, per fold** (full session grid, 12,143 signals pooled):

| Fold (test window) | Signals | Share | Precision |
| --- | ---: | ---: | ---: |
| 2024-02-02 → 2024-07-29 | 10,173 | 83.8% | 14.56% |
| 2024-07-30 → 2025-01-17 | 1,448 | 11.9% | 24.72% |
| 2025-01-20 → 2025-07-14 | 147 | 1.2% | 21.09% |
| 2025-07-15 → 2025-12-31 | 375 | 3.1% | 33.60% |

Pooled: **16.44%** on 12,143 signals. On the full grid the first fold dominates
even more strongly than it did on the stride-5 grid — 84% of all signals — and it
again has the *lowest* precision of the four. Removing it raises the pooled figure
to **26.14%**.

> A review made a fair procedural objection here: *"deleting the worst fold raises
> the mean — that is arithmetic, not a proof of robustness."* That is correct, and
> the leave-one-fold-out figure should be read as a sensitivity diagnostic, not as
> a better estimate. The all-folds number is the one to quote. What the diagnostic
> legitimately establishes is the *sign* of the bias: fold-to-fold drift is not
> hiding a weaker result, it is diluting a stronger one. The honest caveat is the
> opposite one — fold 1 holds 84% of signals, so this result is much closer to a
> single-period estimate than the phrase "4/4 folds above base" suggests.

**2026 holdout, same treatment:**

| Treatment | Precision | Signals |
| --- | ---: | ---: |
| As published | 13.61% | 6,202 |
| Drop busiest date | 14.13% | 5,781 |
| Drop 3 busiest dates | 15.23% | 5,142 |
| Drop 5 busiest dates | 16.11% | 4,550 |
| Drop 10 busiest dates | 16.20% | 3,538 |
| First half of signal dates | 10.74% | 3,101 |
| Second half of signal dates | 16.48% | 3,101 |

No single date carries it: the busiest date holds 6.8% of signals, and removing it
*raises* precision. Both chronological halves are far above the 2.9% base rate,
and the effect strengthens in the later half. These are the same rows and the same
threshold as the headline figure above, so the two modules agree exactly —
`concentration.py` now reuses `final_holdout.purge_by_label_end` instead of
deriving its own split, which previously left the last ten pre-holdout sessions in
the training set and made the two report the same holdout on different rows.

An earlier revision of this table read 8,352 signals at 12.07% throughout, a run
that predates the purge fix, and the counts were printed to stdout only so nothing
on disk contradicted it. `reports/ml_concentration.json` now records both
`precision` and `signals` per treatment, which is what the counts above are read
from.

---

## 9. What is actually true

- **A real signal exists.** The one-shot 2026 holdout gives **13.61%** precision
  against a 2.90% base rate — a **4.70× lift** on 6,202 signals across 1,194
  stocks and 150 distinct dates, with a date-clustered 95% interval of
  [10.24%, 17.59%] that excludes the base rate. The within-day ranking is also
  real (AUC ≈0.70). This is a genuine, modest edge and it is worth reporting
  precisely.
- **The best honest precision at a useful signal count is ~13–29%.** The 2026
  holdout is 13.61% at 6,202 signals; the best figure for this model at ≥250
  signals is 26.78%; top-1-per-session reached 23.81% on the old grid. None of
  these exceeds the model's own oracle frontier, and the top-1 rule sits *below*
  it (23.81% at 462 signals against 26.78% at 534).
- **The headline is conservative, not flattering.** The dominant walk-forward fold
  has the *lowest* precision; removing it raises the pooled figure. Lift is 4.70×
  on the holdout, computed against an exactly pooled base rate.
- **It is not 60%, and no configuration came close.** Across 82 features, four
  model families, 58 hyperparameter configurations, nine feature-group ablations
  and a cross-sectional ranking experiment, nothing approached the target.
- **The 70–80% figures in the source material are in-sample or tiny-sample
  artifacts.** Reproducing them requires the very protocol error this repository
  was built to catch: the six configurations landing between 50% and 68%
  in-sample deliver **11–18%** out-of-sample (11.39 / 12.19 / 12.94 / 14.44 /
  15.98 / 18.21%).
- **The earlier claim that 70% is *mathematically* unreachable is withdrawn.** It
  overstated what the frontier computation proves. The frontier bounds threshold
  choice on one model's ranking; a different feature set would produce a different
  ranking with its own frontier. What can be said is empirical: every
  configuration tried fell 2.6–4.9× short, and the arithmetic in §1 shows why the
  target demands an extreme operating point. That is a strong empirical case, not
  a proof, and it is reported as such.

---
---

## 10. Reproduce

```powershell
$env:PYTHONPATH='.'
python -m src.ml.build_matrix --stride 1    # full session grid, 2.68M rows, 82 features
python -m src.ml.precision_ceiling          # §2: scoped frontier
python -m src.ml.search --preset wide --workers 5
python -m src.ml.null_tests                 # §7: validate the harness cannot cheat
python -m src.ml.concentration              # §8: how much one period carries
python -m src.ml.final_holdout              # §6: purged one-shot 2026 evaluation
python scripts/audit_reports.py             # consistency of every published number
python scripts/scratch/check_stride_phase.py  # the stride counterexample
```

Machine-readable output: `reports/ml_precision_ceiling.json`,
`reports/ml_search_wide.json`, `reports/ml_null_tests.json`,
`reports/ml_concentration.json`, `reports/ml_final_holdout.json`,
`reports/ml_precision_frontier_oos.csv`.

**Note on the grid.** Earlier versions ran on `--stride 5`, which sampled every
fifth *session*. That was wrong for two reasons: it reduced 887 sessions to 178,
too few for the walk-forward's 150-session warm-up, and it made each row's
features come from a different cross-section than the one being scored. The
harness now uses the full session grid. Numbers produced on the stride-5 matrix
differ from the ones in this document and are not comparable to them.

---

## 11. What would change the answer

**No mathematical bound is claimed here**, so the answer is openly a property of
the search that was run, not of the problem. It could move:

- **A different target.** +5% in 10 sessions has a far higher base rate, so far
  less precision is needed to be useful; a high precision figure may well be
  reachable there. It is also a much less valuable prediction.
- **A longer horizon.** More time for the event raises the base rate.
- **A genuinely better feature set.** This is the real open door, and the honest
  one: §2 bounds threshold choice on the *current* ranking only, so a feature set
  that reorders the data would face a different frontier. The 82-feature set, nine
  group ablations and the cross-sectional ranks were all tried against exactly this
  question and none moved it materially — but that is a search result over the
  features tried, not a closed question.
- **The long-horizon task.** This work predicts a 10-session +30% move, which is
  not the original 504-session low-zone objective. Results here do not transfer in
  either direction; see `docs/REVIEW_RESPONSE.md` §"Not done".
- **Point-in-time universe and real costs.** These would make results *worse*, not
  better, but are required before any live claim regardless.

Reporting a measured result that is real, over a fabricated 70% that is not, is
the only defensible outcome. The instruction not to report below 60% cannot be
honoured without inventing a number, and inventing one would repeat precisely the
failure this audit was commissioned to find.
