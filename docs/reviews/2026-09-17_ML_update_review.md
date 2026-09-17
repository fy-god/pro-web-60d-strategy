# 更新复查：ML验证、精确率前沿与长期低位模型优化

日期：2026-09-17。固定审查提交：`c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91`；比较起点：`bda8f3df43db808864f3bef52473e0a833cb38d5`。

## 1. 结论与证据等级

这轮新增了真实的工程内容：连续数值特征、市场与横截面背景、walk-forward、留出评价、负控制、成交可能性与收益诊断。相对于固定36个规则的排行榜，这是实质推进，不能继续用旧评价说项目只有几个分类器。

但两条最强结论需要撤回或收窄：

1. `precision_ceiling.py`只能给出固定模型分数的事后阈值前沿，**不是所有模型或所有特征的数学上界**。不能据此宣布“任何模型都不可能70%”。
2. `final_holdout.py`声称独立的一次2026留出，但训练仅按信号日期<2026过滤，没有清除结果窗跨入2026的训练标签。**当前196/1614=12.14%应保留为已提交、待重新验证的结果，不能称为无泄漏最终认证。**

此外，新ML主要目标是10日+30%的`label_high`或`label_close`，并未等同于“504日收盘严格>4倍且达标前low>=0.8E”的长期低位目标。短期效果不自动迁移，负面短期结果也不能否定长期任务。

本报告做了真实源码读取、提交比较，以及定向软件/算术反例。没有取得完整原始市场面板、没有重跑全市场拟合，没有估计修复后实股提升幅度。仓库已有数字与本次计算严格分开。

## 2. 已实现的进步应当保留

| 新内容 | 价值 | 不能由此推导的结论 |
|---|---|---|
| `src/ml/build_matrix.py`连续特征 | 减少clip导致的幅度信息丢失；加入KDJ、市场、横截面 | 82个字段不等于82个独立有效因子 |
| `walkforward.py:folds` | 显式引入时间块、purge、开发与最终区间 | 没被调用的另一个holdout入口不会自动受保护 |
| `null_tests.py`及控制实验 | 可发现部分泄漏、无效输入或记忆行为 | 控制通过不构成所有训练路径无泄漏的证明 |
| `final_holdout.py`日期聚类区间 | 比把同行情日所有股票当独立观察更合理 | 未处理跨日期重叠和重复股票的全部依赖 |
| `tradeability.py` | 开始区分价格路径结果和执行问题 | 日线开在涨停价不等于已经证明没有成交卖盘 |
| 收益、命中率分开 | 触及目标与到期收益确实不同 | 10日退出规则不能替代504日识别目标 |

## 3. P0：所谓“数学上界”实际上只约束一个给定排序

### 3.1 从函数直接看

`precision_ceiling.py`先拟合固定HGB，得到`s_te`，然后：

```python
order = np.argsort(-scores, kind="stable")
tp = np.cumsum(y[order])
```

所有前沿点都依赖这个固定排序。后续打印却写：

> No threshold, model or hyperparameter choice can exceed the oracle rows above.

这句话超出了计算证明的范围。

**正确表述：**在本次已拟合模型、给定分数、给定候选队列、给定标注、指定样本约束下，事后挑选阈值能达到的经验精确率前沿。换模型或特征会改变排序，因此不受这个前沿约束。

U07软件反例：相同10个标签、2个正例，最低2条信号。排序A把正例排最后，其最佳前缀精确率20%；排序B把正例排最前，则100%。这是纯数学反例，不是实股模型，不证明70%可实现；它只推翻“排序A限制所有排序”的推理。

### 3.2 当前前沿甚至不总等同于“所有可实现标量阈值”

- 前2000个k枚举、之后只采约200点，是稀疏经验网格，不保证得到2000以后全部k的最优值。
- 分数相同的样本被stable sort按输入顺序排列。若在并列组内部截断，这不是单一`score>=threshold`能实现的集合。
- U12反例：10条同分0.5，前2条恰为正，代码前缀k=2显示100%；真正非空标量阈值只能全选10条，精确率20%。
- 在测试折内做百分位归一化使用整段分数分布，可以作为事后诊断，但不是该折早期可实时冻结的阈值。

建议重命名为`fixed_score_frontier.py`；精确标量阈值只在不同分数的组末计算；Top-K另列并锁定并列处理规则。报告中删除普适不可能性和“no model can exceed”措辞，保留贝叶斯公式作为目标难度说明。

### 3.3 正确的70%讨论

`PPV = pi*r / (pi*r + (1-pi)*f)`是正确恒等式。它说明给定基率pi与召回r时，需要怎样的误报率f；它没有给出所有模型可达到的最小f。

下一步应比较新增信息能否改善同预算、同召回区域的错误结构，不是靠现有模型前沿提前结束研究。也不能只选1条成功样本宣布解决问题。

## 4. P0：最终留出入口缺少标签时间隔离

### 4.1 具体代码路径

`final_holdout.py:main`使用：

```python
train = frame[frame["date"] < cutoff]
test = frame[frame["date"] >= cutoff]
tr = train[train["label_high"].notna() & train["resolved"].fillna(0).astype(bool)]
```

`resolved`是在完整面板上计算的，不是截至模型生效时点的可知性。12月末样本的10日结果可能包含1月价格，但仍进入训练。

这条入口没有调用`wf.folds`中的purge。U08用一份独立工作日日历与10日标签末期构造，日期筛选保留了10条标签末期越过2026边界的训练行。该反例证明逻辑漏洞，不是实际市场受影响行数；后者必须从原面板生成泄漏明细。

### 4.2 修复不能只删最后十行

删除的应是每一行`label_known_at >= fit_asof`，保守完整随访基线使用`label_end >= fit_asof`。期限是市场会话，不是抽样后矩阵行数，更不是整个DataFrame最后十行。

新增断言与输出：

```python
assert (train.label_end < model_fit_asof).all()
assert (calibration.label_end < policy_frozen_at).all()
```

导出被purge行的code、signal_date、label_end、越界长度与标签。日期集合由独立交易所日历提供；个股停牌不延长目标期限。

### 4.3 “只运行一次脚本”不等于全项目从未看过留出

先前规则评价、图表、收益诊断已覆盖2026。不能仅因`final_holdout.py`只有一组配置，就证明研究者从未利用过2026信息。

建议将当前2026结果标为`historical_holdout_with_prior_project_exposure`，并追踪模型和特征冻结记录。已经看过的测试段不能通过改文件名重新变成未见数据。新的正式检验应使用预注册未参与选型的后续时间段或真正未用于开发的独立数据；长H标签需等待或使用已有、确实未接触的更早留出。

## 5. P1：当前仍是短线bull目标，不是长期joint目标

`build_matrix.py`产生`label_high`和`label_close`，默认H10、target0.30；`final_holdout.py`固定`label_high`。两个标签只描述是否达到收益目标，没有在ML输出里把先破0.8E作为联合失败。

单改CLI为`--horizon 504 --target 3`不够，因为：

1. `wf.folds`或其他入口可能仍固定horizon10。
2. `META_COLUMNS`采用黑名单，新增`label_joint`或`goal_day`若未更新，可能进入`feature_columns`。
3. 数据加载可能仍选择旧矩阵。
4. 同一分数的短期最优阈值不适合长期目标。
5. 训练期、成熟期与独立校准的时间预算完全不同。

改成`TaskSpec`贯穿构建、训练、评估、绘图与缓存；显式特征白名单；特征表和标签表物理分离。短期实验保留原名，新的长期路线命名`joint_close4x_H504_low80_v1`。

## 6. P1：全局抽样依赖其他股票，且不能支撑严格同日横截面比较

`build_matrix.build`最后使用`out.iloc[::stride]`。DataFrame按股票拼接，前面任一股票增删一行，会改变后面所有股票的抽样相位。

U09：A原本选日期[0,5]；前面加入另一股票的一行后，A变成[4,9]。A自己的行情完全没变。

如果每股不同相位抽样，还会使所谓“当天Top1”只在部分轮到抽样的股票中选择，不能解释为完整市场横截面的Top1。真实影响需核查具体调用者，但基矩阵的行为已经确定。

改法：完整历史计算特征；由固定市场日历选统一评分日；当日所有合格股票评分。训练降采样可独立设置，校准、验证和正式发布保持与生产一致的每日频率。两周查询只过滤已生成账本，不重新预热特征。

## 7. P1：所谓close浮点修复仍混入float32入场价

当前先把`entry_open`转成float32，随后再转回float64计算：

```python
close_ratio = run / (out["entry_open"].to_numpy("float64") + EPS) - 1.0
```

转回float64不能恢复丢掉的原始精度。U11：原始entry9.99、close39.96，严格四倍应为False；entry经float32变9.989999771118164后，原表达式可能变True。

标签层保留原始float64或明确的定点价格及复权因子。优先直接比较`future_close > entry*target_multiple`，不要为了防零加EPS改变所有边界；零入场价应报错。测试精确边界、前后一个tick、调整后非两位小数价格，特征层可使用float32，标签层不要因此降精度。

## 8. P1：执行过滤是保守情景，不是从日线证明无卖盘

`tradeability.py`用`gap >= limit-0.005`标记`unfillable`。需要区分：

- 涨停附近开盘是风险提示，日线不能直接确定你的订单队列和成交结果。
- 全日一字、高低开相等也是日线信息，不能作为开盘时已经知道的筛选特征。
- 下一条个股bar可能是若干市场会话后的复牌，不一定是次日。
- ST、上市初期、特殊除权等状态缺失时，固定幅度法只是代理。
- 观察到未来全日成交量才决定是否假设开盘已成交，会引入执行条件的后验信息。

U10只验证代码0.5个百分点容差把9.6%缺口也归为10%涨停附近，不是对某只实际股票可成交性的判决。

建议分别输出`observed_open_at_limit_proxy`、`execution_unknown`、`conservative_skip_scenario`、`verified_fill`。真实执行验证需订单类型、提交时点、开盘集合竞价或逐笔数据；没有这些时报告上下界情景，不宣称已完整解决交易可行性。

## 9. 校准与发布时间政策要分开

训练集拟合后在训练分数上取top2%不是直接使用测试标签，不能把它一律叫未来泄漏；但训练内分数更极端，阈值迁移后发布率会漂移。类加权和正例重采样又会改变概率含义。

建议：

1. 基础模型拟合使用截至F已知的数据。
2. 模型冻结，对后续历史校准段生成分数，不在该段重拟合基础模型。
3. 等该段标签在政策冻结时点可知后拟合校准器。
4. 另一个过去的政策段选择发布阈值、最低质量与容量上限。
5. 新模型发布即绑定自己的校准器和TaskSpec；重拟合后不能直接套旧阈值认证概率。

官方概率校准文档也要求基础模型拟合数据与校准数据分离。时间序列需进一步遵守标签可知时点，而不是使用默认随机CV。

最终Top-K只是容量上限，不能为了每天凑K只降低质量门槛。两周没有信号可以是诚实结果，但必须区分没有合格机会、代码失败、输入缺失与未校准四种情况。

## 10. 下一轮真正的专家模型优化

### 10.1 保留什么

保留新建的原始连续量、KDJ、市场残差和横截面背景。规则专家作为可解释的辅助信号，不把每个阈值版本当独立专家。相同基础分数多个阈值归为同族。

### 10.2 怎样优化

| 实验 | 唯一主要变化 | 检验 |
|---|---|---|
| E0 | 固定任务、修purge/日历/标签/账本 | 修复前后分母变化，不宣称算法提升 |
| E1 | 同任务Joint-GBDT | 基准概率、同政策自然基率 |
| E2 | 加未clip专家分量 | 是否胜过只用专家0/1与固定权重 |
| E3 | 按机制去重并增加上下文交互 | 同日期、同预算下是否减少伪共振 |
| E4 | 加独立时间外生成的神经网络表征 | 是否提供不同于原82字段的增量 |
| E5 | 基础模型+专家元模型 | 必须用过去OOF分数训练第二层 |

深度表示只作为候选信息，不预设一定胜过GBDT。若同队列、同目标、相近复杂度下无增量，保持GBDT。

### 10.3 针对性错误分层

每条已发布信号按未来结果分为：未四倍且未破低位；先破低位；四倍但不满足严格路径；联合成功；结果未知；研究入场不可用。优化需针对失败类型，不能统一提高所有门槛。

例如大量timeout意味着模型只识别安全横盘，需增强启动与幅度信息；大量先risk意味着入场结构不稳；大量市场同日误报意味着缺少个股相对背景。所有解释以分层计数为依据。

## 11. 评价：不要把窗口、发布事件和独立牛股混成一个数

主报告至少包含：

```text
n_eligible_stock_days
n_published_signals
n_mature_published
n_unresolved_published
n_entry_unavailable
n_joint_hits
joint_precision = n_joint_hits / n_mature_published
distinct_stocks / distinct_signal_dates
positive_episode_count / detected_positive_episode_count
recall_at_signal_budget
Brier / logloss / PR-AUC
```

主Precision采用固定、可比较的成熟信号日期队列；不能只纳入最近已经成功的信号，而把尚未失败者排除。事件Recall需预注册`episode_id`构造，分母独立于模型信号产生。相邻正窗口不能按独立牛股计数。

同日聚类Bootstrap比行级独立假设好，但长H存在跨月重叠和股票依赖。补充按较长日期块、按股票以及两者的敏感性分析；不要把HHI倒数称为正式统计有效样本量。比较模型用同一重采样索引的配对差异，不用两个独立置信区间是否重叠代替检验。

不能因为删除最低表现折后均值提高，就称原结果“保守”。删任何低值都会提高均值，这是算术，不是可靠性的证明。应保留所有预注册折并解释漂移。

## 12. 缓存、注册与可复现性

矩阵名包含horizon/target/stride是进步，但还需要close/high、strict_low、数据快照、特征版本、日历、候选范围、执行政策。缓存不匹配即拒绝复用。添加任何新标签列不得自动成为特征。

每次输出独立的小文件：TaskSpec、FeatureSpec、split manifest、label-flow表、模型参数、校准参数、发布账本和逐信号标签。大型行情可放外部可验证快照，但README单独数字不是完整复现证据。

## 13. 本次已执行的定向反例

这些均为人工软件/算术检查，不是市场训练：

| ID | 内容 | 结果 |
|---|---|---|
| U07 | 相同标签、更换分数排序 | 固定排序前沿可被另一排序超越 |
| U08 | final holdout日期过滤与10日标签 | 构造中10条训练标签跨界 |
| U09 | 全局stride增加他股一行 | 本股抽样日期改变 |
| U10 | 9.6%缺口与0.5个百分点容差 | 被标记为10%涨停附近；成交仍未知 |
| U11 | 原始9.99与float32入场 | 精确四倍边界可能被误报 |
| U12 | 10条同分、前2条为正 | 前缀100%不可由非空标量阈值实现 |

上表U07–U12为可执行反例，脚本与真实执行输出就在本仓库[`audit/review_counterexamples.py`](../../audit/review_counterexamples.py)与[`audit/review_counterexamples.json`](../../audit/review_counterexamples.json)，运行`python audit/review_counterexamples.py`可复现表中数值。14项总诊断中另有U01–U06、U13–U14是原模型更新的标签反例，位于持有该训练代码的另一个仓库；此公开报告不复制该私有仓库的源码。未执行全市场fit。

## 14. 建议提交顺序与停止条件

1. **文档纠错提交：**收窄能力上限措辞；标记holdout时间隔离待修；不删除旧数字。
2. **共享标签与日历提交：**market_session、close/high口径、float64标签、timeout/censor。
3. **训练入口提交：**所有入口统一known_at验证；最终留出不能旁路。
4. **发布账本提交：**每日全候选评分、统一状态/冷却、无未来结果过滤。
5. **同任务基准提交：**真实全市场小规模验证，先检验分母与时间，再完整运行。
6. **模型增量提交：**连续专家组件、去克隆、神经表示；逐组消融。

任一时间隔离、价格契约或标签一致性测试失败，都停止该轮正式性能发布。支持样本不足输出不足，不以降低门槛或换目标补足。达到70%仍需独立测试，不因单次点估计超过即宣称解决。

## 源码与方法证据

所有源码链接固定于审查提交，而不是会漂移的main：

- [更新后的README](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/README.md)
- [precision_ceiling.py](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/src/ml/precision_ceiling.py)
- [final_holdout.py](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/src/ml/final_holdout.py)
- [已提交holdout计数](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/reports/ml_final_holdout.json)
- [build_matrix.py](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/src/ml/build_matrix.py)
- [walkforward.py](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/src/ml/walkforward.py)
- [tradeability.py](https://github.com/fy-god/pro-web-60d-strategy/blob/c97de8c3bf8ab7c7b74c1bbd25cf856a4853cd91/src/tradeability.py)
- [scikit-learn官方概率校准说明](https://scikit-learn.org/stable/modules/calibration.html)

本报告是代码审计与研究方案，不是交易建议，不包含收益承诺。