# LOWZONE EVIDENCE AUDIT

**Scope.** Audit of the A-share quant research project at `D:\xm\60日预测\` and `D:\xm\_a_share_86_custom_50pct\a_share_86_custom_50pct\`. Every claim below was checked against the actual JSON / CSV / Markdown content on disk. No claim here rests on a summary that merely points at another summary. Numbers are quoted verbatim with their file path.

**The single most important thing to know before reading the tables:** the project's headline metric is labelled *"hit within pre-anchor -10..0"* in its own success records, but the code computes a **symmetric ±10 window**. The true strictly-pre-anchor counts are materially lower. For 2023 — the lead year of the V08 success claim — the true value is **18/50 = 36.0%**, which **fails** the project's own 60% gate. Details in Section 2.

**Method note.** All JSON/Markdown read as `encoding='utf-8'`; all CSV as `encoding='utf-8-sig'`. PowerShell console output was never used as evidence (it renders the Chinese filenames as mojibake); the `read` tool or Python was used throughout.

---

## 1. Version-by-version claim table

| Version | Claimed scope | Exact reported fractions (all of them) | What the denominator literally is | In-sample or out-of-sample? | Evidence file paths | Verdict |
|---|---|---|---|---|---|---|
| **V00** | "Completed baseline. The 2026 event-window run reported trend 75/84, breakout 70/84, and range 29/84. Retrospective event-window validation only." | trend 75/84 = 0.8929; range 29/84 = 0.3452; breakout 70/84 = 0.8333 | **Three different denominators disguised as one.** `eligible_stocks=84` for all rows, but `counted_stocks` differs: trend 84, range **36**, breakout **82**. Range's 0.8056 precision is over its own 36 signaled stocks; its rate over all 84 is 0.3452. | In-sample / retrospective event-window. `run_manifest.json` mode is a single 2026 as-of run. | `…\output_86_real\tencent_results\accuracy_summary.csv`; `…\output_86_real\tencent_results\run_manifest.json` | **SUPPORTED** (numbers reproduce exactly) — but the index presents 29/84 and 70/84 as if all three shared one denominator when they do not. |
| **V01** | "Exploratory. Includes anchor-distance diagnostics and rule ladders; not a live-proof result." | No headline fraction anywhere. Only coverage / median-lead-time diagnostics. | n/a | Post-hoc anchors only. | `D:\xm\60日预测\03_anchor_rule_search\` (no version-scoped scored summary found) | **NOT_FOUND** — no version-scoped claim with a fraction to verify. Correctly self-labelled exploratory. |
| **V02** | "Completed exploratory CV. R2e strict five-fold result: 52/84 within ±5 and 60/84 within ±10." | Fold-by-fold ±5: 14, 11, 10, 8, 9 → sum **52**. Fold-by-fold ±10: 14, 12, 13, 10, 11 → sum **60**. Eligible per fold: 17,17,17,17,16 → **84**. | 84 eligible stocks with a full 60-day event window, stock-grouped 5-fold. | **Out-of-sample within the fold structure** (5-fold, grouped by stock; the same rule was selected in all 5 folds), **but the label/anchor is retrospective** — it is the 2026 post-hoc max-rise path. | `…\price_action_cv_reversal_broad_86_v3\summary.csv`, `summary.json`, `fold_choices.csv`, `FINAL_RULE.md`, `R2E_LADDER_REPORT.md`; duplicate in `…\price_action_final_tiers_86_v2\CV_REPORT.md` | **SUPPORTED** for the two fractions (fold sums reconcile exactly). **PARTIAL** overall: 53/84 anchors fall on one January-2026 date and the companion outcome table covers only 62 of 84 stocks. |
| **V03** | "Exploratory and not accepted as a four-year 80% lockbox solution." | `yearwise_causal_ml_training_2023_2025_v1`: 2023 **69/100**, 2024 **100/100**, 2025 **91/100**, overall **181/300 = 60.3%**. Also v2: 4/50, 24/50, 22/50; v3 probe: 2/3. | **A merged 100-case bucket mixing gain AND loss cases**, not 50 pure gain cases. `cases = len(details)` = 100/yr. | In-sample year-wise fitting. | `…\yearwise_causal_ml_training_2023_2025_v1\OVERALL_GATE.md` + `run_summary.json`; `…\yearwise_gain_avoid_loss_2023_2025_v2\OVERALL_GATE.md`; `…_v3_probe\OVERALL_GATE.md`; `D:\xm\60日预测\05_annual_training_lockbox\yearwise_causal_ml_training.py` | **UNSUPPORTED as a pass.** The 100/100 is on a mixed bucket that includes loss cases; the v3 "pass" is on 3 cases. The index's own wording ("not accepted") is honest. |
| **V04** | "Exploratory. Multiple ladders, lockbox, and upper-bound experiments were recorded; previous runs did not pass the joint gain/loss acceptance gate." | Every lockbox ladder on disk reads **NOT_PASS**. `strict_lockbox`: 24 variants, 20945 rows, **0** passing all three years ≥30/50 gain with <25/50 loss false; best test ±10 by year: 2023 max **8**, 2024 max **14**, 2025 max **22**. `augmented_lockbox`: 24 variants, 72 rows, **0** passed. Oracle upper bound: max_gain_at_loss10 = **36 / 29 / 27** for 2023/2024/2025, with `min_loss_budget_for_gain40` = 14 / 21 / 23. | 50 gain cases per year for the ladder sweeps; the oracle frontier is over all candidate bars. | Out-of-sample in the lockbox sweeps (target year excluded from fitting and threshold selection); the oracle is an upper bound, not a model. | `…\share_2023_2026_training_20260908\strategies\strict_lockbox\REPORT.md` + `sweep_ranked.csv`; `…\augmented_lockbox\REPORT.md`; `…\original86_allbars_outcome20_upperbound_20260910_v2\ORACLE_FEASIBILITY_REPORT.md` + `oracle_feasibility_summary.csv` | **UNSUPPORTED (as a pass).** Nothing on disk passes. The oracle frontier independently shows the target is unreachable by any threshold. |
| **V05** | "Completed tooling. Charts and indexes are generated from the corresponding run outputs." | No scored fraction. Chart/index generation only. | n/a | n/a | `D:\xm\60日预测\07_charts_and_scans\`, `08_packaging_tools\` | **NOT_FOUND** — no numeric claim exists to verify. Tooling claim is consistent with the `charts_60d` / `charts_120d` directories present in the run outputs. |
| **V06** | "Exploratory failure recorded… reached only 5/50 pre-anchor hits and 48/50 loss alerts." | `V06_ROUND_REPORT.md`: gain pre-anchor −10..0 → 2023 **0/50**, 2024 **5/50**, 2025 **6/50**, 2026 **25/50**; loss false alerts **50/50, 41/50, 49/50, 36/50**. Status **NOT_PASS**. | 50 top-ranked annual gain cases per year (and separately 50 loss cases). | In-sample ("pooled in-sample V2"). | `D:\xm\60日预测\09_bull_lowzone_model\V06_ROUND_REPORT.md`; `D:\xm\60日预测\outputs\v2_full86\rounds\V2-FULL86\summary.csv` + `SUMMARY_ALL.csv` + `parameters.json` | **SUPPORTED as a reported failure.** Every number matches `summary.csv` exactly. Note the index's "5/50" is the 2024 figure only — it omits 0/50 in 2023. |
| **V07** | Present in `V07_ROUND_REPORT.md` but **has no row in `TRAINING_VERSION_INDEX.md`.** | Yearwise: 2023 **4/50**, 2024 **12/50**, 2025 **13/50**, 2026 **24/50**; loss false **18/50, 4/50, 40/50, 47/50**. Status **NOT_PASS**. | 50 gain cases / 50 loss cases per year. | Year-wise in-sample. | `D:\xm\60日预测\09_bull_lowzone_model\V07_ROUND_REPORT.md`; `D:\xm\60日预测\outputs\v3_yearwise_screen86\SUMMARY_ALL.csv` and `…\v3_yearwise_charts86\SUMMARY_ALL.csv` | **SUPPORTED as a reported failure.** Matches `SUMMARY_ALL.csv` exactly. The version index silently omits V07. |
| **V08** | "PASS_YEARWISE_IN_SAMPLE: 2023 31/50, 2024 35/50, 2025 39/50, 2026 33/50 within pre-anchor -10..0; loss false alerts 0/50 in all four years. Parameters are selected separately per year, so this is not a frozen cross-year prediction result." | Claimed: **31/50 (62.0%), 35/50 (70.0%), 39/50 (78.0%), 33/50 (66.0%)**; loss false **0/50** each year. Unified rule: **85/150 = 56.7% → NOT_PASS**. Frozen per-year ensemble: **105/150 = 70.0%**. | 50 gain cases and 50 loss cases per year — **but drawn from ~3,193 mainboard codes, not the "original 86" the index claims** (see §2.3). | **In-sample.** `"training_mode": "same_year_in_sample"`, `"ranking_is_retrospective": true`. | `…\V08_SUCCESS_RECORD.md`; `…\yearwise_gain_avoid_loss_2023_2025_v4_insample\{FINAL_STATUS.md, OVERALL_GATE.md, overall_gate.json, input_quality.json, round_2023|2024|2025|overall\REPORT.md, overall_yearwise_ensemble\REPORT.md}`; `D:\xm\60日预测\outputs\v4_2026_compare86_fixed2\{OVERALL_GATE.md, overall_gate.json, repro_manifest.json, round_2026\REPORT.md}` | **PARTIAL → UNSUPPORTED as stated.** The four fractions are reproducible from `signal_results.csv`, but the "pre-anchor -10..0" label is wrong, the 0/50 loss denominator is inflated, the universe claim is wrong, and the project's own cross-year lockbox contradicts it (17/2/15). Full dissection in §2. |
| **R01** | Present as `v1_full_logistic_2026` / `R01_logistic_2026_lockbox`. Logistic, threshold 0.55, min_tier 1, train 2023-2025, test 2026. Train AUC 0.8464, AP 0.0179, 2,171,925 train rows, 505,600 test rows. | **TEST 2026: gain hits ±10 = 7/50 = 14.0%; pre-10 = 5/50 = 10.0%; loss false = 48/50 = 0.96.** Train years: 2023 7/50, 2024 12/50, 2025 19/50 (±10); loss false 49/50, 48/50, 47/50. | 50 gain + 50 loss cases per year; test years only in `summary_test.csv`. | **Genuine out-of-sample lockbox** (train years and test year are disjoint). | `…\outputs\v1_full_logistic_2026\rounds\R01_logistic_2026_lockbox\summary_test.csv` + `summary_train.csv` + `parameters.json`; `…\v1_full_logistic_2026\run_manifest.json`; `…\v1_full_logistic_2026\case_manifest.csv` | **SUPPORTED as a reported failure.** The one honest chronological lockbox in the V-chain, and it fails decisively (14.0% vs a 60% gate; 96% loss false-alert rate). |

**Also present in the version index (checked for completeness):**

| Version | Claimed scope | Exact reported fractions | Denominator | In/out-of-sample | Evidence | Verdict |
|---|---|---|---|---|---|---|
| **V09** | "FAILED_DIAGNOSTIC: thresholds 4-7 produced only 0-8/50 gain hits in 2023-2025 (pre-anchor -10..0) and 13-49/50 loss false alerts." | gain_pm10 across thresholds: 2023 {0,2,5,0}, 2024 {1,0,1,2}, 2025 {8,3,0,0}; loss_false 2023 {49,49,48,43}, 2024 {42,42,37,17}, 2025 {32,27,21,13} | 50 gain / 50 loss cases per year | In-sample diagnostic | `D:\xm\60日预测\outputs\v9_factor_diagnostic\summary.csv`, `STRATEGY.md`, `run_manifest.json` | **SUPPORTED as stated** (0-8 and 13-49 both reproduce exactly). |
| **V10** | "FAILED: yearwise pre-anchor hits 3/50 (2023), 13/50 (2024), 13/50 (2025), 25/50 (2026); loss false alerts 34/50, 34/50, 27/50, 47/50." | pre10 = 3, 13, 13, 25; pm10 = 3, 16, 13, 31; loss false = 34, 34, 27, 47 | 50 gain / 50 loss cases per year | "Same-year fit only; no cross-year claim." | `D:\xm\60日预测\outputs\v10_supervised86\SUMMARY_ALL.csv` + `rounds\V10-RF86\summary.csv`; `…\09_bull_lowzone_model\V10_SUPERVISED_RF86.md` | **SUPPORTED as a reported failure** — all eight numbers match exactly. |

---

## 2. The V08 claim dissected

### 2.1 What the four fractions actually are

The claimed numbers exist and are reproducible. Reading `signal_results.csv` from each round directory:

| Year | gain cases | signals found | `hit_pm10` (the claimed number) | strictly pre `[-10..-1]` | exact anchor day (0) | post `[1..10]` |
|---|---|---|---|---|---|---|
| 2023 | 50 | 38 | **31** | 13 | 5 | 13 |
| 2024 | 50 | 46 | **35** | 26 | 3 | 6 |
| 2025 | 50 | 47 | **39** | 22 | 10 | 7 |
| 2026 | 50 | 46 | **33** | 23 | 5 | 5 |

Files: `…\yearwise_gain_avoid_loss_2023_2025_v4_insample\round_{2023,2024,2025}\signal_results.csv` and `D:\xm\60日预测\outputs\v4_2026_compare86_fixed2\round_2026\signal_results.csv`. The values 31/35/39/33 match `overall_gate.json` (`gain_hits_pm10`), `round_*/summary.json`, and the success record.

### 2.2 What "hit within pre-anchor -10..0" means — and why the label is false

The label is **wrong**. The metric is symmetric, not directional. From `yearwise_gain_avoid_loss_training_v3.py`:

- line ~349 / ~365: `hit_pm10 = abs(distance_trading_days) <= 10`
- `hit_pm5  = abs(distance_trading_days) <= 5`

`abs(...)` means a signal **after** the anchor counts identically to one before it. The correct strictly-pre-anchor figure for `[-10..0]` is therefore `(distance >= -10) & (distance <= 0)`:

| Year | Claimed ("pre-anchor -10..0") | True strictly pre-anchor | Claimed rate | True rate | Clears the project's 60% gate? |
|---|---|---|---|---|---|
| 2023 | 31/50 | **18/50** | 62.0% | **36.0%** | Claimed: yes. **True: NO.** |
| 2024 | 35/50 | **29/50** | 70.0% | **58.0%** | Claimed: yes. **True: NO.** |
| 2025 | 39/50 | **32/50** | 78.0% | **64.0%** | Claimed: yes. True: yes. |
| 2026 | 33/50 | **28/50** | 66.0% | **56.0%** | Claimed: yes. **True: NO.** |

**Three of the four years fail the 60% gate once the label is read the way the code computes it.** In 2023, 42% of the claimed "pre-anchor" hits are either on the anchor day itself or after it.

The label is not merely loose. For **V06** and **V07** the same phrase is applied to a genuinely directional metric — `v1_bull_lowzone_60d.py` line ~375 computes `hit_pre10 = -SIGNAL_PRE_DAYS <= distance <= 0`, and V06's published 0/5/6/25 matches that column exactly. So the phrase meant one thing in V06/V07 and silently changed meaning in V08 while the wording stayed identical. Anyone comparing V07's "13/50" against V08's "39/50" for 2025 is comparing a directional metric with a symmetric one.

**Is the anchor a future event?** Effectively yes, and for 2026 it is *only* a future event. The gain anchor is `interval_start_pos` with `anchor_kind="low_start"` — the minimum low of the year's best low→high interval (`annual_interval_extreme_blind_test_2023_2025.py`, `maximum_intervals()`, lines 163-217). It is the start of the best interval, so it precedes that interval's end, but its location within the year is determined by scanning the **entire year**. 2026 anchors run 2026-01-06 to 2026-04-07, and the 2026 data file extends to 2026-08-28. The metric is not computable until the year is over. The run self-declares this: `input_quality.json` contains `"ranking_is_retrospective": true` and `"training_mode": "same_year_in_sample"`.

**2026 is also an incomplete year** (data ends 2026-08-28) and is not out-of-sample in any sense — tier, threshold, `loss_max`, and `min_bars` were all re-searched on 2026's own labels (`repro_manifest.json`: `min_tier=1`, `gain_threshold=0.70`, `loss_max=0.05`).

### 2.3 The "0/50 loss false alerts" denominator is inflated

Every year reports exactly `0/50`. The 50 is real, but it is not 50 opportunities to be wrong. Signals were found for only a handful of loss cases:

| Year | loss cases | loss signals found | loss false ±10 | distance range of the signals that were found |
|---|---|---|---|---|
| 2023 | 50 | **4** | 0 | −230 to −84 |
| 2024 | 50 | **18** | 0 | −150 to −69 |
| 2025 | 50 | **11** | 0 | −230 to −25 |
| 2026 | 50 | **19** | 0 | −133 to −77 |

`hit_pm10` is `False` whenever `signal_found` is `False`, so 46 / 32 / 39 / 31 loss cases contribute **automatic zeros**. The "0/50" therefore reads as perfect specificity when it is really "we emitted almost no loss-side signals, and the few we emitted were 25-230 trading days away from the anchor". It is a *sensitivity* statement, not a specificity one.

This is not an accident, because the optimizer is explicitly rewarded for it. `_sort_key()` in `yearwise_gain_avoid_loss_training_v3.py` (lines 413-424) orders candidates by:

```
(qualified, -loss_false_pm10, -loss_false_pm5, gain_hit_rate_pm10, gain_hits_pm5,
 gain_signal_precision_pm10, -median_gain_abs_distance, -selected_code_years)
```

Zero loss false alerts sorts **above** gain recall. With a `LOSS_FALSE_LIMIT = 24` gate, the search can satisfy the loss side by suppressing signals entirely. 2025 is the clearest case: 47 gain signals but only 11 loss signals in the same year.

### 2.4 The universe is not the "original 86 stocks"

`TRAINING_VERSION_INDEX.md` V08 row claims scope "**Original 86 stocks**; 2023-2026 annual gain/loss top-50 cases". This is false for the 2023-2025 leg.

- `v4_insample\input_quality.json` records `"codes_after_dedup": 3193` and sources covering **2,939** and **3,193** codes.
- `yearwise_gain_avoid_loss_training_v4_insample.py` line 144-146: `--universe` defaults to `mainboard_universe.csv`, and line 156 calls `base.load_names(args.universe)`. `load_names()` reads **display names only** — no universe filter is applied to the price data. Line 157 calls `build_case_manifest(data, names, [2023,2024,2025], ...)` over everything.
- Overlap of the published gain-top-50 with the 86-stock list (`…\top50_two_stage_package_20260909\data\stock_list_86.csv`, 86 unique codes):

| Year | gain_top50 ∩ 86-list | loss_bottom50 ∩ 86-list | unique codes in manifest |
|---|---|---|---|
| 2023 | **1 / 50** | 1 / 50 | 97 |
| 2024 | **1 / 50** | 1 / 50 | 92 |
| 2025 | **4 / 50** | 0 / 50 | 98 |
| 2026 | **50 / 50** | 3 / 50 | 98 |

So the 2023-2025 cases come from the broad mainboard universe, while the 2026 cases come **entirely** from the 86-stock list. Those 86 stocks are themselves the top-86 by 2026 max gain (recomputed: **80/86** of the list falls in the 2026 top-86 by `high/low−1`; median rank 44 of 3,193), and the project's own handoff document admits the problem: `HANDOFF_麻烦点与分工.md` line 13 — *"这86只本身是赢家样本"* ("these 86 are themselves a winner sample"), with line 15 recommending ~86-150 ordinary control stocks be added and tested with parameters fully frozen.

**Consequence:** the "four-year" V08 claim is not four years of one population. It is three years of a ~3,000-code universe plus one year of a winner-biased 86-stock subset whose membership was chosen using that same year's outcome. The four per-year fractions are not comparable and cannot be summed into a four-year claim.

### 2.5 Reproducibility: the recorded 2026 command cannot reproduce the 2026 result

`D:\xm\60日预测\outputs\v4_2026_compare86_fixed2\repro_manifest.json` records:

```
"script": "D:\\xm\\_a_share_86_custom_50pct\\a_share_86_custom_50pct\\yearwise_gain_avoid_loss_training_v4_insample.py",
"command": "python yearwise_gain_avoid_loss_training_v4_insample.py ... --top-n 50 --years 2026"
```

That script (sha256 `aa022041abb16ae9b044af4fa986e26b74a3d692a55705ddb45eff57697aa983`, byte-identical in both `D:\xm\60日预测\05_annual_training_lockbox\` and `D:\xm\_a_share_86_custom_50pct\a_share_86_custom_50pct\`) **hardcodes the three-year list**:

- line 147: `ap.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025])`
- line 157: `all_manifest = base.build_case_manifest(data, names, [2023, 2024, 2025], top_n=args.top_n)`
- line 158: `manifest = all_manifest[all_manifest.year.isin(years)]`

`all_manifest` contains only 2023-2025 rows regardless of `--years`, so `--years 2026` yields an **empty** manifest. A scan of all `*.py` under both project roots found **no** script anywhere that builds a four-year or 2026 manifest. Running the recorded command today would reproduce `case_count: 0` — exactly the state preserved in the two predecessor directories:

- `outputs\v4_2026_compare86\input_quality.json` → `"case_count": 0`, `"case_counts": {}`
- `outputs\v4_2026_compare86_fixed\input_quality.json` → `"case_count": 0`, `"case_counts": {}`
- `outputs\v4_2026_compare86_fixed2\input_quality.json` → `"case_count": 100`

The third run succeeded with the same script and the same recorded invocation. **The artifact is real but the recorded provenance does not explain it**, and no script on disk can regenerate it. Also note `round_2026.zip` contains 495 entries and **zero** `.py` files — the source is not archived with the result.

**What *is* independently reproducible:** the 2026 case *selection*. Recomputing the year's best `high/low−1` interval per code directly from `mainboard_tencent_daily_2025_20260828.csv` (505,600 rows for 2026, 3,193 codes) returns a top-50 that matches `round_2026\case_manifest.csv` gain_top50 **exactly, 50/50**, including the interval returns (e.g. 603629 → 7.960416666666667). So the manifest content is correct; only the code that produced the scores is missing.

### 2.6 The project's own files contradict the success record

`V08_SUCCESS_RECORD.md` says this is "the first four-year run in this project that clears the requested 60% gain-distance and <=10/50 loss-alert gates in every year." Its own sibling directories say otherwise:

- `…\v4_insample\FINAL_STATUS.md`, `OVERALL_GATE.md`, `round_overall\REPORT.md`: the unified rule is **85/150 = 56.7% → NOT_PASS**.
- `…\overall_yearwise_ensemble\REPORT.md`: the frozen per-year combination is **105/150 = 70.0%** — and it explicitly notes that `round_overall` only reaches 85/150.
- `…\annual_rule_probe_scratch_20260907\INDEPENDENT_RESULT.md` and `cross_year_lockbox_results\FAST_REPORT.md`: with the target year excluded from fitting **and** threshold selection, ±10 hits are **2023 = 17/50, 2024 = 2/50, 2025 = 15/50** (loss 0/50 throughout). `PARENT_NOTE.txt`: *"No target year reached 30/50. v4 31/35/39 is same-year in-sample only."*
- `…\share_2023_2026_training_20260908\strategies\strict_lockbox\REPORT.md`: 24 variants, **0** pass.

---

## 3. Numbers that do NOT reconcile

Each row: the same quantity, two different values, both paths. **Not averaged, not resolved.**

**3.1 — V08 gain rate for 2023-2025: 31/35/39 vs 17/2/15.**
- `31/50, 35/50, 39/50` — `…\V08_SUCCESS_RECORD.md`; `…\yearwise_gain_avoid_loss_2023_2025_v4_insample\FINAL_STATUS.md`; `…\overall_gate.json`
- `17/50, 2/50, 15/50` — `…\annual_rule_probe_scratch_20260907\cross_year_lockbox_results\FAST_REPORT.md`; `…\fast_summary.json`; `…\PARENT_NOTE.txt`; also repeated in `…\v4_insample\FINAL_STATUS.md` under "Strict cross-year lockbox"
- The first pair is same-year in-sample; the second excludes the target year from fitting and threshold selection. Both are on disk, describing the same 150 cases and the same ±10 metric.

**3.2 — The unified V08 rule: 85/150 = 56.7% vs 105/150 = 70.0%.**
- `85/150 = 56.7%` — `…\v4_insample\round_overall\REPORT.md`; `FINAL_STATUS.md`; `OVERALL_GATE.md`
- `105/150 = 70.0%` — `…\v4_insample\overall_yearwise_ensemble\REPORT.md`
- Same 150-case denominator, same project, same ±10 metric, two different numbers, two different directories. The ensemble report is explicit that `round_overall` reaches only 85/150.

**3.3 — The loss gate: `<= 24/50` vs `<= 10/50` vs actual `0/50`.**
- `跌幅±10误触 <= 24/50` — `…\v4_insample\OVERALL_GATE.md`; `…\v4_insample\overall_gate.json` (`"loss_false_pm10_limit": 24`)
- `the 10/50 loss-alert limit` — `D:\xm\60日预测\09_bull_lowzone_model\V06_ROUND_REPORT.md`
- Actual optimised value `0/50` — every `overall_gate.json` year entry (`"loss_false_pm10": 0`)
- The machine gate is 24/50; one human report calls it 10/50; the value that was actually selected against is 0/50. `LOSS_FALSE_LIMIT = 24` in `yearwise_gain_avoid_loss_training_v3.py`.

**3.4 — 2026 "31/50" means two different things.**
- `gain_hits_pm10_top50 = 31` with `gain_hits_pre10_top50 = 24` — `D:\xm\60日预测\outputs\v3_yearwise_charts86\SUMMARY_ALL.csv` (V07 lineage, symmetric metric)
- `gain_hits_pm10 = 33` with pre10 = 28 — `D:\xm\60日预测\outputs\v4_2026_compare86_fixed2\round_2026\summary.json` (V08 lineage)
- `V08_SUCCESS_RECORD.md` cites 33; `TRAINING_VERSION_INDEX.md` V08 row also cites 33; but V07's own report claims 24/50 for 2026. The number "31" for 2026 appears in the V07 files and "33" in the V08 files; **neither is the same metric as V07's own 24/50**.

**3.5 — V03 denominator: 100 vs 50.**
- `2023 69/100, 2024 100/100, 2025 91/100, overall 181/300 = 60.3%` — `…\yearwise_causal_ml_training_2023_2025_v1\OVERALL_GATE.md` + `run_summary.json` (via `D:\xm\60日预测\05_annual_training_lockbox\yearwise_causal_ml_training.py`)
- `2023 4/50, 2024 24/50, 2025 22/50` — `…\yearwise_gain_avoid_loss_2023_2025_v2\OVERALL_GATE.md`
- Splitting the v1 pool by bucket shows why: 2023 gain 23/50 but loss 46/50; 2024 gain 50/50 and loss 50/50; 2025 gain 43/50 and loss 48/50. The "100/100" is a 100-case bucket where **half the cases are loss cases scored by the same `hit_pm10` test**. It is not comparable to any 50-denominator gain figure, yet `TRAINING_VERSION_INDEX.md` presents it alongside them.

**3.6 — 2026 gate: "通过" vs "未达闸门".**
- `2026: 涨幅±10 33/50 = 66.0%；跌幅误触 0/50；通过` — `D:\xm\60日预测\outputs\v4_2026_compare86_fixed2\OVERALL_GATE.md` (per-year line, and `"qualified": true`, `"overall_training_admitted": false` in `overall_gate.json`)
- `结论：未达闸门，不运行 overall。` — **the same file**, conclusion line
- The same 390-byte file both passes and fails 2026. `overall_gate.json` sets `"overall_training_admitted": false` because a single year can never satisfy `set(years)=={2023,2024,2025}` (script line 166). The per-year "通过" is therefore meaningless in that context but is exactly what the success record quotes.

**3.7 — V03 "pass" on three cases.**
- `2023: 涨幅±10 2/3 = 66.7%；跌幅误触 0/3；通过` with `"cases": 6` and `chart_count: 6` — `…\yearwise_gain_avoid_loss_2023_2025_v3_probe\OVERALL_GATE.md` + `overall_gate.json`
- Against `50` per bucket everywhere else. A three-case smoke run is presented with the same "通过" verdict string as a full run.

**3.8 — V00 denominators presented as one.**
- `trend 75/84, breakout 70/84, and range 29/84` — `D:\xm\60日预测\docs\TRAINING_VERSION_INDEX.md` line 7
- `counted_stocks` = 84 (trend), 82 (breakout), **36** (range) — `…\output_86_real\tencent_results\accuracy_summary.csv`
- `range` has `signal_precision = 0.805556` over 36 stocks and `overall_stock_success_rate = 0.345238` over 84. Writing "range 29/84" merges the two: 29 is the numerator over 36, presented over 84.

**3.9 — "60/84" means two different things.**
- `60/84` = ±10 held-out hits — `…\price_action_cv_reversal_broad_86_v3\summary.csv` (`heldout_hit_pm10 = 60`), and `…\price_action_final_tiers_86_v2\CV_REPORT.md`
- `60/84` = a **date concentration count** — `…\sparse_trough_signal_search_86\REPORT.md`: *"60/84 个锚点在1月，其中 36/84 个恰好是2026首个交易日（1月5日）"* ("60 of 84 anchors are in January, 36 of them exactly the first 2026 trading day")
- Both numbers are correct in their own context; the collision makes `60/84` unreadable without the path.

**3.10 — 2026 outcome target vs anchor-distance target disagree inside one run.**
- `gain_success20` 2024 = 34/50 (extra_trees), 2025 = 47/50 (logistic) — `…\original86_outcome20_model_lockbox_20260910_v2\best_by_year.csv`
- In the very same run, `gain_hit_pm10` = 12/50 (2024) and 9/50 (2025) — same file
- A model that "succeeds" 47/50 on one target hits the anchor window only 9/50 on the other. Reporting either without the other is a denominator/target substitution.

**3.11 — Failed predecessor runs left adjacent to the published one.**
- `outputs\v4_2026_compare86\input_quality.json` → `"case_count": 0`
- `outputs\v4_2026_compare86_fixed\input_quality.json` → `"case_count": 0`
- `outputs\v4_2026_compare86_fixed2\input_quality.json` → `"case_count": 100`
- Three sibling directories, the first two empty, all cited by the same evidence chain. No log records what was "fixed" or what changed between them.

---

## 4. Independent CV / lockbox results

Search terms used: `lockbox`, `锁箱`, `cross_year`, `交叉`, `grouped`, `walkforward`, `probe`, `INDEPENDENT`, `FAST_REPORT`. Every hit with an exact fraction:

| Result | Exact fraction | File path |
|---|---|---|
| **Strict cross-year lockbox (target year excluded from fitting AND threshold selection)** | 2023 **17/50**, 2024 **2/50**, 2025 **15/50** (±10, loss 0/50 each). *"No target year reached 30/50."* | `…\annual_rule_probe_scratch_20260907\cross_year_lockbox_results\FAST_REPORT.md`, `fast_summary.json`, `fast_lockbox_leaderboard.csv` (12 rows), `fast_lockbox_ranked.csv` (12 rows), `fast_lockbox.py` (uses `GroupKFold(5)` over `year+"_"+code`); summary in `…\annual_rule_probe_scratch_20260907\PARENT_NOTE.txt` and `INDEPENDENT_RESULT.md` |
| **Independent grouped cross-score probe** | 2023 **26/50**, 2024 **33/50**, 2025 **39/50** (±10, loss 0/50). Best diagnostic: RF + second_confirm. | `…\annual_rule_probe_scratch_20260907\INDEPENDENT_RESULT.md`; repeated in `…\v4_insample\FINAL_STATUS.md` |
| **Strict lockbox sweep** | 24 variants, 20,945 rows, **0** passing all three gain years ≥30/50 with loss false <25/50. Best test_gain_pm10 by target year: 2023 max **8**, 2024 max **14**, 2025 max **22**. | `…\share_2023_2026_training_20260908\strategies\strict_lockbox\REPORT.md` + `sweep_ranked.csv` |
| **Augmented lockbox** | 24 variants, 72 rows, **0** passed. | `…\share_2023_2026_training_20260908\strategies\augmented_lockbox\REPORT.md` |
| **Walk-forward (train 2024 → validate 2025 → frozen test 2026)** | Validation ±5 precision **74.5% (35/47)**. **Test 2026: 80 alerts, hits_pm10 = 10 → precision 12.5%, coverage 11.9%, late false alerts 70, median abs distance 121.0 days, abstentions 4.** | `…\walkforward_primary_bottom_86\REPORT.md` + `summary.json` |
| **R01 logistic lockbox (train 2023-2025, test 2026)** | Test 2026: gain ±10 **7/50 = 14.0%**, pre-10 5/50 = 10.0%, loss false **48/50 = 0.96**. Train: 7/50, 12/50, 19/50. | `D:\xm\60日预测\outputs\v1_full_logistic_2026\rounds\R01_logistic_2026_lockbox\summary_test.csv` + `summary_train.csv` + `parameters.json` |
| **Chronological outcome-target lockbox** | 2024/120 extra_trees **34/50** gain_success20 (0.68), gain_hit_pm10 **12/50**; 2025/120 logistic **47/50** gain_success20 (0.94), gain_hit_pm10 **9/50** | `…\original86_outcome20_model_lockbox_20260910_v2\REPORT.md`, `best_by_year.csv`, `frontier.csv` |
| **Annual price-zone lockbox** | All rows **NOT_PASS**; 2024/2025 prior-year-only training; 2023 within-year diagnostic | `…\original86_annual_pricezone_lockbox_20260910_v2\REPORT.md` + `summary.csv` |
| **Factor ladder lockbox** | **NOT_PASS**; 2023 1/50, 2024 8/50, 2025 5/50 (±10) | `…\original86_factor_ladder_lockbox_20260910_v1\REPORT.md` |
| **Causal factor score lockbox** | **NOT_PASS**; 2023 19/50 (within-year), 2024 3/50, 2025 18/50 | `…\causal_factor_score_lockbox_20260910_v1\REPORT.md` |
| **Active tier score lockbox** | All zeros, **NOT_PASS** | `…\active_tier_score_lockbox_20260910_v1\REPORT.md` |
| **Gain/avoid-loss factor rounds v3** | *"At least one round passed the research screen: False"*; gain_hit_pm10 mostly 0-2/50 | `…\original86_gain_avoid_loss_factor_rounds_20260910_v3\REPORT.md` |
| **Multi-round factor ladder search** | 2023 19/50, 2024 1/50, 2025 22/50, loss 0/50 each, **NOT_PASS** | `…\multi_round_factor_ladder_search_20260910_v1\REPORT.md` |
| **Adaptive ladder v2** | All variants **NOT_PASS**, max gain 27/50 (2024 wide) | `…\original86_adaptive_ladder_v2_20260910\REPORT.md` |
| **Oracle feasibility upper bound** | max_gain_at_loss10 = **36 / 29 / 27** (2023/2024/2025); `min_loss_budget_for_gain40` = 14 / 21 / 23. *"no factor threshold can satisfy the requested target."* | `…\original86_allbars_outcome20_upperbound_20260910_v2\ORACLE_FEASIBILITY_REPORT.md` + `oracle_feasibility_summary.csv` |
| **Independent 60-day causal rule search** | gain_cases 200, gain_signals 167, gain_hits 40 → rate **0.20**; loss_false 68 → rate **0.34**; `"qualified": false` | `…\git_model_search_rules_20260915\REPORT.md` |
| **Multi-tier in-sample score** | Best rule ±5 **37/84**, ±10 **41/84**; 58 signals, 26 abstentions; target (±5≥51, ±10≥61) **未达标**; explicitly "样本内拟合" | `…\multi_tier_in_sample_score_86\REPORT.md` |
| **2026 multi-tier frontier** | ±5 **58/84**, ±10 **61/84**, 61 alerts, precision_pm10 1.0; study string says anchors only rank historical fit (**in-sample**) | `…\share_2023_2026_training_20260908\strategies\2026_multi_tier_frontier\summary.json` + `REPORT.md` |
| **Rolling forward, two-stage package** | 2024 gain recall **10/50** (loss false 14/50); 2025 **29/50** (28/50); 2026 **12/50** (9/50); *"本轮不是80%达标结果"* | `…\top50_two_stage_package_20260909\run\REPORT.md` + `summary.csv` |
| **Four-year training package** | 3 rolling experiments; strict rolling precision 28.9% / 47.4% / 100% (only 2 signals) / 76.9% (13 mature, 34 pending); anchor-supervised target-year precision 2024 = **0/6**, 2025 = **0**, 2026 = **2/17**. *"任何事后用目标年锚点挑门槛得到的 80% 以上数字都属于前视上限."* | `…\four_year_training_package_20260909\README_CN.md` + `summary.json` |
| **Random-anchor noise control** | 300 rows (2 noise types × repeats × 3 systems). Under `random_anchor_same_stocks`, trend precision is unchanged at 0.892857 (identical to the real run), while range moves 0.8056 → 0.5435 and breakout 0.8537 → 0.9250. | `…\output_86_real\tencent_results\noise_random_anchor.csv` |
| **Synthetic self-test (not real A-shares)** | trend 21/84 = 0.25, range 6/20 = 0.30, breakout 20/51 = 0.392 | `D:\xm\_a_share_86_custom_50pct\a_share_86_custom_50pct\output_synthetic_selftest\accuracy_summary.csv` + `RESULTS.md`; `run_manifest.json` has `"mode": "synthetic_self_test"`. **`SYNTHETIC_ONLY_WARNING.txt` states these are synthetic and must not be cited as real-stock accuracy.** |

**Reading of Section 4.** Honest cross-year out-of-sample evidence exists on disk, is documented in the same repositories as the V08 claim, and contradicts it. The consistent picture from every independent method — strict lockbox (17/2/15), walk-forward frozen test (10/80 = 12.5%), R01 logistic lockbox (7/50 = 14.0%), the two lockbox sweeps (0 of 48 variants pass), the independent rule search (qualified: false) — is **no cross-year generalisation**. The oracle frontier (max 36/29/27 at a 10/50 loss budget) shows the 60%-of-50 target is not reachable even by a perfect selector under the stated loss constraint.

---

## 5. Blunt verdict per version

- **V00 — Partially.** The numbers 75/84, 70/84, 29/84 reproduce exactly from `accuracy_summary.csv`, but they are three different denominators presented as one, and the underlying run is a single retrospective 2026 event-window pass, not a forecast.
- **V01 — No (nothing to verify).** No version-scoped claim with a headline fraction exists; the index's "exploratory" label is accurate and no stronger claim is made.
- **V02 — Partially.** 52/84 (±5) and 60/84 (±10) reconcile exactly across the five stock-grouped folds and the same rule was chosen in all folds, which is real methodological strength — but the anchor is a post-hoc 2026 maximum-rise path, 53 of 84 anchors sit on one January date, and the companion outcome table covers only 62 of the 84 stocks.
- **V03 — No.** The "60.3%" headline is computed over a 100-case bucket that merges gain and loss cases, and the only "通过" run with a clean 50-denominator is a three-case smoke test; the index itself declines to accept it.
- **V04 — No.** Every lockbox ladder on disk reads NOT_PASS, both sweep packages pass 0 of 48 variants, and the oracle upper-bound report independently shows the target is unreachable.
- **V05 — No (nothing to verify).** Tooling and chart generation only; no scored claim exists.
- **V06 — Yes, as a reported failure.** The published 0/5/6/25 and 50/41/49/36 match `summary.csv` exactly, and the run is correctly stamped NOT_PASS.
- **V07 — Yes, as a reported failure.** 4/12/13/24 and 18/4/40/47 match `SUMMARY_ALL.csv` exactly — though V07 has no row at all in `TRAINING_VERSION_INDEX.md`, so its failure is not carried into the project's own version history.
- **V08 — No, as stated.** The four fractions are reproducible from `signal_results.csv`, but the label "pre-anchor -10..0" is false (the code uses a symmetric ±10, and the true strictly-pre-anchor values are 18/29/32/28 — so 2023, 2024 and 2026 fail the project's own 60% gate), the "0/50" loss figure is denominator inflation over 4/18/11/19 actual loss signals, the "original 86 stocks" universe claim is false for 2023-2025 (1-4 of 50 cases overlap) while 2026 is drawn entirely from a winner-biased list whose membership was chosen on that year's outcome, the run self-declares `same_year_in_sample` and `ranking_is_retrospective`, and the project's own strict cross-year lockbox reports 17/2/15 against the claimed 31/35/39. The 2026 leg is additionally **not reproducible from its recorded command**: the cited script hardcodes `[2023,2024,2025]` and no script on disk can regenerate the 2026 manifest.
- **R01 — Yes, as a reported failure, and it is the project's most honest artifact.** A genuine disjoint-year lockbox (train 2023-2025, test 2026) that fails outright: 7/50 = 14.0% ±10 against a 60% gate, with 48/50 = 96% loss false alerts.
