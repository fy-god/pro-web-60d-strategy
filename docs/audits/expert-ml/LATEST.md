# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 06:13:30 JST）：10800 秒目标目前只记账、不拦截成功退出

- 完整报告：[`2026-09-23_06-13-30_JST.md`](./2026-09-23_06-13-30_JST.md)。
- 被审实时 `main`：`d651300765eae63bf8dce42febb4df0af7f55e97`；tree：`1ba55f04b56d406dbe4840d9be775280817f2957`；Open PR=0。
- 新增 P1 `EML-P1-H504-TARGET-ACTIVE-NOT-ENFORCED-AT-EXIT`：`ResearchSessionReceipt.finalize()` 会写 `target_met`，但 `run.py --stage all` 不用它决定退出；当前流程在 `target_met=false` 时仍可 `return 0`。
- **决定性现成测试证据**：`test_all_stage_writes_start_and_execution_receipts` 同时断言 `main(...) == 0` 和 `end['target_met'] is False`，即测试套件主动把“10800秒未达但成功退出”锁成正确行为。
- 外层 `scripts/run_fixup.py` 又只按 child `rc==0` 返回成功；虽然打印 `training_status='READ_RESEARCH_EXECUTION_RECEIPT'`，实际并没有读取／验证 final `execution_receipt.json`。因此即使以后把 Windows 任务上限修到 ≥13800 秒，当前链条仍可能明显早于三小时正常退出。
- 新增从属 P2 `EML-P2-H504-DIRECT-STAGE-NO-SESSION-RECEIPT`：receipt 只在 `--stage all` 创建；`h504-hgb` / `aux-tcn` 直接训练入口可完全绕过 start/progress/execution receipt 与三小时 target 验收。
- 隔离候选：single-session exit classifier + launcher receipt handoff，**7 passed in 0.06s**；候选只算软件证据，不计 fit，不等于产品已修。
- 最新本机侧证据仍是 03:33:44 JST 的真实 Windows 查询：213 个任务中**没有 `ProWeb60d-Fixup`**，因此当前不是“任务只有150分钟”，而是该 fixup 任务根本未注册；状态继续为 `BLOCKED_RUNTIME_CONFIG`。
- 四状态：GitHub prompt=`YES`；GitHub任务书=`YES`；本机runtime applied=`NO / BLOCKED_RUNTIME_CONFIG`；本机单次3h completed=`NOT_VERIFIED`。
- 本轮 `real_market_fit_count += 0`；无新的 H504/AUX 实股成绩，旧48-fit余额无本机台账回传，因此不猜数字。

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

[截至 2026-09-23 03:33:44 JST 的完整 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/d651300765eae63bf8dce42febb4df0af7f55e97/docs/audits/expert-ml/LATEST.md)。

上一版索引中的全部历史报告、补遗、争议、更正与旧状态均按该固定 SHA 原样保留；本轮没有删除任何历史审计 Markdown。旧“当前状态”按其固定源码 SHA 和审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际数据/日历/候选指纹、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。
