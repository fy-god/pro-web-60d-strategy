# 专家／ML线研究与审计索引

## 补遗（2026-09-23 07:51:17 JST）：三条独立证据链钉死上一份的 P1；新登记"守卫零检测力 8/11"与"悬空 ID 实为 2 条"；并公开我本轮自己造成的一起证据损毁事故

- 完整补遗：[`2026-09-23_07-51-17_JST.md`](./2026-09-23_07-51-17_JST.md)；被补遗的主报告：[`2026-09-23_06-30-00_JST.md`](./2026-09-23_06-30-00_JST.md)。
- 被审实时 `main`：`5c2e4b7084c75071596873f5daa66c6e800af1b7`；`src/`+`scripts/` 在 `a8ae13cc..5c2e4b70` 的 **29** 个提交中改动 = **0** ⇒ 13 项开放项**按构造不可能被修**。
- 上一份 P1（`EML-P1-AUDIT-STATUS-PUBLISHER-REBASE-ABORTS-ON-UNTRACKED-LEFTOVER`）**获得第二、第三条独立证据链**，且其**决定性前置条件由我逐字节验证**：两个未跟踪文件与远端 blob **完全相同**（`e381839c…` 33,636 B / `11fee1ec…` 17,334 B，CRLF=0），本地 `?? ` 未跟踪、远端已跟踪。
- **精度更正（采纳子 agent C 的测量）**：6 次发布尝试全部失败、6 个提交滞留，但其中**5 次承载新信息**（`Remote drift` 3→6→8→9→15→19），墙钟滞后 **24 h**；首个滞留提交 `4b1f3f6` 只改时间戳、漂移值仍为 3。**我复核**：远端 blob `7902a4f9…` 2,442 B ↔ 本地 `817b4396…` 3,293 B，numstat **+23/−7**，`Scheduled report audit` 提交数 **35/35/29**。
- **扩展既有 ID** `EML-P1-H504-GUARDS-HAVE-ZERO-TEST-DETECTION-POWER-001` 为 **8/11 零检测力**；我**亲自复现最有判别力的不对称对照对**：删地平线守卫 `run.py:90-91` → **65 passed rc=0**；删紧邻的日历守卫 `run.py:88-89` → **1 failed rc=1**；恢复后 blob 回到 `c27711f6…`。机制：唯一端到端测试用 `--evidence-type SYNTHETIC`（`test_candidate.py:321/:328`），把两条守卫一起跳过；日历守卫另有一条直接单测，地平线守卫没有。
- **新登记** `EML-P2-DANGLING-ID-CENSUS-UNDERCOUNTS-AND-CONTROL-GROUP-CONTAINS-THE-DEFECT-001`：悬空 ID **实为 2 条**（`…STOCK-CODE-KEY-NORMALIZATION-MISMATCH` 全树 3 次/**0** 正文；`…FOLD-SUPPORT-USES-CACHED-TIMEOUTS-BEFORE-DEV-START` 2 次/**0**），而旧报告把前者放进"**有真实正文**"的对照组 ⇒ 其对照组本身包含它正在描述的缺陷。
- **新登记** `EML-P1-AUDIT-CLEANUP-DELETES-LIVE-SUBAGENT-WORKSPACES-001`：**我自己的清理脚本**把仍在服务的子 agent 目录列入删除清单，**删除了两个已完成子 agent 的报告（不可恢复）**、并在审计中途损毁了第三个的 clone——子 agent 把它记录为"外部进程"，**那是我**。
- 已发表文本另两处更正：`LATEST.md:34/:37` 两条散文项**不带 ID 记号**（distinct token 实数 11 ⇒ 以 11 当清单会少算）；旧报告 `2026-09-22_07-41-01_JST.md:32/:206` 的 `0.695434` 单分数症状**在所述量级未复现**，本补遗**不采用**该数字。
- 四状态：GitHub 报告=`YES`；本机 runtime applied=`NO / BLOCKED_RUNTIME_CONFIG`（沿用 03:33:44 JST 的真实查询，本轮未复验）；本机单次 3h completed=`NOT_VERIFIED`；新实股成绩=`real_market_fit_count += 0`。

## 当前最小落地顺序

1. 一次性恢复／注册现有 `ProWeb60d-Fixup`，只调整本任务 runtime/prompt，保留 trigger/action/principal；前后导出核验；`ExecutionTimeLimit >= PT3H50M`。
2. 把本轮 target enforcement 接入 runner + launcher：`target_met=false + READY` 必须 `EARLY_STOP_WITH_READY_WORK`，不能 rc=0 冒充完成。
3. REAL_MARKET/AUX_REAL_HISTORY 下禁止无 receipt 的 direct training stage，或给 direct stage 接同一 receipt／shared lock／48-fit ledger。
4. 落地既有高优先级门：shared lock、measured provenance、artifact COMPLETE hash 校验、resolved-dev 支持、跨 session 48-fit 原子台账、feature-source signature、price-basis gate。
5. 所有门禁补“删除守卫必须测试变红”的变异测试；当前 65 项全绿不能继续作为这些门的充分证据。
6. 然后进入真实 `candidate_manifest -> H504 outcome -> candidate-aware fold_support`；合法则主线 T0/T3/T1–T5，无合法折则 `BLOCKED_PROTOCOL_H504` 后同 session 跑 `AUX_REAL_HISTORY`，绝不混报。

## 当前仍开放但本轮不重复计新的关键项

- `EML-P1-H504-SINGLE-INSTANCE-LOCK-NOT-SHARED-WITH-DIRECT-RUNNER`
- `EML-P1-H504-PRICE-BASIS-CONTRACT-ADVISORY-ONLY`
- `EML-P1-H504-RECEIPT-PROVENANCE-CALLER-CONTROLLED`
- `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`
- `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`
- `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`
- `EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE`
- REAL calendar/evidence fail-open、horizon fail-open、AUX 主线抢跑／主线未跑也跑 AUX
- `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`
- `EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`
- 股票代码 alias/key-space split 等已发表输入表示风险。

## 前一版完整索引（不可变保留）

[截至 2026-09-23 06:30:00 JST 的完整 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/5c2e4b7084c75071596873f5daa66c6e800af1b7/docs/audits/expert-ml/LATEST.md)。

上一版索引中的全部历史报告、补遗、争议、更正与旧状态均按该固定 SHA 原样保留；本轮没有删除任何历史审计 Markdown。旧“当前状态”按其固定源码 SHA 和审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际数据/日历/候选指纹、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。
