# 专家 / ML 最新轮审

## 最新专项研究：RSI归因纠偏、Wilder对照与恢复共识

- 完整报告：[`2026-09-20_09-58-00_JST.md`](./2026-09-20_09-58-00_JST.md)
- `publication_kind`：`AUDIT_AND_RESEARCH_QUEUE_UPDATE`
- `audit_time_jst`：`2026-09-20T09:58:00+09:00`
- `reviewed_source_sha`：`a0ca60b4fc9dc73de0b4ff7ce6b753fc3afd1753`
- `reviewed_tree_sha`：`74cda26fa40f00cf7a0459e390daea04ddbae9e0`
- 报告发布提交：[`ddfde0e27741cd1339c9be06fc5765e19d3769dc`](https://github.com/fy-god/pro-web-60d-strategy/commit/ddfde0e27741cd1339c9be06fc5765e19d3769dc)
- 子实验：`EML-EXP-KDJ-PATH-001-REAL/RSI-ATTR-03`，接续 `RSI-CONT-02`，不替代 X17/X18 主线。
- 新增确认 `EML-P1-RSI-ATTRIBUTION-CONFOUND`：上一轮真实100-card重算只有 **3/100** 张卡的旧 `rsi_oversold` 分量非零。50正/50负的2500个AUC正负配对中，至少 **2350对（94.0%）** 两边RSI分量都为0，因此旧复合专家总分约0.58的练习集排序不能被解释成“RSI本身有排序增量”。旧RSI分量加权贡献均值仅约 `0.00111`、最大约 `0.04164`。
- 新增确认 `EML-P2-ML-RSI-COVERAGE-GAP`：当前 dense ML matrix 的82个正式特征含KDJ但没有任何独立RSI列；旧ML成绩不能作为“控制其他特征后RSI无增量”的证据。
- 新候选 `RSI Recovery Consensus (RRC)`：同时保留 SMA-RSI fresh/roll-out、Wilder RSI14 三日变化与 ATR 归一化价格支撑破坏。`RRC=sqrt(tanh(max(F3,0)/5)*tanh(max(W3,0)/5))*exp(-support_break_atr)`；只作交互特征，不是概率或硬发布门槛。持续强趋势的RRC=0不表示看空。
- 下一配对矩阵把旧复合专家拆成 non-RSI subtotal 与 RSI component，并比较 SMA、Wilder、fresh/rollout、RRC 及等历史长度 raw-delta control；主要看 `M3-M2 / M4-M2 / M6-M5 / M7-M6 / M9-M8`，防止把非RSI信息或更长历史归因给RSI。
- 本轮沙箱 Python/container/visible-python 启动仍返回 `ClientError`，所以 `new pytest/HGB/MLP/TCN = not_run`、H504实股fit=0；没有把上一轮本地 `15 passed` 或练习卡重算冒充本轮执行。
- 当前主分支从上一实质源码节点之后仍只有审计文档与 `AUDIT_STATUS.md` 变化；open PR=0。当前 `AUDIT_STATUS` 为 `PASS / 629 checks / 0 problems / drift 0`，仅代表报告一致性，不认证H504模型。

### 本地执行优先级

1. **WP-A1**：冻结HEAD/dirty、读取真实实验台账和剩余预算，盘点更早授权行情，生成 `fold_support.json`；仅887 sessions时正式H504 OOS继续 `BLOCKED_DATA/AWAITING_EVIDENCE`。
2. **WP-A2**：先做显式 FeatureSpec 白名单；`known_at/deadline/label_end/outcome/execution` 及未知新增列不能默认进X，空feature group不得解释为“全部列”。
3. **WP-A3**：生成 `cards100_rsi_attribution.*`，逐卡拆 `score_non_rsi / score_rsi_component / score_total`，报告 AUC、pairwise activity、rank-flip、zero share；必须复现旧专家0/100发布。
4. **WP-A4/A5**：真实完整历史计算 SMA14、Wilder14、fresh3、rollout3、support_break_atr、RRC；输出 `rollout_only / sma_wilder_split / fresh_consensus / supported_recover` 的year/KDJ/position/ATR/liquidity分层。
5. **WP-A6**：只有存在合法H504开发折才跑表格配对；固定candidate/label/split/policy，优先 `M2→M3`、`M2→M4`、`M5→M6`、`M6→M7`、`M8→M9`。
6. **WP-A7**：只有表格模型在多个开发块显示一致方向才跑MLP/TCN RSI增量；不同时扩网络容量。
7. **WP-A8**：从开发错误切片只选一个机制做一次paired retrain；无增益记 `COMPLETE_NEGATIVE`，保留全部失败实验与精确resume队列。

---

## 上一份独立复核：RSI二值专家0/100经离线重算坐实

- 完整报告：[`2026-09-20_07-26-54_JST.md`](./2026-09-20_07-26-54_JST.md)
- `publication_kind`：`INDEPENDENT_RECHECK`
- `audit_time_jst`：`2026-09-20T07:26:54+09:00`
- `reviewed_source_sha`：`8cadbd2a0210b2e2cfa475fb4a60ef46f3ed7155`
- 报告发布提交：[`4d87d080299c4bc8b1152cc2d948cc98a5172950`](https://github.com/fy-god/pro-web-60d-strategy/commit/4d87d080299c4bc8b1152cc2d948cc98a5172950)
- 实际记录：仓库真实实现重算100张练习卡，`predicted_yes_count=0`；score min/mean/max=`0.0354/0.2095/0.4926`；只有3/100张 RSI14≤45，0/100≤25；阈值0.50仍0次触发，0.49才1次。
- 该轮本地记录 `python -m pytest tests/ -q -p no:cacheprovider` → **15 passed**；这是该轮证据，不是本轮重新执行。
- 四条开放项仍在：`EML-P1-RSI-META-LEAK`、`EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`、`EML-P2-LABEL-NOT-H504-CLOSE`、`EML-P2-PANEL-WRITE-SIDE-EFFECT`。

## 上一份完整报告：RSI连续信息融合与本地研究队列

- 报告：[`2026-09-20_06-02-02_JST.md`](./2026-09-20_06-02-02_JST.md)
- `publication_kind`：`AUDIT_AND_RESEARCH_QUEUE_UPDATE`
- `reviewed_source_sha`：`efb6e1a7718a5d540107db9c1f1557994f94f5e8`
- 报告发布提交：[`240e9d8258431d205a6651ba443bc687915f63af`](https://github.com/fy-god/pro-web-60d-strategy/commit/240e9d8258431d205a6651ba443bc687915f63af)
- 该轮提出 `RSI-CONT-02`：比较 RSI 水位、变化、fresh/new、roll-out、价格支撑破坏及ATR归一化，而不是“RSI<30”硬门槛。

## 更早RSI研究链

- 独立复核：[`2026-09-20_03-41-46_JST.md`](./2026-09-20_03-41-46_JST.md)，`reviewed_source_sha=5da1758e81d74f0dab42c7cdb21861e2caea4990`，发布提交 [`b18e081e8183378e465ca752a5e6a81b7d91710d`](https://github.com/fy-god/pro-web-60d-strategy/commit/b18e081e8183378e465ca752a5e6a81b7d91710d)。该轮确认 RSI 滚出反例并指出 `N+E=ΔRSI` 是构造恒等式，不是预测证据。
- RSI候选研究：[`2026-09-20_03-06-03_JST.md`](./2026-09-20_03-06-03_JST.md)，`reviewed_source_sha=ed8b6313cba278442eade24508a707e95f629c92`，发布提交 [`2ffd9a955c786452dcd0bb09f08efcfa671f55cd`](https://github.com/fy-god/pro-web-60d-strategy/commit/2ffd9a955c786452dcd0bb09f08efcfa671f55cd)。其中候选软件测试和TOY训练不属于H504市场成绩。

## 主研究执行方案：贯通研究批次 v2

- 任务书：[`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)
- `publication_kind`：`EXECUTION_PLAN_UPDATE`
- 任务书发布提交：[`5c1e5c5a5444b94aecfd03759638412faa94c5c1`](https://github.com/fy-god/pro-web-60d-strategy/commit/5c1e5c5a5444b94aecfd03759638412faa94c5c1)
- 主批次：真实数据与协议 → 因子实现/调试 → M1—M3及单项对照 → M4快照MLP/M5因果TCN → 消融 → 错误驱动配对再训练 → OOF/meta/CR → 校准/发布账本。
- 同一报告已经处理不等于研究完成；registry中仍有READY/INTERRUPTED、checkpoint、待消融或待错误切片时必须续跑。

## 最近一次完整源码审计＋研究推进（历史指针）

- [`2026-09-20_02-00-47_JST.md`](./2026-09-20_02-00-47_JST.md)
- `reviewed_source_sha=32155ecae1a0a0be1877b780df0da12354c347ea`
- 报告发布提交：[`8dafee50ef084cf7398373b62790888e5b6faeaa`](https://github.com/fy-god/pro-web-60d-strategy/commit/8dafee50ef084cf7398373b62790888e5b6faeaa)

## 更早本对话报告

- [`2026-09-19_22-04-07_JST.md`](./2026-09-19_22-04-07_JST.md)，`reviewed_source_sha=82aefeb583ac6f039cc67ae2582c30803fc7cb32`。
- [`2026-09-19_18-00-42_JST.md`](./2026-09-19_18-00-42_JST.md)，`reviewed_source_sha=318fb47db474195176d101d32dad82bcea11d4e9`。
- [`2026-09-19_04-05-29_JST.md`](./2026-09-19_04-05-29_JST.md)，`reviewed_source_sha=0df81c65a5a2765027d6447c3cf24e4760e0c5e8`。
- [`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)，`reviewed_source_sha=14a2e834985248029f23750b80782c9fa5b36f12`。

### 继续开放、但不在本索引重复展开的核心项

- H504 主任务仍需 `Close>4E`、独立 market-session、next-session no-entry、不延期复牌；旧 `low504` High/个股bar结果不能替代。
- `label_end/known_at` 必须贯穿 fit/imputer/scaler/selection/OOF/meta/calibration。
- publication 必须先冻结 signal，再 join outcome/execution；unknown/no-entry 不得事后删信号或补位。
- `EML-P1-RSI-META-LEAK`：旧 ML 特征选择是黑名单式；新增时间合同列和RSI研究列之前必须用显式 FeatureSpec。
- `EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`：远端 `scripts/fixup_prompt.txt` 仍是“新报告→修P0/P1→同报告即退出”的旧合同；研究任务书已发布不代表用户本机执行器已接入队列。
- 887 market sessions 不足以形成先成熟训练、再成熟 H504 时间外开发的完整随访折；本地若无更早授权历史，正式 H504 OOS 标 `BLOCKED_DATA/AWAITING_EVIDENCE`。

> 本索引严格区分：审计源码 SHA、文档发布 commit、本地／沙箱软件测试、真实市场 fit 与最终认证。docs 提交不代表模型升级；cards_100、H10、合成数据或 in-sample 结果都不能冒充 H504/Close/Low 正式成绩。