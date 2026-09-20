# 专家 / ML 最新轮审

## 最新专项研究：MEB机制家族去重融合

- 完整报告：[`2026-09-20_18-03-00_JST.md`](./2026-09-20_18-03-00_JST.md)
- `publication_kind`：`FOCUSED_FUSION_AUDIT_AND_EXECUTION_PLAN_UPDATE`
- `audit_time_jst`：`2026-09-20T18:03:00+09:00`
- `reviewed_source_sha`：`d6a81439e7e2c176d8d2ed1d80e242d8b9fd94e5`
- `reviewed_tree_sha`：`40ddef7315bf5b44b1d0056f9caf36aed00c45d7`
- 报告发布提交：[`9445b290a65f14acb56264a797fb089168b0b3af`](https://github.com/fy-god/pro-web-60d-strategy/commit/9445b290a65f14acb56264a797fb089168b0b3af)
- 子实验：`EML-EXP-KDJ-PATH-001-REAL/MEB-01`；接续X17/X18、RSI/RRC与ARR-02，不重置旧台账或预算。
- 当前open PR：0。

### 本轮真实增量

本轮没有新的产品源码提交：从ARR审计基准 `b2fe936...` 到本次固定HEAD `d6a8143...` 只有上一份完整审计Markdown和本索引变化；H504主合同、market-session entry/cooldown、known_at/FeatureSpec等旧开放项不能自动标已修。

本轮重点转向“专家怎样无重复地融入ML”。源码确认 `_strict_selector.thresholded_decision()` 只复用base raw score/components并换阈值；`strict_relative_strength` / `strict_relative_strength_v2` 都属于 `relative_strength_rank` 同一家族，OBV的两条strict变体同理。100-card机器归档中两个relative-strength strict版本disagreement仅0.02，两个OBV strict版本仅0.01。

100-card归档还显示6/36专家在全部100张卡上 `predicted_yes_count=0`：`accumulation_base`、`first_board_breakout`、`high_level_consensus`、`reversal_engulf`、`rsi_mean_reversion`、`turnover_weak_to_strong`。这不证明对应机制在H504无效，但证明hard-vote专家数量不能当独立信息数量。

新增候选 **MEB（Mechanism-Equalized Breadth）**：threshold clone先映射到base `family_id`；每个base raw score仅用训练块经验CDF变成冻结 `family_q`，再计算soft breadth、75/90分位支持数、coverage和dominance。开发/校准/测试禁止重新拟合分位。MEB不是概率或硬门槛；模型同时消费family向量和摘要，strict threshold仅作policy/诊断，不作独立家族票。

同条件矩阵F0—F8比较：基线、36 hard votes、36 raw scores、family base raw、family q、+MEB摘要、与RSI/ARR/PDC合流、clone×5不变性负控制、family-label shuffle。主比较依次检验clone去重、分位标准化、广度摘要。只有存在合法H504开发折才可产生H504增量结论。

本轮GitHub与机器归档读取、报告发布和回读实际完成；当前审计沙箱container/Python启动仍返回ClientError，所以没有新增pytest或市场fit，不能把ARR上一轮49 passed/合成21 fit重新包装成本轮执行。

### 本地执行重点

本地agent继续9包：数据/预算续接；生成并数值验证 `family_map.json`；100-card逐样本raw-score/family归因；全历史family feature-health和ECDF漂移；合法折上F0—F8表格配对；真正OOF family meta；有稳定方向后才跑MLP/TCN三臂；错误切片后只允许一次机制驱动再训；最后持久化registry/checkpoint/hash/resume。

沿用17:31报告的累计上限 **360分钟 / 72次实际fit**，不因新报告再次扩容或清零。MEB子批次最多建议28个新增fit并从总额扣除；前置结果否定MEB就立即停掉后续NN，把预算转给其它READY任务。当前launcher每个子agent90分钟硬超时，因此研究必须分段resume，不通过sleep/重复同hash训练凑时长。

下一轮优先验收：非docs源码diff、`family_map.json`、cards逐样本raw-score表、`family_feature_health`、ECDF manifest、F0—F8完整预测、真正OOF family预测、experiment registry累计消耗、错误切片、checkpoint hash和精确resume命令。

## 上一专项：ARR冻结锚点恢复（保留）

- 报告：[`2026-09-20_17-31-44_JST.md`](./2026-09-20_17-31-44_JST.md)
- `reviewed_source_sha=b2fe93619f1b8c81733432abc0f9ce85503ae2fb`
- 发布提交：[`f54db37ea66056463d5a2e8d4ff6b479b53d39b8`](https://github.com/fy-god/pro-web-60d-strategy/commit/f54db37ea66056463d5a2e8d4ff6b479b53d39b8)
- ARR候选完成软件/合成训练，但HGB、MLP、TCN相对同信息对照没有一致增量；实股H504 fit=0。负结果保留，不继续扫ARR阈值制造收益。

## 最近一次完整独立源码复核（保留）

- 报告：[`2026-09-20_15-34-32_JST.md`](./2026-09-20_15-34-32_JST.md)
- `reviewed_source_sha=c9b90e37f68c0415331ca61e4e8acc3b13ce0bdf`
- 最终报告提交：[`eccc360585b1080b5cccd820a46848da06151cc2`](https://github.com/fy-god/pro-web-60d-strategy/commit/eccc360585b1080b5cccd820a46848da06151cc2)
- 该次本地复核确认：真实panel存在943条个股行相邻但市场日不相邻entry边；48/49次真实dedupe调用受错误signal-frame时钟影响；H504 Close合同存在High/Close反转；FeatureSpec黑名单可接纳未来合同列。具体量级和反例以该报告为准。

## 历史导航

- [`2026-09-20_13-57-11_JST.md`](./2026-09-20_13-57-11_JST.md)：H504 RED合同测试设计。
- [`2026-09-20_11-27-10_JST.md`](./2026-09-20_11-27-10_JST.md)：RSI归因独立复核。
- [`2026-09-20_09-58-00_JST.md`](./2026-09-20_09-58-00_JST.md)：SMA/Wilder/RRC对照。
- [`2026-09-20_07-26-54_JST.md`](./2026-09-20_07-26-54_JST.md)：100-card RSI专家不触发复算。
- [`2026-09-20_06-02-02_JST.md`](./2026-09-20_06-02-02_JST.md)：RSI连续信息融合任务。
- [`2026-09-20_03-41-46_JST.md`](./2026-09-20_03-41-46_JST.md)：RSI滚出分解独立复核。
- [`2026-09-20_03-06-03_JST.md`](./2026-09-20_03-06-03_JST.md)：RER候选与TOY接口训练。
- [`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)：贯通研究批次v2原计划。
- [`2026-09-20_02-00-47_JST.md`](./2026-09-20_02-00-47_JST.md)：历史完整源码审计与研究推进。
- [`2026-09-19_22-04-07_JST.md`](./2026-09-19_22-04-07_JST.md)：发布认证链审计。
- [`2026-09-19_18-00-42_JST.md`](./2026-09-19_18-00-42_JST.md)：fixup执行链审计。

## 共同边界

主任务仍是下一市场日有效Open、不顺延，未来504市场日Close严格>4E，之前含达标日Low>=0.8E，同日risk优先。旧High/个股bar/H10结果都不能替代。`label_end/known_at`必须贯穿fit/预处理/选择/OOF/meta/校准；publication先冻结signal_id再join未来outcome/execution。

当前归档只有887 market sessions，保守完整成熟train→成熟dev仍不足；先读取本地更早授权历史。无合法折时继续真实因子健康、cards归因、源码实现和prospective ledger，不随机拆成熟历史伪造H504 OOS。

> 源码SHA、报告提交、索引提交、软件测试、合成fit、真实市场fit和正式认证严格分开。文档提交或100-card练习结果不代表H504实股模型升级。
