# Other Projects Audit — Out-of-Sample Evidence Review

**Audit date:** 2026-09-16
**Scope:** three local projects audited read-only
1. `D:\xm\ly\` (incl. `.worktrees/positive-recall-specialist/`)
2. `D:\xm\a_share_intraday_lab\`
3. `D:\xm\exports\Luna_Max_Kline_Practice_Web_Pro_20260818\`

**Method:** code read directly, not just docs. Where a document and the code disagree, the code wins and the disagreement is reported. All test counts and hashes were **recomputed locally** rather than quoted from docs. Nothing under `D:\xm` was modified.

**Headline result:** **none of the three projects contains a validated, reproducible strategy with real out-of-sample evidence.** This matches the sibling project's pattern. Two of the three are unusually honest about this themselves; one (`a_share_intraday_lab`) has the best-designed protocol of the three but fails its own gate and violates its own test-period reuse rule.

---

## Project 1 — `D:\xm\ly\` (Luna Max)

### 1.1 Purpose and scope

Luna Max is a research engineering repo for A-share main-board limit-up event prediction, with four independent binary tasks (`limitup`, `rise`, `top60`, `reversal`), a LightGBM baseline, an execution-only backtest, and a Transformer control API.

`README.md:50` (the project's own scope statement):

> Luna Max 是一个带数据审计、时间切分、LightGBM 基线、执行回测和 Transformer 对照训练 API 的研究工程。当前仓库没有真实行情 bundle 和真实模型指标；合成数据只用于接口、审计和回归 smoke，不能据此声称策略有效、预测有效或有收益。

("Luna Max is a research engineering project with data audit, time splitting, a LightGBM baseline, a backtest, and a Transformer control-training API. **The current repository has no real market-data bundle and no real model metrics**; synthetic data is used only for interfaces, audits and regression smoke tests, and no strategy validity, predictive validity, or profit may be claimed from it.")

`README.md:39-40`, on the one real experiment it defines:

> The manifest marks this fixed cutoff cohort as `cohort_hindsight=true`; it is a retrospective experiment, not a live-trading claim.

`PLANNING.md:34`:

> 当前仓库未提供真实行情 bundle，也没有可引用的真实模型指标。因此所有阶段的真实硬门槛均不能标记为通过，策略有效性保持未判断。

("The current repository provides no real market-data bundle and no citable real model metrics. Therefore no stage's real hard gate can be marked as passed; strategy validity remains undetermined.")

**Code corroborates this.** The repo root's `runs/legacy_baseline_20260819_retry1/metrics.json:137` is the only frozen official test in the main tree and it reads `"overall_pass_gate": false`.

### 1.2 Strategy inventory

The main tree (`D:\xm\ly\`) contains **infrastructure, not strategies**. There is no `experts/` directory at the root. The strategy content lives in the worktree.

| # | Name | File | What it does (from code) | Type |
|---|---|---|---|---|
| 1 | **LightGBM 4-task baseline** | `models/lightgbm_baseline.py:28-33` | Four independent binary classifiers keyed to labels `y2_seal`, `y_rise5`, `y_reversal`, `top10_60` | ML model |
| 2 | **Multi-branch Transformer** | `models/transformer.py`, `models/transformer_training.py` | Causal TCN + Transformer, daily/weekly/scalar branches, PIT sequence assembly | ML model (control arm, no CLI) |
| 3 | **Event sequence classifier** | `models/event_sequence_classifier.py` | 60×35 causal sequence CNN/GRU classifier; `shuffle=True` at line 1004/1060 is a **training DataLoader**, and `validation_loader` at 1012 is `shuffle=False` — batch shuffling, not a shuffled split | ML model |
| 4 | **raw_v49 / raw_v50 ExtraTrees benchmark** | `.worktrees/positive-recall-specialist/scripts/run_precision70_raw_factor_benchmark.py` | 49 (or 50) causal raw daily factors → ExtraTrees 360 trees, `max_features=0.70`; selects by fixed coverage | ML model (this is the only one with real forward numbers) |
| 5 | **Screener 4 boards** | `screener/screener.py:901-1017` | `limitup` (`next_day_seal`), `rise5`, `rise10`, `reversal`, `top60` boards; risk pre-filter + raw-score ranking (calibration display-only) | Rule + model hybrid (consumes model scores) |
| 6 | **38 expert rule strategies** | `.worktrees/positive-recall-specialist/experts/strategies/*.py` | 20 base rule scorers + 16 `strict_*` wrappers + 2 `__init__`/`_strict_selector` helpers. `_strict_selector.py:17` is a pure re-threshold: `base = base_predict(card)` then `int(base.score >= threshold)` — **no new signal** | Rule (the 16 `strict_*` are not distinct strategies) |
| 7 | **Execution-only backtest** | `backtest/backtest.py`, `pipeline/run_backtest.py` | Consumes given predictions; enforces T+1, fees, slippage, capacity, and manifest/OOS gates | Engineering (no signal of its own) |

**Distinct strategies in ly:** essentially **4 ML tasks + 1 ExtraTrees event benchmark + 4 screener boards + 20 distinct rule scorers**, i.e. the "38 strategy files" count overstates distinct logic by ~16.

### 1.3 Evidence quality — THE KEY SECTION

This is where `ly` differs sharply from a naive in-sample project: it *does* have a genuine frozen-holdout artifact. **And that artifact failed.**

| Result | Path | Exact number | Classification | Justification |
|---|---|---|---|---|
| Official frozen 2025 test, T-1 | `D:\xm\ly\runs\legacy_baseline_20260819_retry1\metrics.json:98` | accuracy **0.7134741814003958** | **REAL_OUT_OF_SAMPLE** | Genuine pre-registered holdout. `metrics.json:33` `"threshold_selection": "validation_pass_gate_then_beat_majority_then_accuracy_then_balanced_then_tp_then_stable_tie_break"`; `audit.json:159-164` fixes `"2025": "official_test"`; `official_test_lock` file + `official_test: true` + `sample_hash`/`frozen_hash` present. **The protocol is real.** |
| ↳ same, gate outcome | same file, line 116 | `"pass_gate": false` | **REAL_OUT_OF_SAMPLE (failed)** | `"beat_majority": false` — 0.7134741814003958 vs `"majority_baseline": 0.7150698921299546`. It **lost to the majority baseline.** |
| ↳ T+1 arm | same file, line 73 | `"pass_gate": false`, accuracy 0.8828637591663451 vs majority 0.8837643123633089 | **REAL_OUT_OF_SAMPLE (failed)** | Also loses to majority; `positive_recall` 0.01715550636413946. |
| T-1 development 2022 | `.../runs/precision70_raw_factor_benchmark_tminus1_v2/metrics.json:28` | precision **0.8270676691729323** (220/266) | **IN_SAMPLE_FIT** | This is the *selection* year. `metrics.json:145` `"selection": "raw score threshold frozen on 2022; no annual percentile"`. Selected for and reported on the same data. |
| ↳ validation 2023 | same, line 123 | precision **0.6715328467153284** (92/137), `"passed": false` | **REAL_OUT_OF_SAMPLE** | Strictly later, threshold frozen before. **Fails the 0.70 gate.** |
| ↳ outer 2024 | same, line 135 | precision **0.6088709677419355** (151/248), `"passed": false` | **REAL_OUT_OF_SAMPLE (exposed)** | Later period, but `metrics.json:3` role is `"event_conditioned_development_and_exposed_historical_check"` — already-exposed, not blind. |
| High-confidence tier 2024 | same, lines 173-183 | precision **0.6904761904761905** (58/84), `combined_gate_passed: false` | **REAL_OUT_OF_SAMPLE (failed)** | `"precision_rate_passed": false`; below 0.70. |
| **Frozen 2026 forward check** | `.../runs/precision70_2026_forward_check_v1/metrics.json:14` | threshold frozen, then 2026 evaluated | **REAL_OUT_OF_SAMPLE (failed)** | The strongest attempt: `"training_boundary": "train labels label_end < 2025-01-01; 2025 selects fallback threshold; **2026 labels never used for fitting or selection**"`. |
| ↳ 2026 T+1 result | same, lines 240-254 | precision **0.4152542372881356** (49/118), `"combined_passed": false` | **REAL_OUT_OF_SAMPLE (failed)** | `"precision_passed": false`, `"recall_passed": false`. 41.5% vs a 70% gate. |
| 2026 T-1 result | `.../hunter_v3_freeze_audit_20260825/manifest.json` `baseline_metrics_summary.forward_2026_exposed.tminus1` | precision **0.5239616613418531** (164/313), active_days 106 | **REAL_OUT_OF_SAMPLE (failed)** | ~52% against a 70% gate. |
| Luna practice-quiz expert scores | `exports/Luna_Max_.../expert_evaluation/scores.json` | accuracies 0.38–0.60 | **ENGINEERING_ONLY / IN_SAMPLE_FIT** | See Project 3. |
| Synthetic pipeline results | `scripts/make_synthetic.py`, `PLAN_DETAIL.md:58-62` | n/a | **SYNTHETIC** | `PLAN_DETAIL.md:66`: "命令索引中的合成训练和回测只验证工程链路，不提供真实策略结论." |
| Test/manifest/hash results | `tests/`, `models/artifacts.py` | e.g. `368 passed` | **ENGINEERING_ONLY** | No strategy claim. |

**The essential finding:** `ly` has the *methodology* of a validated project — purged rolling windows, frozen thresholds, manifest-bound OOS flags, an official-test lock — and its own artifacts report that **every honest out-of-sample evaluation failed**, most of them badly. The 82.7%/92.8% development numbers are the selection year and must not be quoted as performance.

The worktree docs agree and refuse to spin this. `hunter_v3_freeze_audit_20260825.md:13`:

> 当前状态为 **`FROZEN_FOR_AUDIT_ONLY`**，不是 `accepted`、不是 `acceptance_ready`，也不是全市场可交易结论。

`hunter_v3_baseline_evidence_review_20260825.md:120` (the "what not to claim" list) names the exact claims that are unsupported:

> 当前 248 天全市场 yes 的 accuracy≥70% solution、T-1 全市场可交易 launch signal、真实 v2 router/calibration 已完成、acceptance/sealed 已建立、由事件条件 precision 外推到全市场

`precision70_audit_20260820.md:31-34` states the cohort defect plainly, and lines 130-132 close the door on further tuning:

> Further tuning on 2023/2024 labels would convert those years into training data and cannot provide a new out-of-sample claim.

### 1.4 Look-ahead / methodology defects

Grepped across `ly` (excluding `.git`, `__pycache__`, `data`, `artifacts`) for `shift(-`, `future`, `anchor`, `label`-as-feature, `train_test_split`, `cross_val_score`, `shuffle`, `.iloc[-1]`, forward indexing.

**Findings — the causality discipline here is genuinely strong:**

| Pattern | Hits | Assessment |
|---|---|---|
| `train_test_split` | **0** | Never used. Splitting is chronological (`pipeline/cohort_experiment.py:377`). |
| `cross_val_score` | **0** | Never used. |
| `shift(-` | **2** (1 real, 1 mirrored in `exports/`) | `pipeline/cohort_experiment.py:377`: `work["future_last_date"] = work.groupby("code", sort=False)["date"].shift(-label_buffer)`. **This is a leak *guard*, not a leak** — it computes each row's label-window end so the code can assert it falls before the next split. |
| `shuffle=True` | 23, all benign | All are training `DataLoader` batch shuffling (`models/event_sequence_classifier.py:1004`), with the matching `validation_loader` `shuffle=False` at line 1012. `DateBatchSampler(..., shuffle=True, seed=17)` in tests is date-grouped sampling. **No shuffled time-series split exists.** |
| Label-as-feature | 0 real | Actively prevented: `models/lightgbm_baseline.py:36-72` defines `_OUTCOME_COLUMNS` and six `_FUTURE_FEATURE_PATTERNS`; `validate_feature_names` (line 75-98) raises `ValueError(f"future outcome columns cannot be features: {forbidden}")`. |

**One real defect, already found and documented by the project itself.** `precision70_audit_20260820.md:120-126`:

> ## Invalidated Artifacts
> `precision70_raw_factor_benchmark_v3` and `precision70_stability_search_v1` accidentally included the helper `year` column as a numeric feature. They are retained only for debugging and must not be cited.

The `year` column is added at `scripts/run_precision70_raw_factor_benchmark.py:386` (`frame["year"] = frame["observation_date"].dt.year.astype(np.int16)`) and excluded from features via `_IDENTIFIER_COLUMNS` at line 102. **Trust the code over the docs here in the project's favour:** the current `causal_raw_factor_columns()` at lines 87-110 does exclude it, and the $v49$ factor list in the live `metrics.json:202-252` contains no `year` key. The defect is real but confined to the two invalidated artifacts.

**A second, subtler self-documented defect:** the coverage rule is chosen as a fixed fraction of a whole year's rows, which is not knowable online. `hunter_v3_freeze_audit_20260825.md:29`:

> `fixed_global_selection()`（约 158-173 行）按整个目标年样本的分数排序后取覆盖率；当前主结果的覆盖率选择为 2022 年的 1.7%，然后原样应用到 2023/2024。

Code confirms at `run_precision70_raw_factor_benchmark.py:170`: `picks = min(len(frame), max(1, int(np.ceil(len(frame) * float(coverage)))))` — a whole-year quantile. The manifest lists this as blocker `I3_global_year_coverage_not_online`.

**Honest boundary, stated by the project:** the T-1 cohort is hindsight-conditioned. `precision70_audit_20260820.md:31-34`:

> The cohort itself is hindsight-conditioned: at T-1, a live scanner cannot know which stocks will form the next day's limit-up-event cohort. Results therefore measure continuation ranking inside a historical event cohort, not deployable whole-market stock selection.

### 1.5 Test and hash claims verified

The task brief says `ly` "reportedly claims 21/21 tests". **That claim does not exist as stated, and the real number is far larger.**

- `MANIFEST`-style greps for `21/21` across `ly`, `intraday_lab`, and `exports` return **0 hits**.
- The "21" figures in the experiment docs are **per-file counts from specific targeted test files on specific dates**, not a project-wide suite claim. Example: `hunter_v3_regression_matrix_20260825.md:21` `| input manifest | test_build_hunter_v3_input_manifest.py | 21 passed | PASS |`.
- **Independently recomputed:**
  - `D:\xm\ly\tests\` → `def test_` count = **434**; `pytest --collect-only` = **496 tests collected** (15.7s).
  - Worktree `.worktrees\positive-recall-specialist\tests\` → **2,289 tests collected** across 148 test files.
  - Full repo collection (incl. `artifacts/**`) → **505 collected, 5 collection errors** in `artifacts/agent_*/test_*.py` (stale `ModuleNotFoundError` for `artifacts.agent_pretrained_sequence.run_pretrained_sequence`). Worth noting: the root suite is **not** clean out of the box.
- **The "21" claim is stale where it is checkable.** Re-collecting the two files the docs cite at 21:
  - `tests/test_write_shadow_prediction_batch_v1.py` → **22 collected** (`hunter_v3_batch_writer_final_acceptance_20260825.md:16` says `21 passed`).
  - `tests/test_build_hunter_v3_input_manifest.py` → **25 collected** (`hunter_v3_regression_matrix_20260825.md:21` says `21 passed`).
  These are per-date snapshots of a moving tree, and the worktree's own newest report concedes exactly this (`hunter_v3_final_hash_count_latest_20260825.md:140-144`).
- The most recent worktree report gives `368 passed in 13.08s` for a 17-file suite and labels overall status `LOCAL_CONTRACT_PASS / REAL_INPUT_BLOCKED / BLOCKED_FOR_REAL_ACCEPTANCE` (`hunter_v3_final_hash_count_latest_20260825.md:12-15`).

**Hash claims — verifiable, and they FAIL freshness.** I independently recomputed the freeze manifest (`runs/hunter_v3_freeze_audit_20260825/manifest.json`):

| Map | Entries | Match | **Stale** | Missing |
|---|---:|---:|---:|---:|
| `source_files_sha256` | 24 | 23 | **1** | 0 |
| `test_files_sha256` | 12 | 11 | **1** | 0 |
| `run_artifacts_sha256` | 13 | 13 | 0 | 0 |

Stale entries: `data/shadow_prediction_ledger_v1.py` (declared `6afbb659…`, actual `8e8945e3…`) and `tests/test_shadow_prediction_ledger_v1.py` (declared `a1630c44…`, actual `6ed886b2…`). **This reproduces the project's own finding exactly** (`hunter_v3_final_hash_count_latest_20260825.md:73-78`), which is a point in favour of the docs' reliability. The real-run artifacts are all still fresh — meaning nothing was actually run.

**Supply-chain verdict for `ly`: the hash chain is genuine and locally verifiable, but it certifies an *unrun* pipeline.** `manifest.json` `status = FROZEN_FOR_AUDIT_ONLY`, `checks.training = not_started`, `scope.long_training_started = false`, `evidence.v2_run_artifact_scan.matched_count = 0`.

### 1.6 Verdict — `ly`

**NO — no validated strategy, and the project says so itself.**

- **Strongest evidence FOR:** a genuine, pre-registered, lock-file-protected out-of-sample protocol exists and was executed. `runs/legacy_baseline_20260819_retry1/metrics.json` carries `"official_test": true`, `"official_test_year": 2025`, an `official_test_lock` path, `sample_hash` and `frozen_hash`, with `audit.json:159-164` fixing `"2025": "official_test"` and `"2024": "validation"`. Threshold selection ran only on validation (`"threshold_selection": "validation_pass_gate_then_beat_majority_…"`). This is real methodology, not in-sample dressing.
- **Strongest evidence AGAINST:** that protocol reported **failure on its own terms**. `metrics.json:116` `"pass_gate": false`, and the T-1 arm's accuracy `0.7134741814003958` is **below** its own `"majority_baseline": 0.7150698921299546` with `"beat_majority": false`. The frozen 2026 forward check then produced `0.4152542372881356` precision against a 0.70 gate (`precision70_2026_forward_check_v1/metrics.json:243,250`). The only strong numbers (82.71%, 92.79%) are the **selection year**, and the project's own audit forbids citing them.

---

## Project 2 — `D:\xm\a_share_intraday_lab\`

### 2.1 Purpose and scope

A one-minute intraday A-share strategy search package with a deliberately falsifiable gate. `README.md:3-5`:

> 当天盘中按照一分钟K线产生信号并成交，下一交易日开盘卖出，收益率严格大于0是否及格，严格大于5%是否优秀；能否在足够大的样本外数据中找到优秀率严格大于40%的策略？

`README.md:7-18` defines the pre-committed acceptance rule:

> 程序不会预设答案。只有最终未参与调参的测试期同时满足以下条件，才输出 `PROVEN_GT_40`：
> - 测试期前置股票池至少100只；
> - 测试期实际成交至少100笔；
> - 测试期至少20个入场日；
> - 样本外优秀率严格大于40%；
> …
> 未同时满足时，程序输出 `NOT_PROVEN_GT_40` 并逐项列出失败原因，不会为了达到40%而修改测试期参数、删除亏损交易或把不可成交的一字板计入收益。

This is the best-specified protocol of the three projects. Its problem is execution, not design.

### 2.2 Strategy inventory

Source of truth: `src/intraday_lab/strategies.py:13-37` (`SIGNAL_FEATURE_COLUMNS`) and `parameter_grid()` at line 53+.

| # | Name | File:line | What the code does | Type |
|---|---|---|---|---|
| 1 | `pullback_breakout` | `src/intraday_lab/strategies.py:150-175` | Impulse then contraction, then volume expansion: `impulse_range_return >= impulse_min`, `pullback_depth` in range, `pullback_vol_ratio <= contraction_max`, `breakout_vol_ratio >= expansion_min`, `dist_vwap >= 0`, `close_pos >= close_pos_min`, `upper_wick_ratio <= wick_max`, plus rank/breadth gates | Rule |
| 2 | `opening_range_breakout` | `strategies.py:176-194` | `opening_breakout` (gated on `bar_no >= 15`, set in `features.py:241`) and `close > opening_high_15 * (1 + breakout_buffer)` plus trend/breadth gates | Rule |
| 3 | `vwap_reclaim` | `strategies.py:195-208` | `vwap_cross_up` and `prior_low3_to_vwap.abs() <= touch_tolerance` | Rule |
| 4 | `late_strength` | `strategies.py:209-221` | Single-minute signal at `signal_minute` with `below_day_high`, `ret_15`, `day_position` gates | Rule |
| 5 | `near_limit_reseal` | `strategies.py:222-234` | `prior_near_limit_ratio >= prior_touch_ratio`, `to_limit >= current_to_limit_min`, pullback window | Rule |
| 6 | **Execution model** | `src/intraday_lab/execution.py:20-50` | `_attempt_fill` rejects `no_next_bar`, `next_bar_not_same_day`, `next_bar_gap` (>120s), `zero_next_volume`, and `_is_locked_limit_up` (all of O/H/L within 0.15% of limit) | Engineering (not a strategy) |
| 7 | Synthetic generator | `src/intraday_lab/synthetic.py` | Test-data generator | Engineering |

**Distinct strategies: 5** — all rule-based, no ML model anywhere in `src/`. Selection is a grid search over `parameter_grid()`.

### 2.3 Evidence quality — THE KEY SECTION

There are **5** search runs. Every one reports `NOT_PROVEN_GT_40`.

| Result | Path | Exact number | Classification | Justification |
|---|---|---|---|---|
| Best run, test period | `runs/top100_two_week_20260817_20260828_direct/REPORT.md:82` | excellent_rate **40.00%**, n=5 trades | **REAL_OUT_OF_SAMPLE (technically), but statistically void** | Chronological split is genuine (`date_split.json`: train 08-20…08-24, val 08-25, test 08-26…08-27). But the test set is **5 trades over 2 days**, against the project's own `min_test_trades >= 100` and `min_test_days >= 20`. |
| ↳ same, gate | `REPORT.md:94-95` | `excellent_rate 0.4 <= 0.4`; `excellent_wilson_lcb 0.11762077423264783 < 0.3` | **REAL_OUT_OF_SAMPLE (failed)** | Fails on the "strictly greater than" and Wilson-LCB rules. `REPORT.md:5`: `NOT_PROVEN_GT_40`. |
| Alt run, test period | `runs/top100_20260817_20260828/REPORT.md:8` | `opening_range_breakout-0006`, status `NOT_PROVEN_GT_40` | **REAL_OUT_OF_SAMPLE (failed)** | From `selected_strategy.json`: pass_rate 0.4, exc 0.1, lcb 0.0179, mean_return **−0.008047179735634059** (negative). |
| Two relaxed runs | `runs/top100_two_week_..._relaxed/`, `..._relaxed_coverage/` | exc 0.3, lcb 0.1454772448676043 | **REAL_OUT_OF_SAMPLE (failed)** | n=10 trades. One `relaxed` run yields `NaN` for pass/exc/mean — zero resolved trades. |
| Week run | `runs/week_20260824_20260828/` | exc 0.2, lcb 0.03622410863243014 | **REAL_OUT_OF_SAMPLE (failed)** | Train=1 day, val=1 day, test=1 day. |
| `live_reports/2026-09-16_1420_dual_strategy.md` | same path | 24 and 20 candidate rows | **RETROSPECTIVE** | Hand-written same-day report with no labels resolved. Self-flags the gap: line 6 "未留存 14:20 全市场涨幅/量比/换手/市值快照…不能代表全市场涨幅前200"; line 7 "不构成投资建议". |
| `LIVE_SIGNAL.md:47` scale benchmark | `LIVE_SIGNAL.md:47` | 5,000 symbols / 2,400,000 rows, 37.729s, 704 candidates | **SYNTHETIC** | Self-labelled: "该数据是合成压力样本，不是收益证据." |
| `PACKAGE_TEST_RESULTS.txt:12` | same | "End-to-end synthetic smoke run: completed" | **SYNTHETIC** | Line 14: "Synthetic data is only a software test and is not real A-share performance evidence." |
| `self-test` / unit tests | `tests/`, `PACKAGE_TEST_RESULTS.txt:3` | "Unit tests: 8 passed" | **ENGINEERING_ONLY** | No strategy claim. See §2.5 for the count discrepancy. |

**The decisive defect — test-period reuse.** `METHODOLOGY.md:95` sets the rule:

> 若修改策略或参数后再次观察同一测试期，该测试期已经变成开发数据，必须换新的最终测试期。

("If you observe the same test period again after changing the strategy or parameters, that test period has become development data; you must switch to a new final test period.")

**The code violates this four times.** Reading every `date_split.json`:

| Run | test set |
|---|---|
| `top100_two_week_20260817_20260828_direct` | `['2026-08-26','2026-08-27']` |
| `top100_two_week_20260817_20260828_relaxed` | `['2026-08-26','2026-08-27']` |
| `top100_two_week_20260817_20260828_relaxed_coverage` | `['2026-08-26','2026-08-27']` |
| `top100_20260817_20260828` | `['2026-08-26','2026-08-27','2026-08-28']` |

Four runs, four different parameter sets (`near_limit_reseal-0000`, `pullback_breakout-0052`, `opening_range_breakout-0067`, `opening_range_breakout-0006`), **all evaluated on 2026-08-26/27**. By the project's own rule, that window is development data, not out-of-sample. The 40.00% figure is therefore best classified **IN_SAMPLE_FIT after reuse**, even though the split mechanics are correct.

### 2.4 Look-ahead / methodology defects

Grepped `analysis/`, `src/`, `scripts/`, `tests/`, `runs/` for the required patterns.

| Pattern | Hits | Assessment |
|---|---|---|
| `train_test_split` | **0** | Never used. `search.py:28` `chronological_split()` sorts dates (`dates = sorted(dict.fromkeys(dates))`) and slices 60/20/20 — correct. |
| `cross_val_score` / `KFold` | **0** | Never used. |
| `shuffle=True` | **0** | No shuffled split anywhere. |
| `shift(-` | **3, all legitimate** | `features.py:75` `daily["next_trade_open_raw"] = g["day_open"].shift(-1)` and `:76` `daily["next_trade_date"] = g["date"].shift(-1)` build the **label**; `features.py:250` `df[f"next_{col}"] = g[col].shift(-1)` is documented at line 248: `# Next bar is evaluation/execution data. It is never used in a signal mask.` |
| `.iloc[-1]` | 29, in `runs/_*.py` report scripts | "last observed minute" — reading current state, not future state. |
| `future` | 17, all `concurrent.futures` | Thread-pool variables (`analysis/download_minute_top100_sina.py:62` `for i, future in enumerate(as_completed(futures), 1)`), not future data. |
| `anchor` | 3 | Benign. |

**The causality defence is real and tested.** `tests/test_no_lookahead.py:10-28` mutates all future same-day bars (`mutated.loc[same_day_future, ["open","high","low","close"]] *= 1.7`) and asserts earlier features are bit-identical (`pd.testing.assert_frame_equal(..., rtol=1e-11)`). Lines 31-45 multiply `next_day_open` by 99 and assert the signal mask is unchanged. Line 48-73 asserts the opening-range signal does not fire before 15 bars complete. **This is a genuine, executable no-look-ahead guarantee — the strongest of the three projects.**

Two caveats worth stating:
1. `features.py:236-241` computes `opening_high_15` from **all** `bar_no < 15` rows and merges it onto every row including `bar_no < 15`; the guard is the `opening_breakout` conjunction at line 241 (`(df["bar_no"] >= 15) & …`), not the merge. Correct, but relies on the flag rather than on the value being absent.
2. `_is_locked_limit_up` (`execution.py:20-30`) returns `False` when the limit price is unavailable (`if not np.isfinite(limit_up) or limit_up <= 0: return False`), i.e. **fail-open** on missing data — a tradability assumption, not a look-ahead.

**The real methodological defect is sample size, not leakage.** The best test period has 5 trades over 2 days. `METHODOLOGY.md:112-120` requires ≥100 trades and ≥20 days. No reported run came close.

### 2.5 Test and hash claims verified

**Test count discrepancy.** `PACKAGE_TEST_RESULTS.txt:3` claims `- Unit tests: 8 passed`. Independently recomputed:

| File | `def test_` |
|---|---:|
| `tests/conftest.py` | 1 (`def test_cfg():` — a fixture, not a test) |
| `tests/test_dashboard.py` | 1 |
| `tests/test_execution.py` | 2 |
| `tests/test_live_feed.py` | 2 |
| `tests/test_live_signal.py` | 1 |
| `tests/test_live_status.py` | 1 |
| `tests/test_metrics.py` | 2 |
| `tests/test_next_session_label.py` | 1 |
| `tests/test_no_lookahead.py` | 4 |
| `tests/test_split.py` | 1 |
| **Total `def test_`** | **16** (15 real + 1 fixture) |

`pytest --collect-only tests` → **15 tests collected in 2.70s** (the `conftest.py` `test_cfg` is not collected as a test). Restricting to the **six test files the MANIFEST actually covers** (`test_execution`, `test_metrics`, `test_next_session_label`, `test_no_lookahead`, `test_split`, `conftest`) → **10 collected**. The "8 passed" figure is **stale** and matches no current subset. Reported as **NOT_VERIFIED as a current count**; the real current number is **15**.

**MANIFEST.sha256 coverage — genuine format, but the manifest is stale.** Parsed all 32 entries and recomputed every digest:

| Result | Count |
|---|---:|
| Entries | 32 |
| **Hash matches** | **26** |
| **Hash MISMATCHES** | **6** |
| Missing files | 0 |

The 6 mismatching entries:

| File | Manifest | Actual |
|---|---|---|
| `./README.md` | `f971f13148c315f0…` | `641823876e4aea03…` |
| `./pyproject.toml` | `d03e45a4486db55a…` | `138e9e15224f0531…` |
| `./src/intraday_lab/cli.py` | `867ad91aa5fb99f1…` | `c30b18d374423d9d…` |
| `./src/intraday_lab/features.py` | `05ee6e5f54d746bb…` | `61a82ec5b3bab3d9…` |
| **`./src/intraday_lab/strategies.py`** | `222cbc8a599d1c97…` | `d10445792a5724de…` |
| **`./tests/test_no_lookahead.py`** | `58013bcfffdeb9f2…` | `37ef617568c45d2f…` |

**This is the single most important supply-chain finding in this audit.** The manifest was published *before* the strategy code and its no-look-ahead test were edited. The two files that changed include the strategy definitions and the test that certifies causality. **The hash claim is falsified by local recomputation.**

**Coverage gaps.** The manifest covers 32 files. The project contains **7,011** files not listed (excluding `.git`/`__pycache__`), including:
- All docs except `README`, `METHODOLOGY`, `DATA_FORMAT`, `DATA_SOURCES`, `QUICK_START`, `PACKAGE_TEST_RESULTS`: `LIVE_SIGNAL.md`, `EXPORTS`/`analysis/SIGNAL_ANALYSIS_HANDOFF.md`
- **4 of the 10 test files**: `test_dashboard.py`, `test_live_feed.py`, `test_live_signal.py`, `test_live_status.py` (the manifest covers `conftest.py`, `test_execution.py`, `test_metrics.py`, `test_next_session_label.py`, `test_no_lookahead.py`, `test_split.py` = 6 of 10)
- **All of `analysis/`** (the Sina downloaders), **all of `runs/`** (every result), **all of `exports/`**, `config.live.yaml`, `config.top100.yaml`, `config.week.yaml`
- `live.py`, `live_feed.py`, `scale_benchmark.py` — three `src/` modules named in `README.md:45-47` are **not** in `src/` at all; they are absent from the package

**Is there a verification script?** **No.** Grepping all `*.py`/`*.bat`/`*.sh` for `MANIFEST`/`sha256sum` finds no verifier; the hits are `analysis/` downloaders and `scripts/make_chart_index.py`, which generate their own unrelated manifests.

**Supply-chain verdict for `a_share_intraday_lab`: NOT_VERIFIED, and provably stale.** The manifest uses correct `sha256sum` format and 26/32 entries still verify, but the two entries covering **the strategy code and the causality test** fail. There is no script to check it and no evidence any verification was ever run.

### 2.6 Verdict — `a_share_intraday_lab`

**NO — no validated strategy, though the protocol design is the best of the three.**

- **Strongest evidence FOR:** the training/validation/test separation is genuinely implemented in code, not just claimed, and the label cannot leak into features. `search.py:85-93` splits on labeled dates and writes `date_split.json`; `search.py:11` `from .execution import simulate_trades` executes at `t+1`; `tests/test_no_lookahead.py:26-28` proves by mutation that future bars cannot change past features. And the project **refuses to claim success when it fails**: `README.md:18` "不会为了达到40%而修改测试期参数", and all five runs output `NOT_PROVEN_GT_40`.
- **Strongest evidence AGAINST:** the "out-of-sample" result is **5 trades over 2 days evaluated four times on the same dates**, against the project's own requirement of ≥100 trades and ≥20 days — and the same window was reused across four different parameter sets, which `METHODOLOGY.md:95` explicitly forbids. Compounding this, `MANIFEST.sha256` **fails to verify** for `src/intraday_lab/strategies.py` and `tests/test_no_lookahead.py`, so the shipped hash chain does not cover the code that produced the results.

---

## Project 3 — `D:\xm\exports\Luna_Max_Kline_Practice_Web_Pro_20260818\`

### 3.1 Purpose and scope

A local K-line practice quiz — 100 stock cards, 60 qfq bars each — wrapped around a partially-shipped Luna Max export. `PROJECT_README.md:5-8`:

> The practice site presents 100 unique main-board stocks, exactly 50 positive and 50 negative. Each card contains 60 active qfq sessions ending at the observation date. A positive means that the maximum qfq high in the next 10 active sessions is at least 30% above the observation qfq close.

`PROJECT_README.md:41-43`, the honest boundary:

> The next 10 bars and outcome fields remain server-side until an answer is persisted. A refresh restores progress; the new-batch command builds another independently seeded 50/50 session. **Practice results measure the user's decisions, not model accuracy, and are not a trading recommendation.**

`PROJECT_README.md:127` repeats the parent repo's disclaimer verbatim (no real bundle, no real model metrics, synthetic only for smoke tests).

### 3.2 Strategy inventory

**38 files** in `experts/strategies/`, of which **2 are infrastructure**: `__init__.py` and `_strict_selector.py`. That leaves 36 registered strategies: **20 base + 16 `strict_*`**.

The 16 `strict_*` are **not distinct strategies**. `_strict_selector.py:10-34` is the whole mechanism:

```python
def thresholded_decision(card, *, strategy_id, threshold, base_predict):
    """Reuse a causal base score while applying a stricter binary cutoff."""
    base = base_predict(card)
    ...
    return ExpertDecision(strategy_id, card.sample_id, int(base.score >= threshold), base.score, threshold, dict(base.components), rationale)
```

It calls the base strategy and re-thresholds its score; `score` and `components` are passed through unchanged. The `strict_*` modules are ~1.2-1.4 KB each and differ only in `THRESHOLD` (e.g. `strict_bollinger_release_v2.py` threshold 0.952088 vs base `bollinger_squeeze`).

| Group | Names | Type |
|---|---|---|
| Base rule scorers | `accumulation_base`, `atr_trend_follow`, `bollinger_squeeze`, `donchian_turtle`, `first_board_breakout`, `gap_follow_through`, `high_level_consensus`, `leader_momentum`, `limit_up_retest`, `main_wave_acceleration`, `obv_volume_price`, `oversold_rebound`, `platform_breakout`, `pullback_retest`, `relative_strength_rank`, `reversal_engulf`, `rsi_mean_reversion`, `turnover_regime_switch`, `turnover_weak_to_strong`, `washout_complete` | Rule (deterministic score thresholds) |
| Strict wrappers | the 16 `strict_*` files | Rule, **same signal, different cutoff** |
| ML models | `models/lightgbm_baseline.py`, `transformer.py`, `transformer_training.py`, `causal_feature_frame.py`, `evaluate.py`, `artifacts.py` | ML model (present as code) |
| Screener | `screener/screener.py` | Rule + model hybrid |

**Distinct strategies: 20 base rules + 4 ML tasks + 1 screener.** The `strict_*` family inflates the apparent count from 20 to 36 without adding signal.

### 3.3 Evidence quality — THE KEY SECTION

The practice set is derived from **real** BaoStock data. `PROJECT_README.md:24-25`:

> In both modes it verifies the bank and source hashes, then recomputes every selected label from the original qfq stock shard before publishing atomically. **Synthetic sources are rejected.**

Code confirms at `pipeline/build_kline_practice_set.py:637-638`:
```python
if actual_source.get("synthetic") is not False:
    raise ValueError("synthetic source data is not accepted")
```
and the session manifest records `"synthetic": false`, `"source": "baostock 00.9.30"`, `"stock_count": 3357`.

**But the evaluation is in-sample and the selections are stratified.** `build_kline_practice_set.py:611` describes the builder as producing a `"development-only, real-source practice session"`, and lines 660-661 enforce a hard 50/50 balance:

```python
if len(cards) != CARD_COUNT or sum(item["label"] for item in outcomes) != POSITIVE_COUNT:
    raise RuntimeError("practice session balance invariant failed")
```

So the quiz is a **fixed, seed-selected 100-card set** (`seed: 20260817`, `counts: {cards: 100, negative: 50, positive: 50}`), spanning observations **2020-04-27 to 2023-11-24** — squarely inside the 2020-2023 **training** partition that `PROJECT_README.md:21-23` says is the only partition read (`train_labels_2020_2023.parquet`; "validation and sealed-test labels are not read").

| Result | Path | Exact number | Classification | Justification |
|---|---|---|---|---|
| Expert accuracy range (36 strategies) | `.../expert_evaluation/scores.json` | `atr_trend_follow` **0.6** (max), `bollinger_squeeze` **0.38** (min), `turnover_regime_switch` **0.48**; **6** strategies at exactly **0.5** with `predicted_yes_count: 0` | **IN_SAMPLE_FIT** | All 36 expert rules are scored on the same fixed 100 cards; thresholds are per-strategy constants. No held-out period exists. |
| Practice-card labels | `.../outcomes.json` | 50 pos / 50 neg | **RETROSPECTIVE** | Real forward returns, but cards were **selected by outcome** to hit an exact 50/50 split. The forward-looking max is computed at `build_kline_practice_set.py:337-342` (`maximum_return = maximum_high / observation_close - Decimal("1")`). |
| Observed card dates | `cards.json` | 2020-04-27 → 2023-11-24 | **IN_SAMPLE_FIT** | Entirely within the stated training partition. `PROJECT_README.md:22` says validation/sealed-test labels are not read. |
| "sealed_predictions" | `.../expert_evaluation/sealed_predictions/*.json` (36 files) | 36 prediction files | **IN_SAMPLE_FIT** | See below — the seal is an ordering guarantee, not pre-registration. |
| `answers.json` (human play) | `.../answers.json` | 16 answers | **ENGINEERING_ONLY** | User interaction state. |
| `README_WEB_PRO` gate | `PROJECT_README.md:84` | accuracy ≥70% / beat majority | **ENGINEERING_ONLY** | Describes a gate for the parent experiment; not executed here. |
| Positive-only pretraining | `PROJECT_README.md:121-125` | n/a | **ENGINEERING_ONLY** | Doc states it "does not compute accuracy, precision, recall, AUC, a binary decision, or a trading threshold." |

**The "sealed prediction" mechanism is real engineering but is not a pre-registered OOS protocol.** `experts/evaluation.py:263` documents the intent:

```python
"""Generate and hash every prediction before opening the outcome file."""
```

The implementation does enforce ordering: predictions are computed and hashed (lines 279-298), *then* outcomes are read (line 300-302). That is genuine defence against outcome-peeking *within a run*. **But it cannot certify that thresholds were frozen before outcomes were seen**, because:
- The expert thresholds are **source-code constants** compiled into `experts/strategies/*.py`, not runtime-frozen values.
- Nothing external pins them: no timestamp, no signature, no git commit, no third-party anchor. `evaluation_manifest.json` records `prediction_hashes` (36/36) and artifact hashes (39/39) but **no hash of the strategy source or thresholds**.

I verified this is not a hypothetical hole: `sealed_predictions/strict_bollinger_release_v2.json` is a threshold of **0.952088** applied to the `bollinger_squeeze` base score, and the base strategy scores **0.38** accuracy on these very cards. With 11 such `strict_*_v2` variants in the suite, the seal cannot distinguish "threshold pre-registered" from "threshold chosen after seeing these 100 cards". Self-described at `strict_washout_complete_v2.py`: `"100-card exploratory precision scan; development-only"`.

Docs agree the seal is not an OOS claim. `README_WEB_PRO.md:39`: "The 100 cards are a fixed exploratory quiz, not an out-of-sample test."

### 3.4 Look-ahead / methodology defects

| Pattern | Hits | Assessment |
|---|---|---|
| `shift(-` in the practice path | **0** | `build_kline_practice_set.py` uses explicit `visible`/`future` slicing, not shifts. |
| `train_test_split` / `cross_val_score` / `shuffle=True` | **0 / 0 / 0** | Not used. |
| `np.random` | 26, all `default_rng(seed)` for reproducibility | None select cases by outcome. |
| `synthetic` | 88, overwhelmingly **guards that reject** synthetic input | e.g. `build_kline_practice_set.py:637-638`. |
| Label-as-feature | 7 | Actively prevented — see below. |

**`models/causal_feature_frame.py` earns its name.** The frame construction is imported into `experts` via `experts/contracts.py`, which defines an explicit unsafe-field denylist enforced at `tests/test_expert_contracts.py:61`:

```python
["outcome", "label", "answers", "future", "future_bars", "actual"]
```

The practice builder's causal split is unambiguous — `build_kline_practice_set.py:213-214`:

```python
before = active.loc[active["date"] <= observation]
after  = active.loc[active["date"] > observation]
```

`visible = before.tail(SEQUENCE_LENGTH)`, `future = after.head(HORIZON_SESSIONS)` — a strict, correct temporal partition. I verified the outcomes are honest: `future_max_return` for each card equals the real maximum forward high over the observation close, and `label` is `1` iff that return ≥ 0.30.

**The one genuine methodology defect** is not look-ahead but **case-control selection**: the 100-card set is built by choosing exactly 50 positives and 50 negatives (`build_kline_practice_set.py:660-661`), and the expert suite is then evaluated on it. This destroys the base rate, so the accuracies (0.38–0.60) cannot be read as performance on a realistic population — a strategy predicting "no" for everything scores 0.50.

**Missing-runtime defect.** `PROJECT_README.md:246` documents a test command (`pytest … tests/test_transformer.py tests/test_transformer_training.py`) for files that **do not exist** in this export, and `config/config.yaml` is absent, so the documented LightGBM/Transformer workflow is **not runnable as shipped**.

### 3.5 Test and hash claims verified

**Test counts (independently recomputed):**

| File | `def test_` |
|---|---:|
| `tests/test_expert_contracts.py` | 6 |
| `tests/test_expert_evaluation.py` | 3 |
| `tests/test_expert_registry.py` | 5 |
| `tests/test_kline_practice_web_assets.py` | 12 |
| `tests/test_serve_kline_practice.py` | 14 |
| `tests/strategies/test_external_strategies.py` | 1 |
| `tests/strategies/test_strict_selectors.py` | 2 |
| **Total `def test_`** | **43** |

`pytest --collect-only tests` → **96 tests collected in 7.00s** (parametrisation expands the 43 functions). **No doc in this export states a test count**, so there is no claim to contradict.

**Hash claims — this project's hashes VERIFY.** I recomputed every declared digest:

| Check | Result |
|---|---|
| `evaluation_manifest.json` → `artifact_sha256` (39 entries incl. all 36 sealed predictions) | **39/39 MATCH**, 0 missing |
| `evaluation_manifest.json` → `prediction_hashes` (36) | **36/36 MATCH** |
| Session `manifest.json` → `cards.json` | **MATCH** (`945b4c9ab8500978…`) |
| Session `manifest.json` → `outcomes.json` | **MATCH** (`d54f2d7d2aebbc9e…`) |
| Session `manifest.json` → `answers.json` | **MISMATCH** — declared `ca3d163bab055381…`, actual `5402e29b0eb566bb…` |

The `answers.json` mismatch is **benign and by design**: the declared digest is `sha256(b"{}\n")` — the empty-answer state at publish time. Answers necessarily mutate as the user plays. `cards.json` and `outcomes.json` — the artifacts that matter — both verify.

**Supply-chain verdict for this export: PARTIALLY VERIFIED.** The internal hash chain is **genuine, complete, and locally reproducible** for the science artifacts — the strongest of the three projects on this axis. It is **NOT_VERIFIED** as an external-provenance claim, because:
- `bank_manifest_sha256 = 362f418fefa86f214e1c60e45de9b8658b72a856cc91475629b0da3315a6a15d` references a bank **not present** in the export.
- `source_contract.source_hash = 006032dd8352b95f7b2a8d5d6b01649b8776fde8b8eac2c7107ffb9071bc23b4` and the three `artifact_hashes` (`bars_qfq.parquet`, `bars_raw.parquet`, `stock_basic.parquet`) reference a raw data bundle **not present**. The claim `"synthetic": false` therefore **cannot be independently confirmed from this export alone** — it can only be trusted as a recorded declaration.

### 3.6 Verdict — Luna Max export

**NO — no validated strategy; it is an exploratory in-sample quiz.**

- **Strongest evidence FOR:** the data provenance and hashing are real and honest. `build_kline_practice_set.py:637-638` hard-rejects synthetic sources; outcomes are genuinely recomputed from the original qfq shards (`:337-342`); the visible/future split is strict at `:213-214`; and I recomputed **39/39 artifact hashes and 36/36 prediction hashes as MATCH**. The web UI (`web/kline_practice/app.js`, `experts.js`) loads real session data from the server, not placeholders.
- **Strongest evidence AGAINST:** the entire evaluation is in-sample by construction. All 100 cards fall in the **2020-2023 training partition** (`cards.json` observations 2020-04-27 → 2023-11-24; `PROJECT_README.md:21-23` reads only `train_labels_2020_2023.parquet`), the card set is a **hard 50/50 case-control selection** enforced at `build_kline_practice_set.py:660-661`, and the expert thresholds are per-strategy source constants — with `_strict_selector.py:17` showing the 16 `strict_*` variants are the same signal re-thresholded. The project concedes the classification itself at `README_WEB_PRO.md:39`: "The 100 cards are a fixed exploratory quiz, not an out-of-sample test."

---

## Final cross-project comparison table

| Project | Distinct strategies | Best real out-of-sample result | Verified? |
|---|---|---|---|
| **`ly`** (Luna Max, incl. `positive-recall-specialist` worktree) | ~4 ML tasks + 1 ExtraTrees event benchmark + 4 screener boards + 20 rule scorers (38 strategy files overstate this: 16 are threshold wrappers) | **Precision 0.5239616613418531** (164/313, T-1, 2026 frozen forward check) and **0.4152542372881356** (49/118, T+1). Official 2025 test accuracy **0.7134741814003958** vs majority baseline **0.7150698921299546**. **All below their gates.** | **Hash chain verified locally (23/24 source, 11/12 test, 13/13 run artifacts fresh) — but it certifies an unrun pipeline: `checks.training = not_started`, `status = FROZEN_FOR_AUDIT_ONLY`, `matched_count = 0`.** Test count claim "21/21" **does not exist**; real counts: 434 `def test_` / **496 collected** (root `tests/`), **2,289 collected** (worktree). |
| **`a_share_intraday_lab`** | **5** rule families (`pullback_breakout`, `opening_range_breakout`, `vwap_reclaim`, `late_strength`, `near_limit_reseal`) + execution model. No ML. | **excellent_rate 40.00% on 5 trades / 2 days** (`top100_two_week_20260817_20260828_direct`), failing `excellent_rate 0.4 <= 0.4` and `excellent_wilson_lcb 0.11762077423264783 < 0.3`. All 5 runs = `NOT_PROVEN_GT_40`. | **MANIFEST.sha256 FAILS: 26/32 match, 6 MISMATCH** — including `src/intraday_lab/strategies.py` and `tests/test_no_lookahead.py`. No verifier script exists. **NOT_VERIFIED.** Claimed "8 passed" tests is stale; real = **15 collected**. Test window `2026-08-26/27` **reused across 4 parameter sets**, violating `METHODOLOGY.md:95`. |
| **`Luna_Max_Kline_Practice_Web_Pro_20260818`** | **20** base rule strategies + **16 `strict_*` re-threshold wrappers** (not distinct) + 4 ML tasks + screener. | **None.** All 36 expert accuracies (0.38–0.60) are **IN_SAMPLE_FIT** on a fixed 100-card set drawn entirely from the 2020-2023 **training** partition. Best is `atr_trend_follow` at **0.6**; `bollinger_squeeze` is **0.38** and **6** strategies predict "no" for all 100 cards. | **Hash chain VERIFIED locally: 39/39 artifact + 36/36 prediction hashes MATCH.** But it proves only internal consistency — it does **not** cover strategy thresholds, so the "sealed predictions" cannot certify pre-registration. Source/bank hashes **NOT_VERIFIED** (referenced bundles absent). Tests: 43 `def test_` → **96 collected**; no doc states a count. |

### Cross-cutting conclusions

1. **Pattern matches the sibling project.** All three contain exploratory/in-sample results. None contains a strategy that survived a genuine later-period untouched evaluation.
2. **The two "Luna Max" copies are the same codebase.** `ly` and the `exports/` package share `experts/strategies/` almost file-for-file (38 files each; the only size deltas are `strict_turnover_weak_to_strong_v2.py` 1409→1389 and `strict_relative_strength_v2.py` 1380→1360 bytes). They are not independent evidence.
3. **`ly` is the only project with a true frozen-holdout discipline — and it is also the one that most clearly documents its own failure.** Its honesty is a feature: `PLANNING.md:34`, `README.md:50`, and `hunter_v3_freeze_audit_20260825.md:13` all refuse to claim validity.
4. **`a_share_intraday_lab` has the best-specified protocol and the worst integrity outcome** — its own manifest fails to verify for the strategy file and the no-look-ahead test, and it reuses one test window across four parameter sets in violation of its own written rule.
5. **Doc-vs-code disagreements found (code trusted):**
   - `ly`: docs cite per-file test counts of 21 that collect as 22 and 25 today — stale snapshots, conceded by the project's own newest report.
   - `a_share_intraday_lab`: `PACKAGE_TEST_RESULTS.txt:3` "Unit tests: 8 passed" vs **15 collected** now; `MANIFEST.sha256` declares hashes for `strategies.py` and `test_no_lookahead.py` that **do not match** the shipped files.
   - Luna export: `PROJECT_README.md:246` documents `tests/test_transformer.py` and `tests/test_transformer_training.py`, **neither of which exists**; `config/config.yaml` is absent so the documented workflow is not runnable.
6. **No project's supply-chain claim is fully verifiable end-to-end**, and in two of three the failure is concrete rather than merely unpinned:
   - `ly` — verifiable and fresh, but for artifacts of a pipeline that never ran.
   - `a_share_intraday_lab` — **provably stale for the strategy code itself** (6 hash mismatches).
   - Luna export — internally complete and self-consistent, but its external trust root (bank + raw bundle) is absent, and it does not hash the strategy source it claims to have sealed.
