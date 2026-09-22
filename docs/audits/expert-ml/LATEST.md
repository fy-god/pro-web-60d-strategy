# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 06:30:00 JST）：每 4 小时的状态发布器已连续 6 次把提交留在本地、远端状态冻结约 24 小时

- 完整报告：[`2026-09-23_06-30-00_JST.md`](./2026-09-23_06-30-00_JST.md)。
- 被审实时 `main`：`dc725a820f6ea8bf835820c6cce8baf6325b7546`；tree：`1ba55f04b56d406dbe4840d9be775280817f2957`；Open PR=0。
- 新增 P1 `EML-P1-AUDIT-STATUS-PUBLISHER-REBASE-ABORTS-ON-UNTRACKED-LEFTOVER`：`scripts/scheduled_report_audit.py:255-256` 的 `git rebase --autostash origin/main` **无法处理未跟踪路径**；另一条自动化（本审计线）留下的未跟踪 `docs/audits/expert-ml/*.md` 使 checkout 被拒，重试在 `:257-260` **abort 并返回**，提交永远留在本地。
- **实测留档**：被 gitignore 的 `logs/report_audit/scheduler.out` 记录 16 次发布结果 = 3 次直接成功 + 4 次 rebase 后成功 + **6 次 `committed locally; rebase … failed on attempt 1`** + 3 次更早期的普通 push 失败；**末尾连续 6 次全部失败**。判别性对照（仓外沙箱，单变量）：有未跟踪文件时 `rebase` rc=1 且逐字输出 `would be overwritten by checkout`；去掉该文件后 rc=0。
- **影响**：远端发布物仍停在 `| Last run (local) | 2026-09-22 03:15:01 |`、`3 path(s) differ`，而实测真实漂移为 **20** 个路径；本地 `main` 与远端 **ahead 6 / behind 27**；最后一次成功发布 `a8ae13c`（09-22 03:15:08）正是两侧的 merge-base。失败在本地有 4 处痕迹，在 GitHub 侧 **0 处**（`:369` 只打印、启动器 `--quiet`、输出落进被 gitignore 的 `logs/`、`:376` 退出码只看一致性检查器、无 CI）。
- **重试环救不回**：`:257-260` 在 rebase 第一次非 0 时即 abort 并 return，`:248` 的 `for attempt in range(1,4)` 对该类失败**永远走不到**（`push failed after 3 rebase attempts` 计数 = 0）。
- **同一脚本自己的 docstring 断言被推翻**：`:217-221` 称 "a file no other job touches -- so the rebase cannot conflict"。冲突源不是它提交的文件，而是另一条线的未跟踪路径。
- 上一轮（06:13）新登记的 `EML-P1-H504-TARGET-ACTIVE-NOT-ENFORCED-AT-EXIT` 及其 P2 本轮**逐条实测确认，未被推翻**（`run.py:194` 无条件 `return 0`；`run_fixup.py:162` 只看 `rc==0`；`tests/research_h504/test_candidate.py:320-322` 与 `:327` 在同一测试里正向锁死）。
- 本轮 `src/` 与 `scripts/` 改动数 = **0**（`2026-09-23_06-13-30_JST.md` 之后 27 个提交全部是 docs）；因此本轮**不把任何旧项写成"已修复"**。
- 四状态：GitHub 报告=`YES`；本机 runtime applied=`NO / BLOCKED_RUNTIME_CONFIG`（沿用 03:33:44 JST 的真实 Windows 查询，本轮未复验）；本机单次 3h completed=`NOT_VERIFIED`；新实股成绩=`real_market_fit_count += 0`。

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

[截至 2026-09-23 06:13:30 JST 的完整 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/dc725a820f6ea8bf835820c6cce8baf6325b7546/docs/audits/expert-ml/LATEST.md)。

上一版索引中的全部历史报告、补遗、争议、更正与旧状态均按该固定 SHA 原样保留；本轮没有删除任何历史审计 Markdown。旧“当前状态”按其固定源码 SHA 和审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际数据/日历/候选指纹、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。
