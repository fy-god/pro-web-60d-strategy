# 专家／ML最新研究与审计索引

## 最新候选推进：可执行 `--stage all` H504研究流水线 v3

- 完整报告：[`2026-09-21_10-08-25_JST.md`](./2026-09-21_10-08-25_JST.md)。
- 类型：`CANDIDATE_EXECUTABLE_PIPELINE_AND_REGRESSION_UPDATE`；不是新的实股H504成绩。
- 时间：`2026-09-21T10:08:25+09:00`。
- 被审默认分支：`64abac1778e5c3a439ce61a0a7774f71701c1297`；tree：`79b7e95e5e5c41c3348b35bd85a0f687e83bf71c`；Open PR=0。
- 报告提交：[`2dbd67efd44b8216c917b195a99d41f7cc698f1d`](https://github.com/fy-god/pro-web-60d-strategy/commit/2dbd67efd44b8216c917b195a99d41f7cc698f1d)，报告 blob `c95c6cb4e6198eb4ff06f7c1a3f990e0fddd93f2`，已按返回提交回读。
- 从上一索引 `0122fc6f...` 到本轮审计起点只有定时 `AUDIT_STATUS.md` 更新；产品 `src/experts/tests` 与模型结果仍没有新的提交，真实市场模型成绩没有推进。
- 当前 `AUDIT_STATUS.md` 同时写 `PASS` 与 `Remote drift = 2`；`scheduled_report_audit.py` 的 verdict 仍只看 consistency exit code 和 unstable，不把 changed/note 纳入PASS，因此认证状态不能替代源码/训练证据。
- 本轮隔离沙箱把候选从 session-clock v2 推进到可执行 v3：新增 `--stage all/features/h504-hgb/aux-tcn`、真实候选manifest fail-closed H504拟合入口、全量因子健康诊断、AUX causal-TCN、checkpoint/完整dev预测和JSONL resume registry。
- H504拟合不会自行把所有stock-day当低位候选；缺 `--candidates` 返回 `BLOCKED_CANDIDATE_MANIFEST`。无合法full-followup H504折返回 `BLOCKED_PROTOCOL_H504`，不把504缩成60/10。
- AUX-TCN仅在H504阻塞时推进真实历史表征：128-session causal window、feature+mask、6个双卷积残差块、dilation 1/2/4/8/16/32、RF=253；AUX目标与指标不得冒充H504成功率。
- 本轮候选测试 `29 passed in 2.45s`。合成集4次AUX-TCN fit完成；首轮外层中断后registry留下3个completed，完全相同命令续跑只补第4个fit，验证了基本resume能力。合成plus_research没有优于base，该负结果保留且无真实市场外推权。
- candidate v3 zip SHA-256=`0e0f579fa39e3a4341f1be2ca9de6b7bd820896bd231c8e06baaa2cc2743f35f`；v2→v3 patch SHA-256=`f9e0ab9526df72929e9f1f25e22433bda1f563cddd533a2fa82349ae18f10524`。候选代码未写入远端产品树。
- `real_market_fit_count=0`。用户本机 runtime 仍无 start receipt，单次三小时仍 `LOCAL_APPLY_PENDING / NOT_RUN / NO_EVIDENCE`。下一轮只有 `data_inventory/fold_support/feature_health + REAL/AUX_REAL registry + checkpoint + 完整predictions + execution_receipt` 才算真实本地研究推进。

## 最近成功独立审计：low504真实停牌面板窗口错位

- 完整报告：[`2026-09-21_03-50-40_JST.md`](./2026-09-21_03-50-40_JST.md)。
- 类型：`INDEPENDENT_REGRESSION_AND_REAL_MARKET_DEFECT_QUANTIFICATION`。
- 被审默认分支：`59788d8a1ba17d3ba3c3f6098758b66f784c63ab`。
- 真实A股面板复核确认：当前 `src/labels.py` entry/horizon仍按个股行空间；`low504` 成熟行中12.2237%实际跨越超过504个market sessions，最长590；停牌案例会把复牌open当次日entry。
- 当前冷却仍按信号帧自身日期秩，稀疏帧会过度抑制；`walkforward.META_COLUMNS`仍是默认放行黑名单。
- 该报告同时纠正：H=504 dense full-followup train→later mature dev 最低1010 sessions的算术成立，但不能据此宣称用户本机没有更长授权历史，也不能把产品H10结果当H504验证。
- 该审计没有新模型拟合，真实市场fit仍为0。

## 最新本地执行合同：单次连续三小时 v5

- 完整任务书：[`2026-09-21_01-43-18_JST.md`](./2026-09-21_01-43-18_JST.md)。
- 单次有效研究目标10800秒；正常wall上限12600秒；runner硬兜底13200秒；建议本项目Windows执行上限13800秒/PT3H50M。
- 旧75分钟切片、一小时验收和180分钟累计wall停止条件均被该人工合同替代；旧48次累计fit及已耗次数继续保留。
- 三小时任务不是等待凑时：数据/合同/因子→真实训练/预训练/消融→错误分析与一次配对修改；一个READY完成立即继续下一个。
- 后续自动轮次不管理排程；云端prompt更新、GitHub任务书发布、本机runtime实际接入、本机三小时实际完成四种状态分开验收。

## 前序候选与研究报告

- [`2026-09-21_06-03-05_JST.md`](./2026-09-21_06-03-05_JST.md)：H504 session-clock v2、training eligibility与market-session cooldown。
- [`2026-09-21_02-07-54_JST.md`](./2026-09-21_02-07-54_JST.md)：H504合同、FeatureSpec、fold-support、VIR基础候选。
- [`2026-09-20_23-50-06_JST.md`](./2026-09-20_23-50-06_JST.md)：独立回归、fetch失败仍PASS、克隆/冷却等核验。
- [`2026-09-20_22-00-19_JST.md`](./2026-09-20_22-00-19_JST.md)：VIR量价冲击恢复方案。
- [`2026-09-20_18-03-00_JST.md`](./2026-09-20_18-03-00_JST.md)：MEB机制家族去重融合。
- [`2026-09-20_15-34-32_JST.md`](./2026-09-20_15-34-32_JST.md)：独立回归与实股影响核查。
- [`2026-09-20_13-57-11_JST.md`](./2026-09-20_13-57-11_JST.md)：H504合同与回归测试审计。
- [`2026-09-20_09-58-00_JST.md`](./2026-09-20_09-58-00_JST.md)：RSI归因及恢复共识。
- [`2026-09-20_06-02-02_JST.md`](./2026-09-20_06-02-02_JST.md)：RSI连续信息专项。
- [`2026-09-20_03-06-03_JST.md`](./2026-09-20_03-06-03_JST.md)：RSI新增/滚出分解。
- [`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)：贯通研究批次v2。

> 历史报告文件均保留。最新候选实现、最新人工执行合同、最近成功独立审计、产品源码状态和真实市场成绩分别记录；软件测试、合成训练、候选代码与真实A股模型结果不得互相替代。
