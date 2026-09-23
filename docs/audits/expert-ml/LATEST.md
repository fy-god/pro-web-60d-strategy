# 专家／ML线研究与审计索引

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
