# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 16:21:24 JST）补遗：AUX-TCN 训练路径完全没有特征门，标签可作特征接入

- 完整报告：[`2026-09-23_16-21-24_JST.md`](./2026-09-23_16-21-24_JST.md)。本轮为对同批子 agent 结论的**亲自复核**；上一轮报告 `2026-09-23_16-10-10_JST.md` 发布时子 agent 尚未返回。
- 被审产品源码：`664b78d58e3e34a0e3937e944b54d63ad33e0e36` 的 `src` 树（`13b15b60dc40b54af29d2931b3c9831021ab7a40`，与上一轮相同，range 为 docs-only）。
- **新 P1** `EML-P1-AUX-TCN-HAS-NO-FEATURE-GATE-001`：`aux_tcn.py:94` 是不受限的直接列选择；该文件 `FeatureSpec`/`feature_spec`/`_forbidden`/`_FORBIDDEN` 出现次数**均为 0**（实测）。H504 路径至少还有一道（不完整的）语义门，**AUX-TCN 一道都没有**。
- **新 P1** `EML-P1-AUX-LABEL-ADMITTED-AS-FEATURE-AT-UNGATED-PATH-001`：`aux_tcn.py:87/89` 把 `_targets()` 并入模型帧，`:101` 用 `aux_ret1` 作分类标签，而 `:94` 可把**同一列**选为特征；`_forbidden('aux_ret1')=False`（`aux_` 不在任何前缀表）。实测：选中的那列**逐元素等于**标签；真 `run_aux_tcn(feature_cols=["ret5","aux_ret1"])` 返回 **`COMPLETE_AUX`**。对照 `label_joint` 被 `FeatureSpecError` 拦下——同类问题 H504 侧拦、AUX 侧不拦。
- **定级纠正（我否证了子 agent 的一处说法）**：子 agent 称 `aux_ret1` 在默认 `--stage aux-tcn` 下可达；我实测 `feature_cols` 61 列中 **不含** `aux_ret1`（`build_research_features()` 不产出它，全仓库产品源码里它只在 `aux_tcn.py`）。故定级为 **latent / 调用方署名可达**，**不是默认泄漏**；泄漏的指标幅度**未计数**，不主张它抬高过任何成绩。
- **回归复现 P1** `EML-P1-PIPELINE-HASH-BLIND-TO-BUILD-MATRIX-SOURCE-001`：`run.py:94` 只非递归 glob `research_h504/*.py`（16 个），而 `snapshot_features.py:78` 导入的 `src/ml/build_matrix.py`（26,259 B）不在其中。三臂实测：变异 glob 内文件 → 签名**变**（正向对照有效）；变异 glob 外 `build_matrix.py` → 签名**完全不变**。
- 真实测试真数不变：`python -m pytest` = **65 passed in 30.18s**，exit 0（对以上全部缺陷类盲）。
- 四状态：GitHub 报告=`YES`；本机 runtime applied=`NO_LAST_VERIFIED / NOT_RECHECKED_THIS_TURN`；本机单次 3h completed=`NOT_VERIFIED`；新实股成绩=`real_market_fit_count += 0`。

## 当前最小落地顺序

1. 先修发布器（唯一能让本仓库对外状态恢复可见的项）：rebase 前 `--include-untracked` 收走残留，或改为直接推送单个 status 提交、不 rebase 本地分支。
2. 把安全门做成**同一条 allowlist**，同时接在 `train_h504.py:45` **和** `aux_tcn.py:94`；来源用 `run.py:112` 已产出的 `feature_schema.json`。
3. 追加硬断言：所选特征列与目标列（`aux_ret1`/`aux_rv5`）交集必须为空；`pipeline_hash` 改为递归覆盖默认路径真正消费的源码。
4. 真实 H504 验收仍须来自用户本机：真实 task/runtime、真实 panel/calendar、重生成的 outcome ledger、合法 candidate-aware fold、真实 registry/checkpoint 与 `execution_receipt`。

## 仍开放但本轮不重复计新的关键项

- `EML-P1-H504-RISK-KNOWN-BUT-CLOSE-MISSING-MISCLASSIFIED-UNKNOWN-001`
- `EML-P1-H504-SINGLE-INSTANCE-LOCK-NOT-SHARED-WITH-DIRECT-RUNNER`
- `EML-P1-H504-PRICE-BASIS-CONTRACT-ADVISORY-ONLY`
- `EML-P1-H504-RECEIPT-PROVENANCE-CALLER-CONTROLLED`
- `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`
- `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`
- `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`
- `EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE`
- `EML-P1-H504-ORACLE-ALLOWLIST-BYPASS-CLASS-NOT-INSTANCE-001`
- `EML-P1-FEATURE-SCHEMA-WRITTEN-BUT-NEVER-READ-001`
- `EML-P0-REPORT-AUDIT-PUBLISHER-REBASE-BLOCKED-BY-UNTRACKED-LEFTOVER-001`
- REAL calendar/evidence fail-open、AUX 主线抢跑、target_active_seconds 未形成成功退出硬门、direct stage 绕过完整 session receipt。
- `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`、`EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`、股票代码 key-space/alias 风险。

## 前一版索引（不可变保留）

[截至上一版（最新审计（2026-09-23 16:10:10 JST）：报告发布器连续 8 次无法发布（untracked 残留锁死 rebase）＋ FeatureSpec oracle 绕过是类级缺陷）的 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/4d407134f53f7c243e3d3513613fb3cfc574bcf0/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际 panel/calendar/basis/候选指纹、重新生成的 H504 outcome ledger、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。
