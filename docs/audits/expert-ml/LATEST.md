# 专家 / ML 最新轮审

- 最新报告：[`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)
- `reviewed_source_sha`: `14a2e834985248029f23750b80782c9fa5b36f12`
- 上一审查基线：`6bc7fa229d6770e1fb3429c20a2a6133c3d9459d`
- 报告提交：`7730f6380ceb3c788227a6b9254fb6d3a7fc2c05`
- 审计时间：2026-09-19 03:00 JST
- 本轮已确认修复：`EML-P0-LABEL-TIE`（first-hit 与 bull 统一严格 `>`）和 `EML-P0-SCANBASE-S1`（scan / baseline 共用 selection mask）。仓库归档 blast-radius 显示旧 comparator bug 在当前 panel 上 0 个 strict-low outcome flips，因此不能宣称模型精度提升。
- 仍未解决：`EML-P0-COOLDOWN-GRID`（cooldown 仍按 signal-date grid）、`EML-P0-SESSION-ALIGN`（next stock row 仍非 next market session）。
- 本轮深化确认：`EML-P0-LEDGER-ORDER`——`score_signals()` 先按未来 `label_resolved` 删除信号，再做 cooldown/dedupe，未来完整性仍会改变历史发布事件；`EML-P0-H504-HIGH-CLOSE`——仓库 `low504` 仍以 `High>4E` 定义 bull，而当前主目标要求 `Close>4E`。
- 验证层：publisher push race 已加 fetch/rebase/retry，最新 `AUDIT_STATUS.md` 已发布 `629 checks / 0 problems / remote drift 0`；但 `EML-P1-AUDIT-CLEAN-SHA` 仍未解决，并新增 `EML-P1-AUDIT-PUSH-SCOPE` 风险：脚本未断言本地只领先一个 status commit，`HEAD:main` 理论上可夹带无关本地 commit。
- 本轮没有新的市场训练/收益/精度结果。下一专题：优先 X13 High-vs-Close H504 parity、X14 outcome-independent ledger、X15 exchange-session cooldown、X16 next-market-session entry；基础契约冻结后再做 temporal OOF threshold 与 residualized-cross / OOF path-risk / cluster-normalized training。

> 本索引只指向已写入并回读核验的审计报告。审计报告提交本身不代表模型或实验结果发生改进；仓库已归档市场成绩与本轮独立复验严格区分。