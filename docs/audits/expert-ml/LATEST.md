# 专家 / ML 最新轮审

## 最新增量审计：先把 H504 主合同写成会失败的测试，再继续重训练

- 完整报告：[`2026-09-20_13-57-11_JST.md`](./2026-09-20_13-57-11_JST.md)
- `publication_kind`：`AUDIT_AND_EXECUTION_PLAN_UPDATE`
- `audit_time_jst`：`2026-09-20T13:57:11+09:00`
- `reviewed_source_sha`：`1363e68b1a6419aef71d6508aa3d2dd5a6d18bf0`
- `reviewed_tree_sha`：`ab838fb9124e8f0955da88fe16ca8da2e0e59c98`
- 报告发布提交：[`0901b8c408616569f709f088ccec3bca90ed5ff5`](https://github.com/fy-god/pro-web-60d-strategy/commit/0901b8c408616569f709f088ccec3bca90ed5ff5)
- 报告 blob：`23c8aa0de766cfe4b19955c29ffd8f8e97ae9458`，已按发布提交回读核验。
- 新增确认 `EML-P1-TEST-COOLDOWN-FIXTURE-COUPLING`：当前 cooldown 边界测试明确用另一只股票的 filler signals 补齐日期网格；目标股票同样的两条信号，在“无 filler”与“有 filler”时可得到不同去重结果。底层 `EML-P0-COOLDOWN-GRID` 因而不仅缺测试，现有 fixture 还把错误耦合写进了预期语义。
- 新增确认 `EML-P1-TEST-ENTRY-ROW-MASQUERADE`：`test_entry_is_next_open_not_close` 的 `rows[1]` 同时是下一条个股记录与下一市场日，无法区分用户要求与当前 `opens[1:]` 实现；必须增加“下一市场日停牌/缺bar、之后复牌”的 no-entry RED case。
- 新增确认 `EML-P1-TEST-H504-CLOSE-CONTRACT-MISSING`：当前 labeler 和现有 target tests 都用未来 High；需要 `high>4E but close<=4E`、`close==4E`、`close>4E` 和 same-day risk-first 四个合同测试。
- 新增 `EML-P2-TEST-KDJ-NESTED-IN-WILSON`：KDJ 跨年连续性代码当前缩进在 Wilson 测试函数尾部，不是独立 pytest case；应拆开，避免 Wilson 提前失败时跳过 KDJ 合同。
- 研究执行器仍未落地：远端 `scripts/fixup_prompt.txt` 仍是“同报告即 NO_NEW_REPORT、只修 P0/P1”；从上一研究索引到当前 HEAD 只有 docs/status 三个提交。代码搜索未发现 `experiment_registry`、`fold_support`、`research_h504` 或 `FeatureSpec`；该搜索本身标 `incomplete_results=true`，因此结论仅限“远端尚无研究源码提交”，不推断用户本机未 push 状态。
- 本轮沙箱实际尝试 container clone/shell 与 Python probe，均在工具启动层 `ClientError`；因此没有把上一轮本机 `15 passed` 冒充成本轮测试，也没有新 HGB/MLP/TCN/H504 fit。
- 本地下一优先级已改成六个 RED contract tests + FeatureSpec leak test，然后修 TaskSpec/calendar/publication；并行实现 raw RSI/SMA-Wilder/fresh-rollout/RRC、真实历史 factor-health 与 `fold_support.json`。有合法 H504 dev fold 才跑 M0–M9；无合法折则保持 `BLOCKED_DATA`，继续真实因子诊断与 prospective ledger。
- 下一轮优先验收：是否出现非 docs 的研究源码 commit、RED→GREEN 日志、独立 market calendar、no-entry、Close>4E/risk-first、FeatureSpec、`cards100_rsi_attribution` raw RSI、`fold_support`、experiment registry 与完整 dev predictions。

---

## 最新独立复核：RSI 归因算术复算无误，并补上「截断」这一定性关键

- 完整报告：[`2026-09-20_11-27-10_JST.md`](./2026-09-20_11-27-10_JST.md)
- `publication_kind`：`INDEPENDENT_RECHECK`
- `audit_time_jst`：`2026-09-20T11:27:10+09:00`
- `reviewed_source_sha`：`a0ca60b4fc9dc73de0b4ff7ce6b753fc3afd1753`（被复核报告的源码点）
- `main_head_after_sync`：`5a135d3a95e2d5cc201c7a6c3dda8703fce8431d`
- 报告发布提交：`e9f7b8cf00a5fd01f25afee48fe70a3157f278cc`（已 `git ls-remote` 回读 MATCHED）
- **候选报告**：`09-58-00` 报告自报审计沙箱 Python/container 返回 `ClientError`、未跑测试。本轮在**本机**实测 `python -m pytest -o addopts="" -p no:cacheprovider -q` → **`15 passed in 4.17s`，exit 0**，与其上一轮记录一致。
- **逐项复算该报告 RSI 归因，全部精确复现**（未采信散文，用仓库自身 `ExpertCard.from_mapping` + `rsi_mean_reversion.predict`）：`rsi_oversold==0` 为 **97/100**；两边皆零的正负配对**恰为 2350/2500 = 94.0000%**（且恰好取到下界）；`0.30×mean=0.001115`、`0.30×max=0.041631`；`score min/mean/max = 0.0354/0.2095/0.4926`；`AUC(score_total)=0.5836`；`fires=0/100`。**该报告没有编造数字。**
- **本轮新增三点量化（该报告未做）**：
  1. 94.0% 是「活动率上界」而非「影响量」：RSI 项的 AUC 边际贡献**为负**——去掉它 AUC **上升** `+0.0032`（≈8/2500 配对）；总分排序力几乎全来自单一分量 `nonpanic_volume`（单独 AUC **0.5828** vs 五项合计 **0.5836**；`drawdown` 单独仅 0.4728）。
  2. Bootstrap 1000× 留一：五项 ΔAUC 的 95% CI **全部包含 0**——故「RSI 无增量」成立，但「其余四项有增量」**同样未被证明**；总分本身 z≈+1.44 亦不显著。该报告的因果口吻应降级为方向性提示。
  3. 「AUC≈0.5 ⇒ RSI 无用」**不可判定**：`rsi_mean_reversion.py:46` 的 `_clip((45.0-rsi)/20.0)` 把 `rsi14>45` 压成恰好 0，而实测 **97/100 卡 `rsi14>45`**（min 42.22/max 100.00/mean 67.38）。连续 RSI 信息在进入 AUC **之前**已被销毁 97%，数据无法区分「无信息」与「有信息但被截断遮蔽」。
- **新增覆盖缺口**：`experts.registry` 共 **36** 个策略，而 `tests/` 单文件 15 个测试中仅 1 个局部 import `experts`、只断言 **4 个**换手率代理策略——**覆盖率 4/36**，`rsi_mean_reversion` **无测试**（无任何测试断言上述截断行为）。**自我更正**：本报告初稿曾误称「零个测试 import `experts`」，实为 `test_engine.py:476-477` 确有 import，正确表述为 4/36；报告中已保留该更正记录。
- **五项开放项全部 CONFIRMED（0 证伪 / 0 已修）**：`EML-P1-RSI-META-LEAK`（潜伏，今日暴露=0：两矩阵均 91 列、9/9 META、82 特征、`known_at/deadline/label_end` 均不存在；非分组过滤调用点 10 文件 13 处；无白名单）、`EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`、`EML-P2-LABEL-NOT-H504-CLOSE`（`labels.py:62/182/193/199-201` 用 high；`close` 全文仅 1 次且在 `:11` docstring）、`EML-P2-PANEL-WRITE-SIDE-EFFECT`（潜伏，`data/panel_daily.parquet` 已存在故未触发）、`EML-P0-AUDIT-FETCH-FAIL-PASS`（**可执行证明**：fetch 失败 + audit 绿 → 仍发布 `PASS`）。
- **该报告自身诚实**：明确声明沙箱 `ClientError`、明确不冒充 `15 passed`、其 `reviewed_tree_sha: 74cda26f…` 经我核验**恰等于 `a0ca60b^{tree}`**；「8cadbd2→a0ca60b 只有两次提交」经 `git rev-list --count` 核为 **2**。
- **源码自上一实质节点未变**：`git diff --stat 8cadbd2..HEAD -- src/ experts/ tests/` **为空**，故只改 `docs/audits/expert-ml/2026-09-20_11-27-10_JST.md` 与 `LATEST.md`；`reports/AUDIT_STATUS.md` 未动。
- `AUDIT_STATUS` 当前 `PASS / 629 checks / 0 problems / drift 0`（`a0ca60b` 所改），仅代表报告一致性，**不认证 H504**。

### 本地执行优先级（沿用 `09-58-00` 的 WP-A1…WP-A8，本轮追加 WP-A3 强化）

1. **WP-A1**：冻结 HEAD/dirty、读取真实实验台账与剩余预算，生成 `fold_support.json`；仅 887 sessions 时正式 H504 OOS 继续 `BLOCKED_DATA`。
2. **WP-A2**：先做显式 FeatureSpec 白名单；`known_at/deadline/label_end/outcome/execution` 及未知新增列不得默认进 X，空 feature group 不得解释为「全部列」（对应 `EML-P1-RSI-META-LEAK`）。
3. **WP-A3（本轮强化）**：生成 `cards100_rsi_attribution.*` 时**必须**逐卡附 **`rsi14` 原值**，并报告**截断率**与 `AUC(rsi14_raw)`；仅有 `rsi_oversold` 的产物**不得**被引用为 RSI 结论（依据：97% 被 `_clip` 截断）。
4. **WP-A4/A5**：真实完整历史计算 SMA14、Wilder14、fresh3、rollout3、support_break_atr、RRC；分层输出。
5. **WP-A6**：仅在存在合法 H504 开发折时跑表格配对；优先 `M2→M3`、`M2→M4`、`M5→M6`、`M6→M7`、`M8→M9`。
6. **WP-A7**：仅当表格模型在多个开发块方向一致才跑 MLP/TCN RSI 增量。
7. **WP-A8**：从开发错误切片只选一个机制做一次 paired retrain；无增益记 `COMPLETE_NEGATIVE`。
8. **新增（本轮）**：任何分量去留以「配对 AUC 差的 95% CI 是否排除 0」为准（依据：五项 CI 全含 0）；并让 `rsi_mean_reversion` 等被漏掉的 32 个策略逐步进入 `tests/`。

---

## 上一份专项研究：RSI归因纠偏、Wilder对照与恢复共识

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
