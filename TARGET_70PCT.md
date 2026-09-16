# Can the 70% target be reached?

**Short answer: no — and this is now a measurement, not an opinion.**

The requested target was "tune it to 70%, and don't report back below 60%." This
document reports why that target is unreachable for this task, with the bound
computed from the real data rather than asserted. The honest result is stated
first, because withholding it would be the one genuinely harmful outcome.

---

## 1. The arithmetic that decides it

Precision at a threshold is not a free parameter. For base rate π, recall *r* and
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

## 2. The measured oracle bound

`src/ml/precision_ceiling.py` fits the standard model on each purged
walk-forward fold and then computes, **on the true out-of-sample labels**, the
best precision achievable at *any* threshold. Because it is computed from the
true labels, no threshold choice, model change or hyperparameter search can
exceed it.

Out-of-sample: 281,227 rows, 11,496 positives, base rate 4.0878%.

Because raw probabilities from four separately-fitted fold models are not on a
common scale, the bound is computed twice: once pooling raw scores, once ranking
scores within each fold. The rank-normalised column is the fairer of the two.

| Minimum signals | Max precision (pooled raw) | Max precision (per-fold rank) | Recall |
| ---: | ---: | ---: | ---: |
| 250 | 24.54% | 26.90% | 0.57% |
| 500 | 23.67% | 23.80% | 1.16% |
| 1,000 | 21.11% | 21.88% | 1.91% |
| 2,000 | 19.00% | 18.60% | 3.31% |
| 5,000 | 14.43% | 14.54% | 7.79% |
| 10,000 | 12.56% | 12.75% | 11.38% |

And by required recall:

| Recall floor | Max precision available | Signals published |
| ---: | ---: | ---: |
| ≥ 50% | 6.60% | 87,619 |
| ≥ 30% | 9.07% | 38,157 |
| ≥ 20% | 10.66% | 22,612 |
| ≥ 10% | **13.08%** | 9,893 |
| ≥ 5% | 15.71% | 4,240 |

**Practical ceiling (≥ 250 signals): 24.54% pooled, 26.90% rank-normalised. A 70%
target is 2.60× that ceiling. At a useful recall (≥ 10%) the ceiling is 13.08%
and the target is 5.35× away.**

No amount of feature engineering, hyperparameter search, ensembling or stacking
can cross a bound computed from the labels themselves. That is the whole point of
computing it before spending compute.

> **Correction.** An earlier run of this analysis reported 20.23%. The sampling
> grid then spanned only 200 points across the whole range, so it jumped from 1
> published row to ~338 and could not represent the small-count region at all.
> The grid is now dense below 2,000 signals. The corrected bound is higher, and
> it is the number that reconciles with the independent cross-sectional
> experiment in §5 — 23.81% at 462 signals sits just below the 500-signal oracle
> of 23.67%. The earlier figure was a sampling artifact of my own analysis, not a
> property of the data.

---

## 3. Why "70%" appeared reachable in the source material

Three mechanisms, all of which this bound eliminates:

1. **Publishing almost nothing.** The absolute maximum precision in the table is
   **100%** — achieved by publishing a single row that happened to be a hit. The
   source project's headline numbers rest on **5–22 hand-picked yes-predictions**.
   A 100% bound on one row is not a strategy, and 70% on 13 signals is the same
   artifact one order of magnitude up.
2. **Measuring in-sample.** The in-sample frontier in the same run also reaches
   100%. The standard model scores **49–57% in-sample** on the exact folds where
   it scores **14–16% out-of-sample**. That gap *is* the source project's 70–80%:
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
| ExtraTrees, 2% publication | 56.26% | **18.21%** | 368 | 3/4 |
| ExtraTrees, 2% publication | 47.05% | **16.50%** | 515 | 3/4 |
| HGB (baseline), 2% publication | 50.60% | **15.98%** | 1,790 | 4/4 |
| ExtraTrees, 5% publication | 40.89% | **15.72%** | 3,913 | 4/4 |
| HGB wide, 2% publication | 68.57% | 15.26% | 996 | 4/4 |
| RF, 2% publication | 42.07% | 14.70% | 3,892 | 4/4 |

Three things stand out.

1. **The best configuration is 18.21% at 368 signals, and it is 3/4 folds — worse
   on consistency than the baseline's 4/4.** It is not a better strategy; it is a
   luckier draw on a smaller sample. The baseline is the more trustworthy result.
2. **The in-sample/OOS gap is 2.4×–11×.** The very configuration that reaches
   68.57% in-sample delivers 15.26% out-of-sample. This ratio *is* the mechanism
   behind every published "70%".
3. **The search's top row is a trap.** A configuration scored **33.33%** — on
   **3 signals**. In-sample it was 91.60%. Reporting that as a 33% strategy would
   be the same error as reporting 70% on 13 cases.

Feature-group ablations were also run, with the group table corrected after an
initial bug (prefix matching made seven "different" ablations resolve to the same
ten columns — they are now exact, disjoint sets covering all 82 features, with a
`check_groups` guard). Dropping `position` gives 17.10% at 1,661 signals, dropping
`kdj` 16.05%, dropping `volume` 16.00%, versus 15.98% for all features. Single
groups: `cross` alone 14.93%, `volatility` alone 14.79%, `market` alone 13.67%,
`candle` alone 12.83%, `momentum` alone 12.65%, `kdj` alone 7.69%.

Two conclusions: the raw-volatility and cross-sectional families carry the most
standalone information, and **the KDJ/expert-style indicator family is the
weakest single group** — the opposite of what the original expert library
assumed. No group or combination approaches the target.

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
genuinely informative (pooled AUC 0.699; mean within-session AUC 0.725, above 0.5
in 98% of sessions).

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

This is exactly what the §2 bound predicts. The oracle at 500 signals is 23.67%
and top-1 achieves 23.81% at 462 — the model is *at* the frontier, not beyond it.
Any rule that publishes fewer signals will report higher precision, and that is
not skill.

---

## 6. The one-shot 2026 holdout — the only real out-of-sample evidence

`src/ml/final_holdout.py` evaluates **one pre-committed configuration, once**, on
the 160 sessions from 2026-01-01 onward that no other script touches.

| | Value |
| --- | ---: |
| Training sessions | 727 (434,383 usable rows) |
| Holdout sessions | 160 (95,374 usable rows) |
| Threshold (from pre-2026 scores only) | 0.165961 |
| Holdout base rate | 2.9096% |
| Signals published | 1,614 |
| Hits | 196 |
| **Precision** | **12.14%** |
| Lift over base rate | **4.17×** |
| Wilson 95% interval | [10.64%, 13.83%] |
| **Date-clustered 95% interval** | **[8.82%, 16.48%]** |
| Distinct stocks / dates | 802 / 146 |
| Date HHI | 0.0285 (≈35.1 effective dates) |
| Precision excluding busiest date | 12.87% (1,476 signals) |

The date-clustered interval **excludes the base rate**, so the effect is real and
not an artifact of clustering — 1,614 signals across 802 stocks and 146 distinct
dates, and dropping the single busiest date *raises* precision rather than
destroying it. This is a genuine, modest edge of roughly 4× the base rate.

It is also **12.14%, not 70%.**

---

## 7. Is the measurement itself trustworthy?

Two independent null batteries were run. The larger one
(`outputs/ml/audit/nulls_audit.json`, 2,906 s, 14 variants) destroys the
feature–label relationship in ten different ways and confirms the harness cannot
manufacture precision where none exists. It also includes two **positive
controls** that prove the harness *can* detect a real signal when one is planted.

| Variant | OOS precision | Base rate | Lift | Folds above base |
| --- | ---: | ---: | ---: | ---: |
| **real (control)** | **15.98%** | 4.46% | **3.58×** | **4/4** |
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

**Every null collapses to the base rate (lift 0.88–1.21), and both positive
controls fire strongly (9.47× and 4.71× with 4/4 folds).** This is the decisive
validation: the harness detects a planted signal and finds nothing where nothing
was planted. The baseline is therefore measuring a real relationship, not an
artifact of the purge, the folds, the stride sampling or the feature scaling.

Two further results sharpen this. The auditor's chance-ceiling calculation puts
2% publication at 5,625 signals on 281,227 rows with a null mean of 4.12% and SD
0.262 pp — so the observed 15.98% sits roughly **25 standard deviations** above
chance, and the best of 1,000 null draws is 5.10%. A date-block bootstrap over
299 distinct signal dates gives a **95% interval of [13.6%, 18.7%]**. Row-level
intervals would be wrong here (3.2–5.1%) because same-day signals share a
10-session forward window.

A smaller independent battery (`reports/ml_null_tests.json`) reached the same
conclusion by different means: permuted labels 3.00% vs 3.09% base, noise features
4.55% vs 4.12%, and no feature exceeding AUC 0.68. **Both verdicts:
trustworthy.**

> **Two corrections the audit forced, both now applied.** First, the pooled base
> rate was an unweighted mean of per-fold rates while precision was
> signal-weighted, so the reported lift mixed two weightings: the true figure is
> **3.58×, not 3.87×**. `summarise()` now weights both consistently and reports
> the unweighted value alongside. Second, `label_close` was censored on "saw at
> least one future bar" instead of "has a full 10-bar window", so 5,747 rows at
> the very end of the panel carried a label computed from a partial window.
> Censoring is now on the full window, and the label ratio is compared in float64
> to remove 3 rows where a float32 round-trip flipped the comparison. Neither
> defect touches `label_high`, and a full rebuild confirms `entry_open`,
> `fwd_max_high`, `label_high`, `resolved` and all 85 feature columns are
> **bit-identical** (max absolute difference 0.000e+00).

---

## 8. How much does any single period carry?

A pooled precision can be carried by a handful of observations, so both headline
numbers were stress-tested for concentration (`src/ml/concentration.py`).

**Walk-forward baseline, per fold:**

| Fold (test window) | Signals | Share | Precision |
| --- | ---: | ---: | ---: |
| 2024-02-02 → 2024-07-29 | 1,131 | 63.2% | 10.79% |
| 2024-07-30 → 2025-01-17 | 539 | 30.1% | 23.19% |
| 2025-01-20 → 2025-07-14 | 45 | 2.5% | 31.11% |
| 2025-07-15 → 2025-12-31 | 75 | 4.2% | 33.33% |

This **is** uneven — 63% of signals sit in one fold — and it is worth stating
plainly. But the direction matters: the dominant fold has the *lowest* precision
(10.79%), so it drags the pooled figure **down**, not up. Removing it raises the
pooled number from 15.98% to **24.89%**. The concentration makes the reported
headline conservative, not flattering. Dropping the busiest dates also raises
precision monotonically (15.98% → 17.34% after dropping 20 dates).

Note that folds 3–4 carry only 45 and 75 signals, so "4/4 folds above base" is
weaker evidence than the phrase suggests: two of those four folds are small. The
result rests on folds 1–2, which together hold 93% of the signals and bracket the
15.98% pooled figure from either side.

**2026 holdout, same treatment:**

| Treatment | Precision | Signals |
| --- | ---: | ---: |
| As published | 12.14% | 1,614 |
| Drop busiest date | 12.87% | 1,476 |
| Drop 3 busiest dates | 13.80% | 1,312 |
| Drop 5 busiest dates | 14.35% | 1,150 |
| First half of signal dates | 10.29% | 807 |
| Second half of signal dates | 14.00% | 807 |

No single date carries it: the busiest date holds 8.6% of signals, and removing it
*raises* precision. Both chronological halves are far above the 2.91% base rate,
and the effect strengthens in the later half. This is the most robust number in
the document.

---

- **A real signal exists.** The one-shot 2026 holdout gives **12.14%** precision
  against a 2.91% base rate — a **4.17× lift** on 1,614 signals across 802 stocks
  and 146 distinct dates, with a date-clustered 95% interval of [8.82%, 16.48%]
  that excludes the base rate. The within-day ranking is also real (AUC 0.725).
  This is a genuine, modest edge and it is worth reporting precisely.
- **The best honest precision at a useful signal count is ~16–24%.** The
  walk-forward baseline is 15.98% at 1,790 signals; top-1-per-session is 23.81% at
  462; and the oracle bound at those counts is 23.67–24.54%. The model is already
  *on* the frontier.
- **The headline is conservative, not flattering.** 63% of walk-forward signals
  sit in the fold with the *lowest* precision (10.79%); removing that fold raises
  the pooled figure to 24.89%. Lift is 3.58×, not the 3.87× first reported.
- **It is not 60%, and cannot be.** At a useful recall (≥ 10%) the ceiling is
  13.08%, and the achieved holdout figure of 12.14% sits essentially on it.
- **The 70–80% figures in the source material are in-sample or tiny-sample
  artifacts.** Reproducing them requires the very protocol error this repository
  was built to catch: the configuration that reaches 68.57% in-sample delivers
  15.26% out-of-sample.
- **The target was mis-specified, not merely hard.** "Tune it to 70%" presumes 70%
  is a reachable point on this frontier. §2 shows it is 2.60× beyond the best
  achievable point, and no amount of tuning reaches it.

---

## 9. Reproduce

```powershell
$env:PYTHONPATH='.'
python -m src.ml.build_matrix --stride 5    # 82 causal features + labels
python -m src.ml.profile_stages             # time the harness before sizing a run
python -m src.ml.precision_ceiling          # the bound in §2
python -m src.ml.search --preset wide --workers 5
python -m src.ml.null_tests                 # §7: prove the harness cannot cheat
python -m src.ml.concentration              # §8: how much one period carries
python -m src.ml.final_holdout              # §6: one-shot 2026 evaluation
```

Machine-readable output: `reports/ml_precision_ceiling.json`,
`reports/ml_search_wide.json`, `reports/ml_null_tests.json`,
`reports/ml_concentration.json`, `reports/ml_final_holdout.json`,
`reports/ml_precision_frontier_oos.csv`.

---

## 10. What would change the answer

The bound is a property of *this label definition on this universe*, so it can
legitimately move if the question changes:

- **A different target.** +5% in 10 sessions has a far higher base rate; 70% may
  well be reachable there and would be an honest result to report. It is also a
  much less valuable prediction.
- **A longer horizon.** More time for the event raises the base rate.
- **A genuinely better feature set** — if it moved the achievable ROC corner. §2
  bounds *threshold* choice, so better features could in principle raise it. The
  82-feature set, the group ablations and the cross-sectional ranks were all tried
  against exactly this question and none moved the corner materially.
- **Point-in-time universe and real costs.** These would make results *worse*, not
  better, but are required before any live claim regardless.

Reporting a measured result that is real, over a fabricated 70% that is not, is
the only defensible outcome. The instruction not to report below 60% cannot be
honoured without inventing a number, and inventing one would repeat precisely the
failure this audit was commissioned to find.
