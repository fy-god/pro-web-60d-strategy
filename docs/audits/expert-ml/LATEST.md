# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 10:05:12 JST）：H504 risk-first oracle 会在 `Close` 缺失时吞掉已知 `Low` 风险事件

- 完整报告：[`2026-09-23_10-05-12_JST.md`](./2026-09-23_10-05-12_JST.md)。
- 被审实时 `main`：`ca73ae8a1c5116821b56fe702ea804357c248f70`；相对上一审计点 `5c2e4b70...` 只多 2 个审计文档提交，产品 `src/`/`scripts/` 没有变化；Open PR=0。
- **新 P1** `EML-P1-H504-RISK-KNOWN-BUT-CLOSE-MISSING-MISCLASSIFIED-UNKNOWN-001`：当前 `task_spec.label_h504_candidates()` 用一个同时要求 `Low` 与 `Close` 有效的复合 `valid` 掩码，再定义 `risk = valid & (Low < 0.8E)`。因此 `Low` 已明确跌破风险线但同日 `Close=NaN` 时，当前 oracle 错误输出 `unknown_missing_price / label_joint=NaN / unresolved`，而不是 contract 要求的 `risk / 0 / resolved`。
- 隔离最小反例：`E=10, floor=8, first post-entry Low=7.5, Close=NaN`，当前逻辑稳定复现上述错误；本轮窄候选把 low/close observability 拆开，严格按 `risk -> unknown -> success` 分类，**5 passed in 0.05s**。候选 ZIP SHA256=`5cd05d6a73ca558263829497caf36e2595ba0d5f3fce11985dfca53c04418d87`。
- 影响：会把已知 risk 负例移出 resolved 集合，进而影响 resolved 支持、base rate、Brier/log-loss/AP 样本集合，并可能改变临界折的 READY/BLOCKED；本轮没有真实用户数据通道，因此**不声称真实 panel 中出现频次**。
- 当前测试覆盖“同日 risk+success 且价格完整”与“整根 post-entry bar 缺失”，但没有覆盖“Low 已知 risk、Close 单独缺失”的不对称场景；下一次产品修复必须补 mutation test，删除 risk-before-unknown 分支时测试必须变红。
- 四状态：GitHub 报告=`YES`；本机 runtime applied=`NO / BLOCKED_RUNTIME_CONFIG`（沿用上一轮真实机器核验，本轮无机器侧复验通道）；本机单次 3h completed=`NOT_VERIFIED`；新实股成绩=`real_market_fit_count += 0`。

## 当前最小落地顺序

1. 先修本轮 risk/Close 缺失 oracle，并补产品级回归 + mutation test；在 candidate→outcome→fold 之前先保证 G1 标签语义正确。
2. 一次性恢复／注册现有 `ProWeb60d-Fixup`，只调整本任务 runtime/prompt，保留 trigger/action/principal；前后导出核验；`ExecutionTimeLimit >= PT3H50M`。
3. 落地 target enforcement：`target_met=false + READY/INTERRUPTED` 必须 `EARLY_STOP_WITH_READY_WORK`，不能 rc=0 冒充完成；REAL_MARKET/AUX_REAL_HISTORY 下 direct training stage 不能绕过 receipt/shared lock/48-fit ledger。
4. 再落 shared lock、measured provenance、artifact COMPLETE hash 校验、resolved-dev 支持、跨 session 48-fit 原子台账、feature-source signature、price-basis 和 REAL calendar/evidence gate。
5. 重新生成真实 candidate/outcome ledger，专门统计 `missing_low / missing_close / missing_bar / risk-with-missing-close` 原始计数及股票/年份切片，再重算 candidate-aware fold support。
6. 有合法 mature train→dev 折才继续 H504 T0/T3/T1–T5；没有则明确 `BLOCKED_PROTOCOL_H504`，同 session 转 `AUX_REAL_HISTORY`，绝不把 AUX 当 H504 成绩。

## 仍开放但本轮不重复计新的关键项

- `EML-P1-H504-SINGLE-INSTANCE-LOCK-NOT-SHARED-WITH-DIRECT-RUNNER`
- `EML-P1-H504-PRICE-BASIS-CONTRACT-ADVISORY-ONLY`
- `EML-P1-H504-RECEIPT-PROVENANCE-CALLER-CONTROLLED`
- `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`
- `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`
- `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`
- `EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE`
- REAL calendar/evidence fail-open、horizon fail-open、AUX 主线抢跑／主线未跑也跑 AUX
- target_active_seconds 目前仍未形成成功退出硬门；direct training stage 仍可绕过 session receipt
- `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`
- `EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`
- 股票代码 alias/key-space split 等已发表输入表示风险。

## 前一版索引（不可变保留）

[截至 2026-09-23 07:51:17 JST 的 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/ca73ae8a1c5116821b56fe702ea804357c248f70/docs/audits/expert-ml/LATEST.md)。

上一版索引中的历史报告、补遗、争议、更正与旧状态均按固定 SHA 原样保留；本轮没有删除任何历史审计 Markdown。旧“当前状态”按其固定源码 SHA 和审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际 panel/calendar/basis/候选指纹、重新生成的 H504 outcome ledger、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。