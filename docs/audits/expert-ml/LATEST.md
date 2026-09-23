# 专家／ML线研究与审计索引

## 最新审计（实测 2026-09-23 19:20–19:50 JST；轮次标签 20-10-00）：引用 guard 不存在；现有测试对本缺陷零判别力

- 完整报告：[`2026-09-23_20-10-00_JST.md`](./2026-09-23_20-10-00_JST.md)。
- 被审 `main` 起点：`aacf63178c6b116a9d8335e53a65ef2e4a1cbd66`；审计开始时远端尖端 `aacf6317…`，`aacf6317..f818e23f` 恰 2 个提交且均为 docs-only；产品 `src` tree `13b15b60dc40`、`scripts` tree `eac5e3911906` 在审计区间内逐位未变，故本轮做的是独立复核与证伪，不是新提交审查。
- **新 P1** `EML-P1-CITED-GUARD-DOES-NOT-EXIST-001`：上一份报告引用的「隔离 guard 实测 4 passed in 0.07s」在仓库中**不存在**。尖端 `f818e23f` 的 2243 个 tracked 文件里只有 3 个含 `def test_`（40/15/10 个测试函数），**恰含 4 个测试函数的文件 = 0 个**；被审计基线 `aacf6317` 与用户现场工作树同样只有这 3 个。逐目标实跑无一产出「4 passed」。该 guard 是上一份报告唯一标注「实测」的行为证据。
- **新 P1** `EML-P1-TEST-SUITE-ZERO-DETECTION-POWER-002`：把上一份报告**自己提出的修复**（去掉 `data_io.py` 的 reindex filler）实际打进代码后，`pytest -q tests` 仍为 **65 passed in 24.38s, exit 0**（未改时 65 passed in 26.30s）；子 agent 变异臂独立同向：M1 打入修复 65 passed、M3 改 KDJ 语义 65 passed，而 M2 正对照（删 `run.py:88-89` calendar 守卫）**1 failed, 64 passed, exit 1**——证明套件是接上的，只是**恰好盲于本缺陷及其修复**。
- **零判别力根因**（我亲自读到）：`tests/research_h504/test_github_delivery.py:22-27` 用 `assert pd.isna(aligned.loc[aligned.date.eq(day),'open']).all()` **把「插入全 NaN 行」这一缺陷行为钉成期望**；修复后该选择集为空，而 `pd.isna(空序列).all()` 恒为 True（实测 `True`，`len=0`），断言在两种代码上都通过。
- **上一份报告核心缺陷成立**（我已端到端复现）：`data_io.py:36-41` 物化全 NaN filler；`src/features.py:57-59` 在 filler 行的 `span` **有限**（`rolling(min_periods=1)` 跳过 NaN）但 `close` 为 NaN ⇒ `rsv=NaN`；`:66-71` 的手写递归 `k=(1-1/3)k+(1/3)rsv` 让 NaN **吸收**。实测玩具例 `kdj_k=[50.0,59.259,68.078,NaN,NaN,…]`。
- **契约缺口（正+负对照）**：`src/features.py:44-46` 承诺平坦窗口给 50。POSITIVE（`span<=EPS`）→ `rsv=50.0` 遵守；NEGATIVE（span 有限、close 为 NaN）→ `rsv=NaN` **违反**。即该保证只覆盖零分母分支，未覆盖缺失 close 分支。
- **T0 影响由我用仓库自身函数测得**：`run.py:47` 的 `_baseline_feature_cols` 只排除 `vir*`/`vp_*`/`kdj_low_*`；116 个 feature 列中 9 个 kdj 列里 **6 个进入 T0**（`kdj_k/kdj_d/kdj_j/kdj_k_chg5/kdj_j_chg5/kdj_k_minus_d`），一个 filler 后 **6/6 全部 all-NaN**；无缺口对照全为 False。默认路径实测选中 `repository_build_matrix_raw_features`。
- **新 P2** `EML-P1-MARKET-SESSION-ID-FLATTENS-ACROSS-HALT-003`：filler 行同时压平 `market_session_id`（实测 filled 0..199/停牌日有行 id=100，observed 0..198/无该行；停牌后第一根真实 bar 的 id 为 **filled=101 vs observed=100**），因为 `add_market_session_id` 从**帧内实际存在的日期**重新编号，任何缺口在 id 序列上不可见。
- **本轮我证伪并降级的项**：① 上一份报告的「4 passed in 0.07s」→ `未复现`（不存在）；② 子 agent A 关于 P2 的 magnitude 说法（observed-only 下 `vir_coverage20=0.0`）→ `未复现`：我在 N=60/200/400 三组夹具实测 observed-only **同样为 1.0**，真实原因是重新编号使缺口根本不进入 id 序列。保留的是直接测得的 **id 压平** 事实。
- **13 项未修项回归 = 13/13 仍开放**（子 agent B 逐条定位，12 项有可运行反例，1 项为静态普查）。其中第 13 项有**生产日志证据**：`logs/report_audit/scheduler.out` 记录 2026-09-22 07:15 → 2026-09-23 15:15 **连续 9 次发布失败**。
- 运行时常量我逐条核对：`scripts/run_fixup.py:23 AGENT_TIMEOUT_SECONDS = 13200`，而 `scripts/run_fixup.task.xml:16 <ExecutionTimeLimit>PT2H30M`（=9000s），**缺口 4200 秒**；该 XML 为 UTF-16LE，普通 grep 会漏读。
- 本轮真实 A 股 H504/AUX fit 增量：`0`；**没有新的 H504 成功率**。`evidence_type` = 软件样本 + 真实源码 + 仓库自带 pytest；`real stock = 0`。
- **未测量（不猜数）**：第 4、6 项的 magnitude 需要真实 A 股 panel / calendar / basis manifest，clone 内不存在 ⇒ 「低点存在但 close 缺失」的会话频率、真实 panel 是否混用价格基准，**均未计数**。

## 前一版索引（不可变保留 · 截至 2026-09-23 18:00:16 JST）

## 最新审计（2026-09-23 18:00:16 JST）：独立日历 filler 会永久毒化递归 KDJ 状态

- 完整报告：[`2026-09-23_18-00-16_JST.md`](./2026-09-23_18-00-16_JST.md)。
- 被审 `main` 起点：`aacf63178c6b116a9d8335e53a65ef2e4a1cbd66`；根 tree `f3d10ba80e5a7fa4198ac3ea40227a41d05bf052`；产品 `src` tree `13b15b60dc40b54af29d2931b3c9831021ab7a40`；Open PR=0。自 `8163db84...` 以来最新范围仍为 docs-only，产品研究源码本轮没有变化。
- **新 P1** `EML-P1-H504-CALENDAR-FILLER-ROW-POISONS-RECURSIVE-KDJ-STATE-001`：`data_io.prepare_panel(..., calendar)` 会把每只股票缺失的市场 session 物化成全 NaN OHLCV filler；`run.py` 随后把这张重索引 panel 直接送入 `build_research_features()`；默认 richer snapshot 路径调用 `src.ml.build_matrix.add_price_features()` → `src.features.kdj()`。一条 filler 可让 `RSV -> NaN -> K/D/J`，而手写递归没有 finite guard，导致该股票后续真实 bar 的 K/D/J **永久 NaN**。
- **影响默认 T0，不只是研究增量**：baseline 只排除 `vir*`、`vp_*`、`kdj_low_*`，普通 `kdj_k/kdj_d/kdj_j/kdj_*chg5` 仍可进入 T0。HGB 会把这些永久 NaN 中位数/0 插补；而 `add_kdj_path_features()` 中 `NaN < 20` 为 False，又会把后续低位路径向“非低位”方向编码。
- 该问题与旧 `missing-bar provenance` 共用结构根因：把 calendar filler 永久塞回股票 bar panel。正式修复应拆成 `observed_bar_panel` + 独立 `market_calendar`；feature builder 只消费真实 observed bars，label oracle 内部临时对齐；`market_session_id` 从独立 calendar 映射到 observed rows，从而保留停牌后的 session jump，VIR 等 gap-sensitive 因子仍能拒绝桥接。
- 隔离 guard 实测：**4 passed in 0.07s**。覆盖“当前 reindex 生成 NaN filler”“当前递归 KDJ 一次 filler 后永久 NaN”“observed-only KDJ 重开后保持有限”“external market_session_id 保留 2-step gap”。这是软件证据，不计48-fit，也不是市场成绩。
- 三小时状态：tracked runner `13200s` 已在源码；tracked `run_fixup.task.xml` 仍为 `PT2H30M`；用户 Windows 实际已注册 task 本轮未重查。因此 `LOCAL_RUNTIME_APPLIED=NOT_VERIFIED / LOCAL_APPLY_PENDING`，`LOCAL_SINGLE_CONTINUOUS_3H_COMPLETED=NOT_VERIFIED`。
- 本轮真实 A 股 H504/AUX fit 增量：`0`；没有新的 H504 成功率。

## 当前最小落地顺序

1. 先拆 `observed_bar_panel` 与独立 calendar grid，修本轮 KDJ poison，并同时消除 missing-bar provenance 的结构根因；feature 只在真实 bars 上推进，`market_session_id` 由独立 calendar 映射。
2. 把同一条 feature allowlist 接到 H504 与 AUX；所选特征与 `aux_ret1/aux_rv5/label_joint` 等目标字段硬互斥，并真正消费 `feature_schema.json`。
3. `pipeline_hash` 递归覆盖默认路径真实依赖，包括 `src/ml/build_matrix.py`、`src/features.py` 等，而不是只 hash `research_h504/*.py`。
4. 继续修 `risk-known/close-missing` oracle、resolved-dev 支持、artifact COMPLETE hash 校验、48-fit 全局预算、measured provenance、shared lock、price-basis/calendar gate 与 stock-code key normalization。
5. 把 `target_active_seconds=10800` 做成真正成功退出硬门；本机实际 registered task/runtime 先核验并窄改到 `>=PT3H50M`，再由新配置启动一次连续 session。
6. 重生成 candidate/outcome/fold；有合法 H504 fold 才继续 T0/T3 主线，无合法折则明确 `BLOCKED_PROTOCOL_H504` 后进入 `AUX_REAL_HISTORY` fallback，不能拿 AUX 数字替代 H504。

## 仍开放但本轮不重复计新的关键项

- `EML-P0-REPORT-AUDIT-PUBLISHER-REBASE-BLOCKED-BY-UNTRACKED-LEFTOVER-001`
- `EML-P1-AUX-TCN-HAS-NO-FEATURE-GATE-001`
- `EML-P1-AUX-LABEL-ADMITTED-AS-FEATURE-AT-UNGATED-PATH-001`
- `EML-P1-PIPELINE-HASH-BLIND-TO-BUILD-MATRIX-SOURCE-001`
- `EML-P1-H504-ORACLE-ALLOWLIST-BYPASS-CLASS-NOT-INSTANCE-001`
- `EML-P1-FEATURE-SCHEMA-WRITTEN-BUT-NEVER-READ-001`
- `EML-P1-H504-RISK-KNOWN-BUT-CLOSE-MISSING-MISCLASSIFIED-UNKNOWN-001`
- `EML-P1-H504-SINGLE-INSTANCE-LOCK-NOT-SHARED-WITH-DIRECT-RUNNER`
- `EML-P1-H504-PRICE-BASIS-CONTRACT-ADVISORY-ONLY`
- `EML-P1-H504-RECEIPT-PROVENANCE-CALLER-CONTROLLED`
- `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`
- `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`
- `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`
- REAL calendar/evidence fail-open、AUX 主线抢跑、`target_active_seconds` 未形成成功退出硬门、direct stage 绕过完整 session receipt、AUX partial-epoch resume weighting、全 NaN feature 静默插补与股票代码 key-space/alias 风险。

## 前一版索引（不可变保留）

[截至 2026-09-23 16:21:24 JST 的上一版 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/aacf63178c6b116a9d8335e53a65ef2e4a1cbd66/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际 panel/calendar/basis/候选指纹、重新生成的 H504 outcome ledger、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。
