# 专家 / ML 最新轮审

## 最新审计报告：对 03-06-03 RSI 分解报告的独立复核

- 完整报告：[`2026-09-20_03-41-46_JST.md`](./2026-09-20_03-41-46_JST.md)
- `publication_kind`：`CURRENT_EXPERT_ML_AUDIT`。这是**独立复核报告**，不替代下方专项研究，也不重复既有未修项。
- `audit_time_jst`：`2026-09-20T03:41:46+09:00`
- `reviewed_source_sha`：`5da1758e81d74f0dab42c7cdb21861e2caea4990`
- `reviewed_tree_sha`：`a206b8a7cf57e3f485d7b07b8509c045975310fc`
- `audit_base_sha`：`32155ecae1a0a0be1877b780df0da12354c347ea`
- 报告发布提交：[`b18e081e8183378e465ca752a5e6a81b7d91710d`](https://github.com/fy-god/pro-web-60d-strategy/commit/b18e081e8183378e465ca752a5e6a81b7d91710d)
- 报告 Git blob：`7d216fde893399224fd1714648b18ace05067a30`。已按 `ls-remote` 回读核验本地与 `origin/main` 一致，本次 diff 仅落在 `docs/audits/expert-ml/` 白名单内。
- 本轮实际运行：`git merge --ff-only origin/main`（exit 0）；`python -m pytest tests/ -q -p no:cacheprovider` → **15 passed, exit 0**；两份独立数学复算脚本 exit 0；开放 PR = 0。
- **源码层自 `32155eca` 起无任何变更**（6 个提交全为 `docs/`），故不重复展开既有未修项。
- 独立复算**确认**：03-06-03 的反例数值精确吻合（13.207547→51.851852，N=−1.058869，E=+39.703173）；`RSI=50[1+(C_t−C_(t−14))/Σ|d|]` 成立；H504 时间可行性算术成立（最早开发起点 564 > 最后可完整评价起点 382 → **不存在合法成熟时间外折**）。
- 新增发现 `EML-P2-RSI-REPORT-VACUOUS-IDENTITY`：该报告的"24,250 次转移满足 ΔRSI=N+E"是**望远镜式重言式**，对任意 F 恒成立，**不可能失败、零鉴别力**，不应计入已验证性质（报告已自认其为算术精度，故不算夸大）。
- 新增发现 `EML-P2-REPORT-NONEXISTENT-ARTIFACT`：报告 L187 称"现有 `research_h504` 适配器"、L229 称"已有 `experiment_registry`"，实测该 SHA 下两者均为 **0 个路径**，且与其自身 L183 矛盾。
- 独立加重 `EML-P1-RSI-META-LEAK`：`META_COLUMNS` 仅 9 名（`walkforward.py:58`），`feature_columns` 为黑名单式（`:108`），空分组直接放行全部列（`:300`），且 `final_holdout.py:222`、`concentration.py:56`、`validate_rf.py:72`、`profile_stages.py:28` 均绕过分组过滤。新增 `known_at`/`deadline` 将**静默成为模型输入**。
- **未复现并降级**："朴素相减会产生负微小量"（03-06-03 第 3 节）在真实与 1e14~1e17 对抗输入下**均未复现越界**；改动需比值 ≳1e12 而真实约 1e3，余量约 9 个数量级 → 改标 `待验证风险`，不列 `已确认错误`。
- 另确认 `EML-P2-LABEL-NOT-H504-CLOSE`（`labels.py:62/165/182/199` 为个股 bar + High 口径，从不比较 `close`）与 `EML-P2-PANEL-WRITE-SIDE-EFFECT`（`data_pipeline.py:114-118` 读函数内嵌写盘）。
- **剔除一条子 agent 误判**："报告称已更新 LATEST 但该提交未更新"不成立——审计与索引分两提交发布是本仓既定惯例，`5da1758` 已更新。
- 状态三轴：`execution_status=COMPLETED`、`research_verdict=INCONCLUSIVE`、`evidence_status=VERIFIED`（数学/引用部分）、`evidence_type=SYNTHETIC`。**本轮实股 fit = 0，没有新增实股结果。**

## 最新专项研究：RSI有效恢复与本地检验

- 完整报告：[`2026-09-20_03-06-03_JST.md`](./2026-09-20_03-06-03_JST.md)
- `publication_kind`：`FOCUSED_FACTOR_RESEARCH_AND_SOFTWARE_TESTS`。这是RSI专项源码核验、因子实现、软件测试和研究任务，不替代下方最近一次完整源码审计记录。
- `audit_time_jst`：`2026-09-20T03:06:03+09:00`
- `reviewed_source_sha`：`ed8b6313cba278442eade24508a707e95f629c92`
- `reviewed_tree_sha`：`c859da7eb6a0e9949db61158f8a38a8308ef0ed0`
- 报告发布提交：[`2ffd9a955c786452dcd0bb09f08efcfa671f55cd`](https://github.com/fy-god/pro-web-60d-strategy/commit/2ffd9a955c786452dcd0bb09f08efcfa671f55cd)
- 报告blob：`670b2979fd885f25703e4e47545708b827a6b22b`，已按提交回读，和本地完整报告Git blob一致。
- 子实验：`EML-EXP-KDJ-PATH-001-REAL/RSI-RER-01`，接续X17/X18和现有研究预算。
- 本轮确认：专家公共RSI函数已有零损失/全平边界处理；当前82列ML矩阵没有独立RSI列。不能把原模型的上涨填0错误套进本项目，也不能把复合RSI专家成绩当独立RSI增量。
- 新机制：SMA-RSI变化分解为新增价差贡献N和旧价差滚出贡献E，满足ΔRSI=N+E。实际合成反例中当天价格仍下跌，RSI从13.21升到51.85；新贡献为负，升幅来自旧下跌滚出。它不是RSI公式bug。
- 候选RER：正向新增恢复×历史低点承接；保留原始分量，只作连续特征，不当概率或硬发布门槛。持续上涨RER=0不表示看空，不过滤RSI>70。
- 实际测试：上传参考18/18重跑；本轮44项候选pytest；24,250次分解恒等式检验；6组HGB及2组MLP完成合成接口fit/保存/reload/全候选预测。所有训练是TOY随机目标，实股fit=0，不称H504成绩。
- 集成风险`EML-P1-RSI-META-LEAK`：新增known_at/deadline后不能使用现有“排除META后全部入X”的黑名单；新因子和训练原型采用显式白名单。远端源码未修改。
- 本地顺序：时间可行性→因子/日历→真实滚出频率→白名单及归因→A—F表格模型→MLP D/F和开发错误配对修改→独立校准/ledger→台账交接。G/H同历史原始价差是严格控制；最多24fit从旧48fit/180分钟余额扣除，不新开预算或排程。
- 下一轮读取：fold_support、factor_health、rolloff_diagnostics、实验台账、全候选预测、训练日志、checkpoint及配对差值。任务书已发布不等于用户本机agent已启动。

### 重要纠正：887日不等于能做成熟H504时间外开发

`EML-P1R-H504-TEMPORAL-SUPPORT`的旧算术需要更严格解释。887-504=383只是在现有数据末端看，有完整未来窗的历史起点数；它不保证存在“标签先成熟的训练集→更晚且本身也完整成熟的开发集”。

在0..886市场日索引、60日预热、训练标签严格早于开发开始的保守合同下：最早训练起点59、期限终点563，最早开发起点564；最后可完整评价的开发起点却是382。没有交集。即使只要求一行训练和一行开发，下界也至少1,069市场日，实际有意义的训练/校准/测试还需要更多。禁止在383起点中随机分割或放宽标签凑H504时间外成绩。

本地可能已有更早授权行情，须实际盘点。仅有该历史时仍可做因子健康/滚出频率、候选实现、截至当前成熟队列的拟合与前瞻未知打分；不把这些冒充成熟时间外验证。以下历史审计中的“383/324个成熟起点”应按本纠正解释。

## 最新主研究执行方案：贯通研究批次 v2

- 完整任务书：[`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)
- `publication_kind`：`EXECUTION_PLAN_UPDATE`，不是一次新的全仓模型审计或市场训练结果。
- `audit_time_jst`：`2026-09-20T02:04:16+09:00`
- 本次执行链核验源码：`32155ecae1a0a0be1877b780df0da12354c347ea`
- 任务书发布提交：[`5c1e5c5a5444b94aecfd03759638412faa94c5c1`](https://github.com/fy-god/pro-web-60d-strategy/commit/5c1e5c5a5444b94aecfd03759638412faa94c5c1)
- 文件 blob：`9935f12f8285f808a00cebdc0f8707b1491ff17d`。
- 首批研究 ID：`EML-EXP-KDJ-PATH-001-REAL`；接续 `X17-KDJ-PRESSURE-PATH` / `X18-H504-CR-KDJ-PATH`，SEQ 与 CR 使用子实验。
- 新工作终点：真实数据与协议 → 因子实现/调试 → M1—M3及单项对照 → M4快照MLP / M5因果TCN → 必要消融 → 一次有依据的错误驱动再训练 → OOF/meta/CR → 独立校准/发布账本/可复算指标。
- 相同报告已经处理不等于研究结束：registry 中仍有 `READY/INTERRUPTED`、可恢复 checkpoint、待消融或待错误切片时继续推进；只有没有新报告、没有未完成队列、没有新数据/环境变化时才 `NO_NEW_WORK`。
- 单次本地研究上限建议 75 分钟，整批累计 180 分钟 / 48 次真实 fit 跨轮续算；上限不是必须耗满的目标。
- 该任务书记录的 23 项候选软件测试属于其独立沙箱执行结果，不是 H504 实股训练或正式神经网络比较；本索引不把它改写为市场成绩。

## 最近一次完整源码审计＋研究推进（保留历史）

下列“当前/本轮”指该次历史审计，不是本次RSI专项重新检查所有旧问题；H504时间支持以上方纠正为准。

- 完整报告：[`2026-09-20_02-00-47_JST.md`](./2026-09-20_02-00-47_JST.md)
- `publication_kind`：`AUDIT_AND_EXECUTION_PLAN_UPDATE`
- `audit_time_jst`：`2026-09-20T02:00:47+09:00`
- `reviewed_source_sha`：`32155ecae1a0a0be1877b780df0da12354c347ea`
- `reviewed_tree_sha`：`fba9afc0b6083b1099850e60280ffee0d4e2aefc`
- 上一份成功源码审计：`82aefeb583ac6f039cc67ae2582c30803fc7cb32`
- 报告发布提交：[`8dafee50ef084cf7398373b62790888e5b6faeaa`](https://github.com/fy-god/pro-web-60d-strategy/commit/8dafee50ef084cf7398373b62790888e5b6faeaa)
- 报告文件 Git blob：`4143fae7c47dc915ef9b58f0a93b3a2f40896f26`；已按发布提交回读核验。
- 当时 open PR：0。
- 该轮没有市场模型重训、远程训练、交易或收益验证；审计文档提交不代表模型升级。

### 该轮新增确认

- `EML-P0-AUDIT-FETCH-FAIL-PASS`【P0】：当时已发布 `reports/AUDIT_STATUS.md` 实际同时记录 `PASS / 629 checks / 0 problems` 与 `git fetch failed (exit 1): incorrect old value provided`。`scheduled_report_audit.py` 把 fetch 失败折叠成空 `changed` 列表与文本 note，顶层 PASS 只看 checker exit 和 unstable，因此同步失败仍可认证 stale local tree。修复要求 frozen `AUDITED_SHA`、同步失败直接 `SYNC_FAILED`，远端变化则 `STALE`，不得 PASS。
- `EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`【P1】：当时 `scripts/fixup_prompt.txt` 仍以“最新报告→只修 P0/P1→同报告已处理则 `NO_NEW_REPORT`”为唯一工作合同，不读取 experiment registry、checkpoint、待消融预测或未完成训练队列；这是本地 agent 工作量过小的直接控制面原因。
- `EML-P1R-H504-TEMPORAL-SUPPORT`【研究约束，已深化纠正】：当时dense H10元数据887日、历史成熟起点383/324的计算不能证明时间外折可行，详见本索引顶部和RSI专项第五节；必须执行逐行fold_support，不缩短horizon或偷看标签。

### 该轮审计沙箱状态

- GitHub 源码与机器结果读取、报告写入和索引更新成功。
- 该轮container/Python执行工具在启动层返回ClientError，因此没有执行smoke/pytest/HGB/MLP/TCN。不是对所有后续轮次环境状态的永久判断。
- 该限制不证明用户本机缺数据或缺PyTorch。真实训练应由本地执行器读取授权数据路径后登记到experiment_registry.jsonl。

## 主批次研究矩阵（须先通过更严格时间可行性）

`EML-EXP-KDJ-PATH-001-REAL` 在第一个真实合法H504开发折、seed17的起始队列：

1. `M0`：自然基率常数，不计 fit。
2. `M1`：KDJ + 长期位置 Logistic。
3. `M2`：纠错后的 snapshot HGB。
4. `M2P`：M2 + repaired pressure only。
5. `M2K`：M2 + KDJ-path only。
6. `M3`：M2 + KDJ-path + pressure HGB。
7. `M4`：snapshot MLP `64→32→1`。
8. `M5`：128-market-session causal TCN + 同 snapshot branch；width32、kernel3、6个双卷积残差块、dilation1/2/4/8/16/32，理论receptive field253sessions。

支持、预算和错误分析允许时再扩folds和seed17/29/43。保留2—4fits给错误驱动配对再训练；48fits是整批累计上限，不是48configs×3seeds×3folds。本次RSI子任务共享余额，不要求所有矩阵从头重训。

## 历史开放模型／评估问题

以下状态来自02:00完整审计，本次RSI专项没有重新验收全部旧问题。后继应按当前源码和实际回归判定。

- `EML-P0-H504-HIGH-CLOSE`：旧low504仍按未来High严格超过4E，不是主目标Close>4E；本次RSI专项也重新确认该入口差异。
- `EML-P0-SESSION-ALIGN`：entry与horizon按个股bar，而非独立市场日；本次也重新确认该入口差异。
- `EML-P0-YEAR-KNOWN-AT`：年度训练／历史阈值评分缺逐行label_end/known_at。
- `EML-P0-KNOWN-AT-GAP`：holdout的market-session purge与实际个股-bar标签时钟不一致。
- `EML-P0-ML-COHORT`：cross-sectional评分前按未来标签完整性删test row。
- `EML-P0-LEDGER-ORDER`：score_signals先删unresolved再dedupe。
- `EML-P0-COOLDOWN-GRID`：cooldown时钟从signal dates重建。
- `EML-P1-DOWNVOL-EMPTY`：五日down/up互斥分组各min_periods=3，旧比值无法产生有效混合窗口。
- `EML-P1-ZERO-SIGNAL-BASE`：summarise删除0信号fold后再算自然基率。
- `EML-P1-RULE-SHAPE`：深回踩和大gap因clip获得与温和结构相同满分。
- `EML-P1-FRONTIER-TIES`：同分组内部prefix被当作scalar-threshold点。
- `EML-P0-FIXUP-SYNC-FAILOPEN`：fixup fetch/rebase失败仍可启动agent。
- `EML-P0-AUDIT-STALE-ATTEST`：checker PASS尚未与最终发布树原子绑定。
- `EML-P0-AUDIT-FETCH-FAIL-PASS`：同步失败仍可顶层PASS。

旧审计已修控制保留：strict target比较器一致、scan/baseline selection mask共用、Close标签raw float64 entry边界修复；不因新文档提交改变这些问题状态。

## 历史归档结果边界

- H10/+30%/High RF开发walk-forward：4765/22867=20.8379%，pooled base4.089445%，4/4folds above base。此处只是历史索引，不是本次实股重训。
- dense H10矩阵元数据：2,680,715rows、3,193stocks、887sessions、82features；High base3.08934%，Close base2.02919%。
- 旧low504归档bull rate约4.21%来自High和个股bar任务，不能当新H504/Close/market-session自然基率。
- 真正H504/Close/Low联合目标尚无本轮可认证的TP/发布分母、自然基率、event Recall、unknown/no-entry、校准或cluster-aware interval。

## 上一份完整源码审计

- [`2026-09-19_22-04-07_JST.md`](./2026-09-19_22-04-07_JST.md)
- `reviewed_source_sha=82aefeb583ac6f039cc67ae2582c30803fc7cb32`
- 报告发布提交：[`3dbaa67e00b3bdbaff8828b6d3ce6b68b73ffa31`](https://github.com/fy-god/pro-web-60d-strategy/commit/3dbaa67e00b3bdbaff8828b6d3ce6b68b73ffa31)

## 更早本对话报告

- [`2026-09-19_18-00-42_JST.md`](./2026-09-19_18-00-42_JST.md)，`reviewed_source_sha=318fb47db474195176d101d32dad82bcea11d4e9`。
- [`2026-09-19_04-05-29_JST.md`](./2026-09-19_04-05-29_JST.md)，`reviewed_source_sha=0df81c65a5a2765027d6447c3cf24e4760e0c5e8`。
- [`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)，`reviewed_source_sha=14a2e834985248029f23750b80782c9fa5b36f12`。

> 区分专项因子研究、最新主执行方案、完整源码审计、文档发布commit与本地研究代码commit。公式恒等式、候选软件测试和随机目标接口训练不等于市场预测收益；RSI分解与RER仍需本地真实、合法、同条件的时间外验证。
