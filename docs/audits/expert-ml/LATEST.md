# 专家 / ML 最新轮审

- 最新报告：[`2026-09-18_18-59-36_JST.md`](./2026-09-18_18-59-36_JST.md)
- `reviewed_source_sha`: `5081139b65de45f2e015d403225b74958d563715`
- 上一审查基线：`2f2945bedcfff20deceb85b076d839b2e8f6633a`
- 报告提交：`b7804fd84939956515a21a0453c6b610abc06394`
- 审计时间：2026-09-18 18:59 JST
- 本轮确认的新 P0：strict-target first-hit 比较器不一致；stride=1 scan population baseline 漏掉 warm-up 过滤；next-stock-row 与 next-market-session 语义仍未统一；low-zone signal ledger 仍受未来 resolved 状态影响。
- 下一专题：先修 TaskSpec / population-contract 的可证伪回归测试，再做 temporal OOF calibration、expert mechanism de-cloning 与 pre-close fillability head。

> 本索引只指向已写入并回读核验的审计报告。审计报告提交本身不代表模型或实验结果发生改进；仓库已归档的市场成绩与本轮独立复验严格区分。