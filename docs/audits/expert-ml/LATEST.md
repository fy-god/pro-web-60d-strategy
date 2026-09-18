# 专家 / ML 最新轮审

- 最新报告：[`2026-09-18_23-03-03_JST.md`](./2026-09-18_23-03-03_JST.md)
- `reviewed_source_sha`: `6bc7fa229d6770e1fb3429c20a2a6133c3d9459d`
- 上一审查基线：`5081139b65de45f2e015d403225b74958d563715`
- 报告提交：`ddec7cbde5bda357b1d07f39b2b17078f366aca0`
- 审计时间：2026-09-18 23:03 JST
- 本轮新增确认 P0：`dedupe_signals()` 的 60-session cooldown 实际按信号帧的 unique signal dates 计数，而不是 exchange market sessions；同股 day0/day60 在稀疏信号帧中可被错误计成 9 个“session”，且别的股票信号密度会改变该股去重结果。
- 旧 P0 状态：strict-target first-hit `>=` 与最终 `>` 仍未统一；next-stock-row 与 next-market-session 仍未统一；stride=1 scan population baseline warm-up 过滤仍不一致；low-zone signal ledger 仍受未来 resolved 状态影响。
- 验证层进展：fail-open section census、关键 artifact 内容断言、结构化 audit summary 与新增 mutation-style tests 已进入 main；当前仓库归档为 629 checks / 0 problems，但定时 audit 仍在 current working tree 而非 detached `origin/main` 上运行，尚不能作为 clean-SHA attestation。
- 下一专题：先检查 X9/X10/X11/X12 的 TaskSpec/event-policy 修复；若基础契约修好，再审 temporal OOF calibration、expert mechanism de-cloning 与 multi-horizon competing-risk landmark stack。

> 本索引只指向已写入并回读核验的审计报告。审计报告提交本身不代表模型或实验结果发生改进；仓库已归档市场成绩与本轮独立复验严格区分。