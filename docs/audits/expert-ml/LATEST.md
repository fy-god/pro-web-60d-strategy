# 专家 / ML 最新轮审

## 最新报告

- 完整报告：[`2026-09-19_04-05-29_JST.md`](./2026-09-19_04-05-29_JST.md)
- 原审计记录时间：`2026-09-19T04:05:29+09:00`（来自本对话原交接记录）。
- `reviewed_source_sha`：`0df81c65a5a2765027d6447c3cf24e4760e0c5e8`
- 仓库前一份归档审查基线：`14a2e834985248029f23750b80782c9fa5b36f12`；本报告是本对话首份基线，不把仓库其他归档冒称为本对话完成。
- 报告发布提交：[`4bac1e79cbdcae2a4a21c6270ff93987ca94a13a`](https://github.com/fy-god/pro-web-60d-strategy/commit/4bac1e79cbdcae2a4a21c6270ff93987ca94a13a)
- 报告文件Git blob：`d08b7c290fe6c3e88df522f1f36521afc7a6abe3`；发布后已按上述commit回读，哈希与完整待上传文件一致。
- 原始报告SHA256：`1f5a9627615b19b240534009b42cee353efd18c487634a9a2d59e78cee439713`；补传保留原文全文，仅增加历史状态说明及固定源码入口。
- 本次发布性质：2026-09-19授权后的历史报告补传，不是新一轮审计、不重新执行15项检查，也没有新市场训练或收益结果。报告中的“未创建排程／未上传GitHub”描述原审计时的历史状态，不能作为当前状态。

## 开放问题与下一步

以下状态对应报告固定源码SHA，后续轮次须重新读取实际实现确认，不把本索引当新源码证据。

- 时间边界：`EML-P0-YEAR-KNOWN-AT`、`EML-P0-KNOWN-AT-GAP`——年度拟合与历史阈值评分缺逐行可知时间隔离；市场日purge与个股bar标签终点不一致。
- 发布与任务：`EML-P0-ML-COHORT`、`EML-P0-LEDGER-ORDER`、`EML-P0-COOLDOWN-GRID`、`EML-P0-SESSION-ALIGN`、`EML-P0-H504-HIGH-CLOSE`——候选、未来完整性、冷却时钟与H504 Close联合目标需统一。
- 特征与统计：`EML-P1-DOWNVOL-EMPTY`、`EML-P1-ZERO-SIGNAL-BASE`——五日互斥涨跌组各要求三条记录导致量价比无法有效；零信号折不应从自然基率总体删除。
- 其他需推进：`EML-P1-RULE-SHAPE`、`EML-P1-FRONTIER-TIES`、`EML-P1-RESULT-SCHEMA`；特征白名单、专家家族去重、数据PIT和干净版本认证风险详见完整报告。
- 保留已修控制：严格比较器、共享scan/baseline选择掩码、Close标签原始float64入场价；不能重复报为未修。零信号折缺陷未被证明改写现有七模型榜单。
- 实施顺序：WP1数据与任务冻结 → WP2标签及as-of / WP3机制与家族 → WP4时间外评分 → WP5损失、meta、独立校准 → WP6发布账本 → WP7计数与不确定性 → WP8版本验收。完整报告包含八个工作包和可复制agent执行段。
- 基础契约实验：X13 High/Close parity、X14 outcome-independent ledger、X15 market-session cooldown、X16 next-market entry。
- 下一优先研究：`X17-KDJ-PRESSURE-PATH`，仅为待验证假设，在基础契约与数据时间可行性通过后开展；区分空列修复、新路径信息和元学习增量。

## 文档交付范围

现有专家／ML自动任务已更新为“本对话完整交付＋GitHub审计文档同步”，继续使用Asia/Tokyo每日01:00、05:00、09:00、13:00、17:00、21:00的原排程。

GitHub写入仅限新增本目录审计Markdown和更新本索引。源码、配置、权重、reports/、AUDIT_STATUS、SCHEDULE.md、Actions及PR均不在写入范围。任务提示词要求每轮实际写入并回读核验；权限、网络或保护规则失败时须在对话说明，不把配置成功等同于未来每轮已发布成功。

## 前一份仓库归档（历史记录保留）

- 报告：[`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)
- `reviewed_source_sha`：`14a2e834985248029f23750b80782c9fa5b36f12`
- 上一审查基线：`6bc7fa229d6770e1fb3429c20a2a6133c3d9459d`
- 报告提交：`7730f6380ceb3c788227a6b9254fb6d3a7fc2c05`
- 原审计时间：2026-09-19 03:00 JST。
- 该轮记录`EML-P0-LABEL-TIE`和`EML-P0-SCANBASE-S1`已修；归档blast-radius显示当前panel上0个strict-low outcome flips，不代表模型精度提升。
- 该轮确认cooldown信号日期时钟、next-stock-row、future-resolved先于ledger、H504 High/Close差异仍待修。发布器race有所改善，但clean-SHA和push-scope风险未解除。
- 该轮读取的历史AUDIT_STATUS为629 checks / 0 problems / remote drift 0；这不是本次补传重新运行的结果，也不是对当前GitHub版本的完整认证。

> 本索引区分审计源码SHA、报告发布commit和历史归档。文档提交不代表模型升级；15项合成检查不等于市场训练、收益或命中率验证。
