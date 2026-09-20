# 专家／ML最新研究与审计索引

## 最新独立审计：low504 在真实停牌面板上窗口错位

- 完整报告：[`2026-09-21_03-50-40_JST.md`](./2026-09-21_03-50-40_JST.md)。
- 类型：`INDEPENDENT_REGRESSION_AND_REAL_MARKET_DEFECT_QUANTIFICATION`；不是新的实股拟合成绩。
- 时间：`2026-09-21T03:50:40+09:00`。
- 被审默认分支：`59788d8a1ba17d3ba3c3f6098758b66f784c63ab`；本轮范围 `c0002b0..59788d8` 只有 `docs/` 变化（`.py`/`.ps1`/`.yml`/`.toml` 零改动）。
- 主要新结论（真实 A 股面板：2,677,525 行 / 3,193 codes / 886 sessions）：
  - `src/labels.py:124-128,161,196` 的入场与视界都在「行空间」，任务定义在「session 空间」，只有同股票守卫、没有相邻交易日守卫。
  - `REGIMES["low504"]`（H=504）有 **12.2237%** 成熟行实际跨度 > 504 session（最长 590）；`low60` 有 **2.0631%**（最长 108）。
  - 真实复牌案例 002656：信号行 2023-04-28 的 `entry_open` = 40 个 session 之后（2023-06-30）的复牌开盘价，不是 next market session open。
  - `dedupe_signals`（`labels.py:233`）的冷却时钟取自**信号帧自身**的日期唯一值，稀疏帧下实测 **24→3**（按真实交易日应为 15），方向是**过度抑制**；`tests/test_engine.py:228-232` 明文承认并靠 `:243-248` 的填充股票掩盖。
  - `META_COLUMNS`（`walkforward.py:58-61`）是默认放行黑名单，不含 `label_joint`/`future_bars`/`forward_*`/`entry_open__*`；今日矩阵未写入故非活跃泄漏，属结构性陷阱。
- **否决性结论**：同批 `02-07-54` §2.3 的「887 session、H=504 → 0 个合法成熟折」**算术为真**（我独立复出，并补出闭式最小 N = 2H+2 = 1010，合法折数 = N−2H−1），但其「本仓库数据不足」的**解释不成立**：该模块从未合入产品树，产品实际矩阵是 `horizon=10`（`matrix_h10_t30_s1_meta.json`，887 sessions），且本仓库 `low504` 的 **95.81%** 标签是 timeout（真实面板重算，非引用陈旧工件），故兄弟仓库的「计划终点 → 实际可知时间」修法在此**不可迁移**，照搬会剔除 95.81% 样本、造成删失偏差。
- 更正上轮我自己的一处错误：`EML-P2-TEST-KDJ-NESTED` 不是「嵌套不执行」，而是 `def` 行丢失、KDJ 断言**活在** `test_wilson_upper_bound_is_not_a_constant` 内部执行（AST：15 个模块级 `test_*`；`-s` 实跑同时打印两条 ok）。
- 未修项：`EML-P0-AUDIT-FETCH-FAIL-PASS` 仍 OPEN，并给出精确语义 —— `note` 被显示（`:141`/`:159`）但**不参与** `verdict`（`:108`）与 `needs_attention`（`:344`），故 `git fetch` 失败时仍判 `PASS` 且不触发 attention。
- 边界：本轮**无新模型拟合**，`real_market_fit_count = 0`；peer 候选包 zip/patch SHA-256 与 benchmark 数字**未复现**（文件不在仓库）；冻结树 `pytest -o addopts="" -p no:cacheprovider -q tests/` = **15 passed**。
- 三项分离：程序修复 0；任务定义变更 0；真实模型增益 0。

## 最新候选实现：H504合同／FeatureSpec／fold-support／VIR已在沙箱落成

- 完整报告：[`2026-09-21_02-07-54_JST.md`](./2026-09-21_02-07-54_JST.md)。
- 类型：`CANDIDATE_IMPLEMENTATION_AND_EXECUTION_PLAN_UPDATE`；不是新的实股H504训练成绩。
- 时间：`2026-09-21T02:07:54+09:00`。
- 被审默认分支：`8b15edeea6118108cc08c31f323c9f6d70c6116f`；tree：`cabb75793be0a98dd249d16330f02320dc56eb57`。
- 报告提交：[`ceaa994ccc724460bc5052a06e76c6335b8fc033`](https://github.com/fy-god/pro-web-60d-strategy/commit/ceaa994ccc724460bc5052a06e76c6335b8fc033)。
- 报告blob：`12ed2db220e4588a1a5cfa0717d376e1da9ec6b9`，已按返回commit回读。
- 当前源码相对`c0002b0e...`仍只有审计文档变化；Open PR=0；产品树仍没有`src/ml/research_h504/`。
- 本轮当前隔离沙箱实际实现候选：独立市场日H504标签oracle、显式FeatureSpec白名单、成熟train→dev `fold_support`、VIR及price-only控制、train-only family ECDF/MEB。候选zip SHA256=`84fb4f97ee2efbf54f06c27316bad8dda19750929e1fe3fbd815544d732b53c7`，统一patch SHA256=`5d9110bac835a69c4322193996710ceb2469a498eb904999487d393e5f782022`；未写入远端产品源码。
- 沙箱真实执行：16项候选单测通过；162,000行synthetic VIR吞吐与6次synthetic HGB接口fit/reload完成。全部明确为软件/合成验证，`real_market_fit_count=0`。
- `fold_support`机器测试确认：887 market sessions、H=504时成熟train→更晚成熟dev split为0；1200-session合成日历可形成合法split。该结论用于阻止在当前887日上随机切分冒充H504 OOS。
- VIR实现新增严格逐step market-session连续性检查，避免“重复一个session+跳过一个session”仍通过端点跨度检查；并保留`vir_novol`用于价格-only归因控制。
- 用户本机runtime仍`LOCAL_APPLY_PENDING`，单次三小时`NOT_RUN`。当前远端runner仍`timeout=5400`，注册模板仍`PT2H30M`；没有本机start/execution receipt前不能说已接入或已跑三小时。

## 最新人工执行合同：单次连续三小时 v5

- 完整任务书：[`2026-09-21_01-43-18_JST.md`](./2026-09-21_01-43-18_JST.md)。
- 类型：`EXECUTION_PLAN_UPDATE`，不是新的全仓源码审计或市场训练成绩。
- 时间：`2026-09-21T01:43:18+09:00`。
- 固定核验源码：`c0002b0e5499de22f000500f27861d3a4f2f5336`；tree：`eb95dfc048d83f549c64103dbe95f6dc1d395449`。
- 报告提交：[`33c8d427c73d296e43c1fbb44144dc3da5961ebe`](https://github.com/fy-god/pro-web-60d-strategy/commit/33c8d427c73d296e43c1fbb44144dc3da5961ebe)。
- 报告blob：`3fb6cf5a3226a45496e3e3ee910bbe0d4b75c791`；已按返回提交回读核验。
- 研究队列：`EML-EXP-KDJ-PATH-001-REAL / LOCAL-3H-01`。

### 以本条替代旧60—75分钟和分三次累计的安排

用户要求一次连续三小时，不是三次各一小时。单次有效研究目标10800秒；同次正常总wall上限12600秒；runner硬超时13200秒；现有Windows本项目任务执行上限建议13800秒／`PT3H50M`。四小时触发间隔与时刻不变，不新增任务。

当前固定源码的runner仍为5400秒，PS1注册模板和跟踪XML仍为`PT2H30M`。这两个上限都需要用户授权的本地执行者一次性接入；模板不证明实际注册值。必须回读本机任务，并确认Triggers、Actions、Principals及其他设置不变，不执行删除重建任务的旧整套注册脚本。修改文件不会延长旧的已启动父进程。

旧48次累计fit上限及已耗次数保留。旧180分钟累计wall停止条件由本次单次210分钟wall上限替代，历史耗时保留但不计入本次三小时。预算迁移需落盘，不能又被旧75分钟条件截断。

三小时工作计划：约30分钟真实数据／全量因子与合同，约120分钟真实训练／预训练／消融，约30分钟误差分析、单项修改与验证。主线与候补有六组HGB、六组MLP、四组TCN、六项消融、第二合法块六组及两次配对重训，共30个fit槽位；不是要求硬跑完30次，全部扣旧48余额。H504无合法折时做明确独立的真实历史AUX表征与因子诊断，不伪造H504成绩。

同一启动内一个任务完成就继续下一READY；同报告已读过不能直接退出。不得sleep、同hash重复、故意拖慢或关闭合理早停凑时间。目标未达要报告原因；有合法READY却提前停，记`EARLY_STOP_WITH_READY_WORK`。有效时长不计多核CPU秒、思考、Markdown、Git和无进展等待。

### 四项状态分别验收

- 云端自动任务prompt：已更新为三小时v5；后续轮次不再管理排程。
- GitHub完整任务书：已发布并回读；本索引只更新文档指针。
- 用户本机运行时／prompt接入：`LOCAL_APPLY_PENDING`，未由本对话修改或启动。
- 用户本机单次三小时：`NOT_RUN`，不能把指令当成绩。

本次候选runner补丁10项软件测试通过，包含源blob、CLI只读查询、mock参数及临时目录git apply；没有运行真实DSH/Windows注册/三小时/实股训练。它不是完整调度器或安全整改。代码包通过本对话附件交付，下一轮应读取本机生效配置、start_receipt、原始训练日志、完整预测、模型hash及execution_receipt。

## 最近一次独立复核：保持原指针

- 完整报告：[`2026-09-20_23-50-06_JST.md`](./2026-09-20_23-50-06_JST.md)。
- 类型：`INDEPENDENT_REGRESSION_AND_NEW_REPORT_VERIFICATION`。
- 被审源码：`91726c9f14edf6047e531a53e71df359fb1ffd60`；tree：`56945a5f28b390613b850200c0cfc98f35a7f69d`。
- 该复核中的真实测试、实股计数、同期报告取证、KDJ测试命名纠正、cooldown计数争议、fetch失败仍PASS以及其他开放项均属于该次复核。本次只调整执行合同，不重认证这些成绩，不将任何开放源码项因文档提交标为已修。
- 更新前完整索引逐字保存在[固定提交的LATEST.md](https://github.com/fy-god/pro-web-60d-strategy/blob/c0002b0e5499de22f000500f27861d3a4f2f5336/docs/audits/expert-ml/LATEST.md)，Git blob `9176aba08f6cbc57cc5648cb0cd62fec2d6a0b7f`。其中该独立复核的完整长摘要、r2追加及历史链接均可追溯，没有修改任何原报告。

## 已被本次时间合同替代的执行计划（归档，不重新生效）

- [原一小时任务书 LOCAL-60M-01](./2026-09-20_22-10-00_JST.md)，发布提交`7989703ae286cc006e8f2b0f7d9accf88ee21f1f`。其因子／接口任务可继续；3600秒目标、4500秒切片及与本次冲突的时长条件已被v5替代，不再用来安排本地一小时收工。
- [VIR量价冲击恢复方案](./2026-09-20_22-00-19_JST.md)，发布提交`5114bbc925ca32acd838fb972b9429f41098b69a`。研究假设继续，旧60—75分钟安排不再生效。
- [贯通研究批次v2](./2026-09-20_02-04-16_JST.md)，保留研究定义和旧fit消耗记录；冲突时间规则以最新人工三小时合同为准。

## 主研究与此前审计（保留入口）

- [独立回归与新报告核查](./2026-09-20_19-47-00_JST.md)。
- [MEB机制家族融合](./2026-09-20_18-03-00_JST.md)。
- [独立回归与实股影响核查](./2026-09-20_15-34-32_JST.md)。
- [H504合同及测试审计](./2026-09-20_13-57-11_JST.md)。
- [RSI归因与恢复共识](./2026-09-20_09-58-00_JST.md)。
- [RSI连续信息研究](./2026-09-20_06-02-02_JST.md)。
- [RSI新增／滚出分解](./2026-09-20_03-06-03_JST.md)。

> 最新候选实现、最新人工执行合同、最近成功独立审计、远端文档发布、本地接入、真实研究结果分别记录。更长的超时只提供运行空间，不证明已经运行或提升模型。保留完整日志和候选/数据/代码指纹才能验收。
