# 专家 / ML 最新轮审

## 最新研究执行方案：VIR量价冲击恢复＋60—75分钟有效本地研究

- 完整报告：[`2026-09-20_22-00-19_JST.md`](./2026-09-20_22-00-19_JST.md)
- `publication_kind`：`AUDIT_AND_EXECUTION_PLAN_UPDATE`；不是新的H504实股训练结果。
- `audit_time_jst`：`2026-09-20T22:00:19+09:00`
- `reviewed_source_sha`：`908a41334eaf2f38570a7fb93954a63ebb80ad52`
- `reviewed_tree_sha`：`34273d2bb4cf275036ae57770858463ed61721cc`
- 报告发布提交：[`5114bbc925ca32acd838fb972b9429f41098b69a`](https://github.com/fy-god/pro-web-60d-strategy/commit/5114bbc925ca32acd838fb972b9429f41098b69a)
- 报告 blob：`3c535d7302637a7592cd2b2badbb512fd200cd31`，已按发布提交回读核验。
- 子实验：`EML-EXP-KDJ-PATH-001-REAL/VIR-01`；新增假设 `X19-VOLUME-IMPACT-RECOVERY`，接续X17/X18，不重置旧实验台账。
- 新候选VIR比较两个不重叠10-session块的上涨/下跌“价格冲击÷相对成交量”不对称变化；原始impact、计数、coverage、one-sided全部保留。它是统计代理，不称机构吸筹，也不作为硬发布门槛。
- 主配对：M2I−M2、M2PI−M2P、M3I−M3，并以C-RAW（同底层原始信息、无VIR合成）和C-NOVOL（price-only impact）做归因控制；表格方向至少两个合法开发块一致后才进入同容量MLP/TCN。
- 本地执行目标改为：存在G0/G1合法READY工作时，单次连续完成**60—75分钟有效研究**；一个任务提前完成立即领取下一READY包，禁止sleep、重复同hash训练或空转凑时长。若所有任务真实阻塞而不足60分钟，必须记录`MIN_RUNTIME_NOT_MET + BLOCKED_*`，不能伪报1小时。
- 预算以用户当前v2为准：第一研究批次**累计48 fits / 180 wall-minutes**，不是此前文档曾出现的72/96 fits或360分钟；旧已用量必须从剩余预算扣除。90分钟launcher硬超时下，通过registry/checkpoint分片续跑，而不是一次硬撑三小时。
- 三段队列：Slice A真实数据/market calendar/TaskSpec/FeatureSpec/全量KDJ-path+pressure+VIR健康检查；Slice B合法H504折上的M1/M2/M2P/M2K/M2I/M2PI/M3/M3I/C-RAW/C-NOVOL；Slice C在剩余预算内进行MLP/TCN、错误切片和一次机制驱动配对再训。
- 当前审计沙箱container/Python仍在启动层`ClientError`，所以本轮新增pytest=0、模型fit=0、H504实股fit=0，60分钟执行目标在审计沙箱为`NOT_MET_BLOCKED_ENV`；这不代表用户本机缺数据或环境。
- 下一轮优先验收本地真实产物：`data_inventory/data_fingerprint/task_spec/fold_support/FeatureSpec/factor_health/vir_diagnostics/experiment_registry`，以及`effective_wall_seconds>=3600`的原始日志；若有合法H504折，再验收完整模型预测、hash、checkpoint和paired metrics。

---

## 最新独立复核：审计两份新报告 + open 项回归；发现**已发布产物已在重复计数克隆策略**

- 完整报告：[`2026-09-20_19-47-00_JST.md`](./2026-09-20_19-47-00_JST.md)
- `publication_kind`：`INDEPENDENT_REGRESSION_AND_NEW_REPORT_VERIFICATION`
- `audit_time_jst`：`2026-09-20T19:47:00+09:00`
- `reviewed_source_sha`：`cb785b8983c2ae3a21e049d74cbff46c462e3901`（`origin/main`）
- `reviewed_tree_sha`：`a7ee77503039a14bd15ed17f1d4c1d42703d6991`
- 报告发布提交：[`bb5c7326096808919713c1df3665c6a41a09d097`](https://github.com/fy-god/pro-web-60d-strategy/commit/bb5c7326096808919713c1df3665c6a41a09d097)（已 `git ls-remote` 回读 MATCHED；diff 白名单仅本报告与本索引）
- 审查区间 `c9b90e3..cb785b8` 共 **9 个提交**，其中 **2 份**是 `fy-god` 新写的报告（`17:31:44` ARR、`18:03:00` MEB）；`src/ experts/ tests/ scripts/ data/` 在该区间**零变更**。
- 本轮为核验实跑 `python -m pytest -o addopts="" -p no:cacheprovider -q` → **`15 passed in 4.45s`，REAL exit 0**；另写 62 个探针脚本 + 4 个只读子 agent。**本轮 H504 实股 fit = 0，无新增市场成绩**（`research_verdict = NO_NEW_REAL_MARKET_RESULT`）。
- **【本轮最重要 · 已发布产物缺陷】`EML-P1-CLONE-DOUBLE-COUNT-PUBLISHED`**：`README.md:186-191` 与 `RESULTS.md:23-28` 的 "top 6 by lift" 表**6 行只对应 3 个机制**（`leader_momentum`／`relative_strength_rank`／`gap_follow_through` 各占 2 行；其中 4 行是 `strict_*` 克隆）。`reports/webpro_hit_rates.csv` **35 行中 16 行是克隆**。实测 **16 个 `strict_*` 的 raw score 与其 base 逐位相同（1600/1600 次比对，0 失败）**；36 个注册策略折叠后仅 **20 个独立家族**（11 个 base 各有 1–2 个克隆）。→ 克隆重复计数**已可见于发布文档**，不是未来风险。
- **【本轮新发现】`EML-P1-POOLED-NO-DEDUP`**：`src/live_readiness.py:155` 的 pooled 行取**全部** `webpro_signals.csv` 且**未去重**。我复算已发布值完全一致（`signals=646,718 / resolved=637,499 / gross_mean=0.004466 / net_mean=0.003446`）；**克隆行占 54.82%**；按 base 去克隆后 `gross_mean` → **0.003020（−32.38%）**；按事件去重 → **0.007182（+60.82%）**。
- **【本轮新发现 · 潜伏】`EML-P1-META-BLACKLIST-H10-NAMES`**：`src/ml/walkforward.py:58-61` 的 `META_COLUMNS` 是 **9 列 H10 旧命名黑名单**，而 `labels.forward_outcomes` 产出 9 个 H504 新列，其中 **8 个不在黑名单**。注入 18 个合同/未来列 → **18/18 全被接纳、0 被拒**（`select_features(cols,[]) == list(cols)` 亦为 True）。**当前运行时不可达**（`build_matrix.py:360-363` 把 H504 列改名回 H10 名，并在 `:520-524` 显式排除），属命名契约陷阱。
- **【已确认 FALSE】`17:31` 报告 L37** 把 `walkforward.py` 的"**黑名单**"描述成"**显式 FeatureSpec 白名单**"，方向恰好相反；`FeatureSpec` 在全部 131 个提交的 `*.py` 中**从未出现**（`git log --all -S FeatureSpec -- *.py` 空；`git grep -i feature_spec` exit 1）。这会把**尚未修复的泄漏风险**写成**已落地的防护**。
- **【`UNVERIFIABLE`】`17:31` ARR 报告的执行证据无法复算**：`python -m arr_candidate.scan_real --help` → `ModuleNotFoundError`，**REAL exit 1**；`git rev-list --all --objects` 的 **3,060 个对象中 0 个**命中 `arr_candidate`/`evidence/`；两个 SHA256 **只出现在该报告 Markdown 自身**；仓库唯一 npz `679f3231…` 与两者都不匹配。**不判造假，判无法复算**，且**不采信**其 `49 passed` / 12 fit / log-loss 表。
- **【报告间矛盾 · 待澄清】** `17:31` 第 12 行写 `EXECUTED_IN_AUDIT_SANDBOX`，30 分钟后的 `18:03` 第 13 行写沙箱 `container/Python` **仍**返回 `ClientError` —— 两者不能同时为真。
- **【本线自我纠正 · 方法性】上轮"KDJ 从未执行"是错的**：把 `tests/test_engine.py:317` 的 KDJ 断言（`< 10` → `< 0`）改坏后，失败点落在 `test_wilson_upper_bound_is_not_a_constant`，且 stdout 先打印 `ok wilson_...` —— **证明 KDJ 断言确实执行**。正确表述：**已执行但无独立 test id、失败会被前面的 Wilson 断言遮蔽**。该项**降级为 `未复现`**。根因是"把未观察到当成未发生"；已固定纠正动作（**必须**给出独立 test id／打桩计数／变异测试三者之一）。
- **回归核对（上轮 8 项）：6 项仍 OPEN、2 项 `未复现`（需降级）、0 项已修复**。仍 OPEN：entry 取下一**个股行**、H504 `Close>4E` 未实现、cooldown 用帧内时钟、fetch 失败仍发 `PASS`、RSI meta-leak（潜伏）、RSI 截断、研究队列缺失。
- **实股计数逐项精确复现**（`data/panel_daily.parquet`，2,680,715 行／3,193 股／887 日）：个股行相邻但市场日不相邻的边 **943**、涉及 **586** 股、逐年 **172/184/327/260**、`|gap|>9.5%` **296**、`>10%` **206**、`>20%` **0**、缺口长度 mean **4.80**／max **46**、跳空 median **0.0503**／p90 **0.1008**／max **0.1137**。RSI：`rsi14>45` **97/100**、min/mean/max **42.22/67.38/100.00**、score **0.0354/0.2095/0.4926**、fires **0/100** —— 全部与上轮一致。
- **上轮三处口径错误已更正**：①「**596 只股票**」应为 **586**（我穷举多种分母，**无一种给出 596**；`901` 是含上市前空白的分母，不可用于停牌叙述）；②「`|gap|>5%` = 531」**我实测 530**；③「KDJ 从未执行」见上（**方法性误判**）。子 agent 报的「注入 18 列 → 17 被接纳」我实测为 **18 → 18**，已更正。
- **`18:03` MEB 报告**：机制正确、6 个恒零名单正确，但 ①量化低报（只举 2 家族／4 克隆，实为 **11 家族／16 克隆**，且从未给出 **36→20** 这个关键结论）；②「新证据」框架不成立 —— 同一事实早在 `audit/OTHER_PROJECTS_AUDIT.md:461`（提交 `bda8f3d`，**2026-09-16**）记载，我实测该报告对先例的引用命中数**全部为 0**，**应补引**；③6 个"恒零"在**真实**面板上 **5/6 会发射**（只有 `accumulation_base` 真恒零，它也是唯一不在已发布 signals 中的策略），不可外推。
- 本仓库**无** `docs/audits/validate_latest.py`（全部可达历史中从未存在），本轮**不声称**通过该闸门。
- **【本线事故 · 已完整恢复】** 上传同步时我误用 `git reset --hard`，把并发写者未提交的 `scripts/register_fixup_task.ps1` CRLF 修复一并抹掉；已从 `git fsck` 的不可达 blob `a2c6b859…` 恢复（174/174 行逐行一致），`git status` 复原为 ` M scripts/register_fixup_task.ps1` + `?? .gitattributes`。残余不确定性：无事故前哈希可比对。此后禁用 `reset --hard`/`checkout -- .`。
- **下一轮优先验收**：`README.md`/`RESULTS.md` 排名表按机制去重（或加 `family_id` 列）、`live_readiness` pooled 明确去重口径、`META_COLUMNS` 改语义判定（或让 `forward_outcomes` 直接产出规范列名）、`17:31` 候选包若真实存在请提交产物或撤回执行声明、两份报告的沙箱能力矛盾请澄清、KDJ 断言拆为独立 test id（收集数 15→16）。

---

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
- `reviewed_source_sha=c9b90e37f68c0419aef71d6508aa3d2dd5a6d18bf0`
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