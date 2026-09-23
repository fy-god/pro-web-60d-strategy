# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 16:10:10 JST）：报告发布器连续 8 次无法发布（untracked 残留锁死 rebase）＋ FeatureSpec oracle 绕过是类级缺陷

- 完整报告：[`2026-09-23_16-10-10_JST.md`](./2026-09-23_16-10-10_JST.md)。
- 被审实时 `main`：`664b78d58e3e34a0e3937e944b54d63ad33e0e36`；tree=`c4ac8946d908f11b841a27da3e3d7f01346439bd`；Open PR=`未能核验`（本沙箱无 GitHub API 通道）。
- **新 P0** `EML-P0-REPORT-AUDIT-PUBLISHER-REBASE-BLOCKED-BY-UNTRACKED-LEFTOVER-001`：`scripts/scheduled_report_audit.py:248-266` 的 rebase 重试被两个 **untracked** 残留报告卡死（`--autostash` 不 stash untracked），`:257-260` 直接 return。生产日志 `logs/report_audit/scheduler.out` 直证 **连续 8 次失败、跨 28.0 小时**，远端 `reports/AUDIT_STATUS.md` 冻结在 `a8ae13c`（2026-09-22 03:15）；本地 main ahead 8 / behind 35，merge-base 恰为最后一次成功发布的提交。
- **P1 升级为类级** `EML-P1-H504-ORACLE-ALLOWLIST-BYPASS-CLASS-NOT-INSTANCE-001`：独立穷举确认上一轮点名的 2 列（`bars_scanned`、`first_missing_session`）**恰好就是全部**（18 列 / 未覆盖 2 列），但补这 2 个名字**修不好这个类**——实测未点名的第三列仍被放行；改用本仓库自己的 allowlist 才拦下。
- **新 P1** `EML-P1-FEATURE-SCHEMA-WRITTEN-BUT-NEVER-READ-001`：`run.py:112` 每次运行都写出规范 `feature_schema.json`，但产品源码里是 **1 writer / 0 reader**——修复资产已在，只差接线。
- 真实测试真数：`python -m pytest` = **65 passed in 30.18s**，exit 0；该套件对上述 oracle 缺陷类**完全盲**。
- 四状态：GitHub 报告=`YES`；本机 runtime applied=`NO_LAST_VERIFIED / NOT_RECHECKED_THIS_TURN`；本机单次 3h completed=`NOT_VERIFIED`；新实股成绩=`real_market_fit_count += 0`。

## 当前最小落地顺序

1. 先修发布器（唯一能让本仓库对外状态恢复可见的项）：rebase 前 `--include-untracked` 收走残留，或改为直接推送单个 status 提交、不 rebase 本地分支。
2. 把训练入口的安全门接到 `run.py:112` 已产出的 `feature_schema.json`，并加“实跑 label builder 后断言其全部输出列都被拒”的契约测试。
3. 让发布失败参与退出码/被检查项，不再 28 小时无人发现。
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
- REAL calendar/evidence fail-open、AUX 主线抢跑、target_active_seconds 未形成成功退出硬门、direct stage 绕过完整 session receipt。
- `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`、`EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`、股票代码 key-space/alias 风险。

## 前一版索引（不可变保留）

[截至上一版（最新审计（2026-09-23 14:06:58 JST）：`FeatureSpec` 仍可显式接入未来 oracle 字段 `bars_scanned`）的 LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/664b78d58e3e34a0e3937e944b54d63ad33e0e36/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。

下一份真正改变市场研究状态的证据仍必须来自用户本机：真实 registered task/runtime、`local_start_receipt`、实际 panel/calendar/basis/候选指纹、重新生成的 H504 outcome ledger、candidate-aware 合法 fold、真实 registry/checkpoint/full predictions 与 `execution_receipt`。GitHub 文档发布或软件 smoke 不等于 H504 成功率提升。
