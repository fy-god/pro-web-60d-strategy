# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 14:06:58 JST）：`FeatureSpec` 仍可显式接入未来 oracle 字段 `bars_scanned`

- 完整报告：[`2026-09-23_14-06-58_JST.md`](./2026-09-23_14-06-58_JST.md)。
- 被审实时 `main`：`d363617da5ca7c74d849647b12b49e62bc40c20b`；tree=`6577b8d5168863fd9c9ccdc418c979e80635ae5c`；Open PR=0。
- **新 P1** `EML-P1-H504-ORACLE-METADATA-BARS-SCANNED-ALLOWLIST-BYPASS-001`：`label_h504_candidates()` 生成数值型未来路径字段 `bars_scanned`，而 `FeatureSpec` 的 forbidden set 没有它；`run_h504_hgb()` 又是在完整 label ledger 与 feature frame 合并后才执行 `FeatureSpec.select(data)`，所以显式 `feature_cols=["bars_scanned"]` 当前可通过 guard。
- 边界：当前默认 T0 的列来自 `build_research_features()`，本轮**没有证据证明默认 T0 已自动使用该字段**；确认的是训练 API / FeatureSpec 的 PIT 安全门 fail-open，必须在 T1–T5、H504 MLP/TCN 扩展前修复。
- 现有 `test_feature_spec_rejects_new_h504_oracle_metadata` 只检查 `training_eligible / target_price / risk_floor / candidate_id / signal_date`，没有检查 `bars_scanned / first_missing_session`。
- 隔离候选：补 `bars_scanned`、`first_missing_session` guard，并保留 causal `ret5`；**4 passed in 0.07s**。候选 ZIP SHA256=`06342d0e9f4343e046b1aa1e59cd5a1570d451723c77c175e9c732e8ceae74bf`。
- 四状态：GitHub 报告=`YES`；本机 runtime applied=`NO_LAST_VERIFIED / NOT_RECHECKED_THIS_TURN`；本机单次 3h completed=`NOT_VERIFIED`；新实股成绩=`real_market_fit_count += 0`。

## 当前最小落地顺序

1. 先修已确认的 risk/Close 缺失 oracle 与本轮 `bars_scanned` oracle-feature 缺口；把 H504 oracle 输出字段维护成 canonical schema。
2. `run_h504_hgb()` 训练前强制 `feature_cols ⊆ feature_frame_schema`，只把正式 feature pipeline 产出的列送入模型；不要只依赖不断增长的 blacklist。
3. 补产品级 metadata injection + mutation tests：删除 `bars_scanned` guard 时必须测试变红。
4. 一次性恢复／注册 `ProWeb60d-Fixup` 并核 `ExecutionTimeLimit >= PT3H50M`；再落 target enforcement、shared lock、measured provenance、artifact hash、resolved-dev 支持、跨 session 48-fit 原子台账、feature-source signature、price-basis 与 REAL calendar/evidence gate。
5. 重新生成真实 candidate/outcome ledger 与 candidate-aware fold support；有合法 H504 mature train→dev 才继续 T0/T3/T1–T5，否则 `BLOCKED_PROTOCOL_H504` 后同 session 转 `AUX_REAL_HISTORY`，绝不混报。

## 仍开放但本轮不重复计新的关键项

- `EML-P1-H504-RISK-KNOWN-BUT-CLOSE-MISSING-MISCLASSIFIED-UNKNOWN-001`
- `EML-P1-H504-SINGLE-INSTANCE-LOCK-NOT-SHARED-WITH-DIRECT-RUNNER`
- `EML-P1-H504-PRICE-BASIS-CONTRACT-ADVISORY-ONLY`
- `EML-P1-H504-RECEIPT-PROVENANCE-CALLER-CONTROLLED`
- `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`
- `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`
- `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`
- `EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE`
- REAL calendar/evidence fail-open、AUX 主线抢跑、target_active_seconds 未形成成功退出硬门、direct stage 绕过完整 session receipt。
- `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`、`EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`、股票代码 key-space/alias 风险。

## 前一版索引（不可变保留）

[截至 2026-09-23 10:05:12 JST 的 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/d363617da5ca7c74d849647b12b49e62bc40c20b/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际 panel/calendar/basis/候选指纹、重新生成的 H504 outcome ledger、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。