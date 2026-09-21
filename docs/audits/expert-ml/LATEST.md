# 专家／ML最新研究与审计索引

## 最新独立审计（2026-09-21 15:48 JST）：自动修复链已死 · 候选无界增殖的契约成因

- 完整报告：[`2026-09-21_15-48-00_JST.md`](./2026-09-21_15-48-00_JST.md)。
- 类型：`INDEPENDENT_AUDIT_AND_PROVENANCE_RECONCILIATION`；不是新的实股H504成绩，`real_market_fit_count=0`。
- 时间：`2026-09-21T15:48:00+09:00`。
- 被审默认分支：`5d1b365cd6c2a80a74b18fbf12e47e766203eb93`（`HEAD == origin/main`）。自上一份专家／ML报告 `74430df` 起仅2次docs-only提交。
- **【P0·任务定义变更】本机自动修复链已死。** 实时 `schtasks /query /tn "ProWeb60d-Fixup"` → `ERROR: The system cannot find the file specified`，exit 1；全表扫描只有 `\ProWeb60d-ReportAudit` 一个 ProWeb60d 任务。即 `register_fixup_task.ps1` 是**从未被执行的注册脚本**，`run_fixup.task.xml` 是**从未被注册的模板**。`logs/fixup/last_processed.txt` 仍停在 `2026-09-19_04-05-29_JST.md`，最新fixup日志为 `2026-09-20_011545.log` 且末行 `dry run: not starting the agent`。
- **后果（本轮量化）**：自最后产品源码提交 `1dd9732`(2026-09-19 01:58:38) 起 **74 次提交 / 26 份审计报告 / 0 次 fixup**，其中触碰 `src/ experts/ tests/` 的提交为 **0**。即 **26 轮审计写下的任何 P0/P1 一条都没有被自动消费过**。这与「`PASS` 无任何机器消费者」（§4）共同构成本项目的**双重惰性**：无人对 PASS 行动，也无人对 findings 行动。
- **【P1·任务定义变更】候选无界增殖的结构性成因**：`SCHEDULE.md:20` 禁止网页审计者改代码，`fixup_prompt.txt:11` 禁止fixup agent写结论——**能写结论的不能改代码，能改代码的不能写结论，而后者还没被调度**。于是每轮唯一可交付物就是再写一份文档，`SCHEDULE.md:24,30` 又把它推向「新思路/新实验」而非落地旧产物。实测：候选代次 v1(`ceaa994`)→v2(`ffa0bd1`)→v3(`2dbd67e`)→v4(`844ea93`) 共8次提交，**仓库落地代码 0**；报告 29 份 / 734,335 B；产出/推进比 26:0。
- **【未复现·待验证风险】** `2026-09-21_14-06-49_JST.md` 的 `33 passed in 5.02s`、4个候选SHA-256、v3→v4 patch，在本仓库**无对应实体**：全部可收集测试实测仅 **15**（`pytest --collect-only` = 15；`tests/` 是唯一测试根；无 `pyproject.toml`/`pytest.ini`/`setup.cfg`）；tracked `*.zip/*.patch/*.pt/*.jsonl/*.receipt` 全为 0；`src/ml/research_h504/` 不存在；4个哈希只出现在2个 `.md` 散文中。**不指控伪造**（候选可能在审计沙箱），但一律记 `未复现`，不得当作本项目已验收证据。
- **【自我更正】** 本报告初稿把「entry/horizon 按行计数」与「cooldown 用帧秩」当作新发现，复核后确认二者**已由 `2026-09-21_03-50-40_JST.md` §1/§2 报出**（该报告与 `LATEST.md:42-43` 均有记录），故降级为**回归确认**；并更正 §3 的**方向表述**——实测净差 **−5**（帧时钟保留 21,193 / 真时钟 21,198），是**过度抑制**而非我初稿所写的过度宽松。
- **回归汇总**：FIXED 1 / STILL_OPEN 8 / NOT_REPRODUCED 1 / 描述更正 1。新增量化：entry/horizon 缺陷在**产品实际 horizon H10** 上影响 **0.3480%**（9,219/2,648,785）成熟行，H60 2.0632%，H504 12.2308%（parquet 口径，887 sessions；与既有报告 12.2237% 同向同量级，绝对数差异源于输入面板不同，故旧绝对数不应作为 parquet 现值引用）。
- **【回归确认·非缺陷】** 887 session 不足以支撑严格 H504 train→dev 时间外折的算术**成立**（564 > 382，差 182；最低需 1,069 session）。同时 887 下确有 1,108,219 行具备完整504行后续、2,930/3,193 只股票 ≥505 bars——两件事不矛盾：阻塞是**缺候选清单/实验注册表**（`research_h504`/`receipts`/`experiment_registry`/`local_start_receipt`/`execution_receipt` 全 0 路径），不是 session 数不够。
- **【provenance】** `output_86_real` 是过期目录名，实为 **3,193** 只主板股票（前缀 100.00% 落在 600/601/603/605/000/001/002/003，非主板 0）。「86」不得被读成样本量。
- **下一步最高优先**：由人类决定**注册 `scripts\register_fixup_task.ps1`，或明确宣告该链未启用**并改写 `SCHEDULE.md`/本索引中的「本机执行链」表述。否则每轮仍会产出无人消费的文档。

## 前一候选推进：三小时执行收据＋epoch级中断续跑 v4

- 完整报告：[`2026-09-21_14-06-49_JST.md`](./2026-09-21_14-06-49_JST.md)。
- 类型：`CANDIDATE_EXECUTION_RELIABILITY_AND_REGRESSION_UPDATE`；不是新的实股H504成绩。
- 时间：`2026-09-21T14:06:49+09:00`。
- 被审默认分支：`74430df12f60b6b30b06baa02111feb0d4d0bcee`；tree：`9156857ae721967ca6530bcc966bc57aa79d1047`；Open PR=0。
- 报告提交：[`844ea93ae7f459867816a81886dd5cbda785def4`](https://github.com/fy-god/pro-web-60d-strategy/commit/844ea93ae7f459867816a81886dd5cbda785def4)，报告 blob `ad07c0be5a7f90a3f82c6cb3d8283699515cc47b`，已按返回提交回读。
- 从上一索引 `f34d24c7...` 到本轮审计起点只有定时 `AUDIT_STATUS.md` 更新；没有新的产品研究源码、真实checkpoint、prediction或registry提交，`real_market_fit_count=0`。
- 本机执行链在仓库中仍未接入三小时合同：`fixup_prompt.txt` 仍只修P0/P1且同报告可直接 `NO_NEW_REPORT`；`run_fixup.py` 仍 `timeout=5400`；tracked Windows task XML仍 `PT2H30M`。这些只是仓库模板，实际本机注册值仍需receipt/只读查询证明。
- 当前 `AUDIT_STATUS.md` 仍同时写 `PASS` 与 `Remote drift = 2`；`scheduled_report_audit.py` 的 verdict依旧不看 `changed/note`，因此PASS不能替代源码同步/训练证据。
- v4修复候选v3的best-checkpoint语义错误：v3会把**最佳epoch模型**与**最后epoch optimizer**装进同一 `best.pt`；v4改为同一best epoch的model+optimizer，并单独维护 `last.pt`。
- v4从“完整fit级registry resume”推进到**单个fit的epoch级resume**：每epoch保存last、保存optimizer/early-stop/history/DataLoader generator/Torch+NumPy+Python RNG；wall budget中断返回 `INTERRUPTED_BUDGET`，compatible rerun从last继续。
- checkpoint新增训练配置hash；feature set / seed / window / batch / LR / weight decay / patience不一致时返回 `BLOCKED_CHECKPOINT_MISMATCH`，禁止静默把旧checkpoint接到新实验。
- 新增 `local_start_receipt.json / session_progress.json / execution_receipt.json`：实际phase wall、fit计数、real/synthetic training秒、target是否达到及主要产物SHA-256。配置了10800/12600/13200秒不会被冒充为已实际运行。
- v4候选测试 `33 passed in 5.02s`；6秒synthetic wall-budget探针正确得到 `INTERRUPTED_WALL_BUDGET` 与 `target_met=false`，同一训练signature随后出现 `INTERRUPTED_BUDGET -> COMPLETE_AUX` 且完成项 `resumed=true`。这些是软件/合成证据，不是A股成绩。
- candidate v4 zip SHA-256=`1aac72397ddaed1ecc51939ae3aed106a5cb49c65495d819dbf375d703eeb27f`；v3→v4 patch SHA-256=`7fa6a9ea90769c19bfb524ce81367222ebe6c254bafd08c6c470fd0cd8b0db84`；verification JSON SHA-256=`08e6cfe3b5afdc570a987f33b196b48230ba76b884210f896aef478e3273e6f7`。候选代码未写入远端产品树。
- 下一次真正的模型推进必须来自本机真实 `start receipt + REAL_MARKET/AUX_REAL_HISTORY registry + best/last checkpoint + 全量predictions + execution receipt`；在此之前停止继续造新因子名。

## 前一候选：可执行 `--stage all` H504研究流水线 v3

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