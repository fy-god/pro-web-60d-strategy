# 专家／ML线研究与审计索引

## 最新独立审计（2026-09-22 11:56 JST）：完成态复用无产物校验端到端复现，并新增守卫不对称证据

- 完整报告：[`2026-09-22_11-56-38_JST.md`](./2026-09-22_11-56-38_JST.md)。
- 被审源码 `reviewed_source_sha`: `89b722d7ab88f6a5fc5f381a14c742a1f53d44cc`；上一被审基线 `2b0232f8acb712569aeb5ce68f7291ab3fc7a5dc`。
- 该区间**产品研究源码零变化**：只有 2 个 docs 提交（`a33b9d2a…` 新增 10:12 报告、`89b722d7…` 更新索引）。因此本轮**没有**任何「已修复」结论。
- **维持 P1 `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`，并用真实入口端到端复现**：真实 `run.py --stage all` + `run_h504_hgb` 调用计数，run1 调用 1 次报 `COMPLETE_H504_DEV`；删除 `h504_T0/model.pkl` 与 `dev_predictions.csv` 后 run2 调用 **0** 次、状态 `REUSED_COMPLETE`、无 stale 标记。截断、同尺寸篡改、零字节同样命中。`registry.py:19-23` 全文 25 行无任何 path/存在性/sha256 校验。
- **本轮精确化（此前未写）**：仓库**已有**所需哈希机制 —— `receipts.py:15 sha256_file()`、`:33 hash_tree()`，并在 `:184` 写入 `execution_receipt.json`。缺陷不是「没有哈希」，而是 `latest_complete` 从不读它、`finalize()` 每轮**覆盖**该 receipt 销毁旧证据、且全仓无消费者。⇒ 最小修复是**持久化既有清单到 registry 行并 fail-closed**，比重造哈希便宜。
- **影响面收窄**：盲复用仅限 `--stage all`；`--stage h504-hgb` / `--stage aux-tcn` 不查 registry、总是重训。不降低严重度，因为 `all` 是文档化的生产调用方式。
- **新增守卫不对称（P1，此前报告只作定性描述）**：`train_h504.py:43` 是**唯一**支持度门，只查 `train.sum()`/`dev.sum()`；`resolved`（`:42`）**只被使用从未被守卫**。AST 枚举 `run_h504_hgb`(24-60) 仅 3 个 `if`（`:37/:43/:47`），`resolved` 与 `len(ydv)` 均不在任何守卫中；`:59` 仍无条件报 `COMPLETE_H504_DEV` 并写入 `n_dev_resolved`。实测 **0** 个 resolved 样本仍返回 `COMPLETE_H504_DEV`。
- **`EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE` 证据链补齐**：`run.py:94` 的 `glob('*.py')` 非递归，只覆盖 `src/ml/research_h504/` 下 **16** 个文件；该包**唯一**跨包导入在 `snapshot_features.py:78`（`from src.ml import build_matrix as bm`），`src/ml/build_matrix.py` 实为 **546** 行且又 `:44 from src import data_pipeline` ⇒ 二阶未覆盖。变异实验（ATR 窗口 14→13、**不改列名**）后 `pipeline_hash` 逐位不变、`latest_complete` 命中 ⇒ 会报 `REUSED_COMPLETE` 并跳过训练。T0 输入 **82/82 = 100%** 来自未覆盖文件。
  - **更正**：一处子 agent 报告把该导入记作 `snapshot_features.py:31`；实测 `:31` 是 `missing = req - set(panel.columns)`，正确为 **`:78`**。
- **我自己提出并已自行推翻的候选**：曾疑「签名无法区分 rich 与 minimal 特征分支」。实跑两分支列数为 **85 vs 33**，且签名载荷含 `'features'` 键（`run.py:150/173`）⇒ 列集合变化**会**改变签名，该候选**不成立**，不计入缺陷。据此把签名问题的措辞限定为「**不改列名的取值级**改动不可见」。
- **`EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED` 搜索路径已明确**：`fits_*` 全仓 12 处**全部**是写入或输出，**0 处**与上限比较；`global_fits|cumulative|total_fits` **0 命中**；`ledger` 全仓 29 处逐条核对**全部无关**（报告级/lowzone/tradeability/候选台账）。唯一强制比较是 `run.py:170` 的**单进程** `--max-aux-fits`（默认 6）。**这同时是条款漂移**：合同写「48 fits/180 min 硬上限」，代码不可强制 ⇒ 需在「落地台账门控」与「明确降级为非强制指引」之间抉择。
- **`EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING` 量级已实测**：24 批/epoch，中途超时存 `epoch=0` 但 optimizer 已 9 步；恢复后 epoch 0 整体重跑 ⇒ **9/24 = 37.5%** 锚点获二次梯度，总步数 81 = 9+3×24。`best.pt` 仅由完整 epoch 产生，故**选择**未污染，维持 P2。
- **`EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`**：实测 `_safe_impute` 使全 NaN 的 dev 行塌缩为**同一向量**（`drop_duplicates` 后 1 行），无缺失指示列；端到端 504 个 dev 行得到**同一个**分数 `0.5747904879932492`，状态仍 `COMPLETE_H504_DEV`、`average_precision=0.5`。
- **未复现**：对端 10:12 报告所指「沙箱 guard 3/3」与候选 ZIP SHA-256 `4c3343b1…`、验证 JSON `6a6f2763…` —— `git log --all -S` 与磁盘穷举均**未找到**该 ZIP 或任一哈希，`latest_complete_validated`/`STALE_COMPLETE_ARTIFACT`/`required_artifact` 在源码中 **0 命中**，仅见于对端 md 正文。对端已自述其为沙箱候选 guard，属**诚实的范围限定**；但其索引一句话概括易被误读为「当前生产代码已验证」，属**表述风险**。**§1 的 P1 不依赖该未复现项**。
- **真实数字**：全仓测试 AST **65**（40+10+15）；`pytest -q -o addopts= -p no:cacheprovider` 从仓库根 **exit 0 / 65 passed**；`tests/research_h504` **50 passed**；`tests/test_engine.py` **15 passed**；`real_market_fit_count=0`；本机三小时与 receipt **NOT_VERIFIED**（仓库与磁盘均无 `local_start_receipt.json`/`execution_receipt.json`/`experiment_registry.jsonl`）。
- **三轴**：执行=本轮审计动作真实执行；研究结论=完成态复用不具可审计性（工程/证据链结论，**不构成命中率结论**）；证据=上述均为**软件/合成面板**上的真实执行。三类区分：§1–§6 为**程序修复**；48-fit 上限为**任务定义变更**；**真实模型增益 = 0**。
- **并发写入者警示**：本地 HEAD `4b1f3f6e…` 与远端**分叉**且**不在真实远端历史中**（`cat-file -e` False、`is-ancestor` False），相对 `origin/main` 还显示**删除 3 份对端报告** ⇒ 本轮**不以其为基线**。另：`git clone <本地路径>` 得到的 `origin` 是**本地路径**，其 `origin/main` 是该仓**本地** `main` 而非 GitHub 远端；须以 `git ls-remote <url> refs/heads/main` 为权威 tip。
- 本仓**无** `docs/audits/validate_latest.py` ⇒ **不声称**通过任何门禁。

## 最新补充审计（2026-09-22 10:12 JST）：registry 完成态复用缺少底层产物完整性验证

- 完整报告：[`2026-09-22_10-12-36_JST.md`](./2026-09-22_10-12-36_JST.md)。
- 报告首次发布提交：`a33b9d2a624178d510810c565ab549af2e6340e2`；被审 HEAD：`95dca888e95beaf2da04f5b09af424f6e2bc3995`，tree：`54926a21a3dd4b31df55593d6a762c1bb6cb0d6b`。
- **新增 P1 `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`**：`Registry.latest_complete()` 只检查 signature 与 `COMPLETE*` status；`run.py` 命中后直接 `REUSED_COMPLETE` 跳过 H504/AUX 训练，不验证模型、完整开发预测、checkpoint 或训练日志是否存在，更不校验 SHA-256。
- `train_h504.py` 虽写出 `model.pkl / dev_predictions.csv / metrics.json`，但完成结果没有把这些关键文件的 path+sha256 写入 registry。因此 registry 行可以在底层证据已删除/损坏后继续“证明完成”。
- 沙箱 synthetic guard 复现：缺 model/prediction 时当前逻辑仍命中 complete；候选 guard 拒绝；完整文件+hash 允许复用；完成后篡改 prediction 则按 hash mismatch 拒绝。3/3 场景符合预期。候选 ZIP SHA256=`4c3343b1d67e400a980085d34ab069cfba9a0c891bae0c237322a9c3f06ea690`。
- 本轮仍 `real_market_fit_count=0`；没有新的本机 start/execution receipt，故单次连续三小时为 `NOT_VERIFIED`。源码 runner 已是13200秒，但 tracked Windows XML 仍是 `PT2H30M` 模板，不能用模板推断机器注册值。
- 相对上次被审基线没有产品研究源码变化；signature 外部特征依赖、resolved dev 支持、全局48-fit门、AUX部分epoch恢复等旧开放项继续开放，本轮不重复计作新增。
- 下一本地优先级：先把 `COMPLETE_*` 改成 artifact-manifest + hash 的 fail-closed 复用，再做全局fit预算与resolved-aware支持；随后真实 candidate/label/fold，合法则T0/T3，否则同session继续AUX_REAL_HISTORY。

## 最新独立审计（2026-09-22 07:41 JST）：H504 研究管线复核，新增 2 条未被发现的缺陷，并更正 1 条严重度

- 完整报告：[`2026-09-22_07-41-01_JST.md`](./2026-09-22_07-41-01_JST.md)。
- 被审源码 `reviewed_source_sha`: `2b0232f8acb712569aeb5ce68f7291ab3fc7a5dc`；被审区间 `8287b33da26978f1d513b7880baf06a9103d2879..2b0232f8acb712569aeb5ce68f7291ab3fc7a5dc` 共 9 个提交；被审落地 commit `878cdeba5837a302004a8b3a656afee3d6a62b44`。
- **新增 P1 `EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE`**（本轮最高危）：`run.py:94` 的 `pipeline_hash` 只哈希 `src/ml/research_h504/*.py`，而 113 个特征实际由 `src/ml/build_matrix.py` 计算。实测：改 `task_spec.py` 签名会变（对照通过），**改 `build_matrix.py` 签名逐位不变** ⇒ `registry.latest_complete` 命中旧记录，`run.py:158` 报 `REUSED_COMPLETE` 并沿用**陈旧特征**结论，破坏"真实模型增益 vs 任务定义变更"的可分离性。
- **新增 P2 `EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`**：`train_h504.py:13-15` 用 train 中位数静默填补且无缺失指示。实测某 session 特征全缺时，50 个候选得到**同一个**有限分数 `0.695434`，无缺失标记，仍报 `COMPLETE_H504_DEV`。
- **严重度更正（对同批报告的更正）**：`EML-…-OBSERVED-BAR-PROVENANCE-LOST` 由 **P1 降级为 P2**。实测两条路径**仅 `outcome_class` 一列不同**，`label_joint`/`label_resolved`/`training_eligible` 完全一致；`src/` 内**零处**对该列做条件分支或聚合；且该列在 `feature_spec.py:18` 的 `_FORBIDDEN_EXACT` 中，不可能进入模型。
- **我自己的中间结论已撤回**：「`unknown_missing_bar` 是死代码」**过强且错误**。实测在多股票联合日历下该分支**可达**；仅在"单股票 + 面板自生日历"下不可达。
- 决定性证据：**变异测试**。删除 `data_io.py:38` 的补行后套件仍 **50 passed 全绿**；子 agent 独立把同一性质推向相反方向（对整段日历补行、彻底删除 reindex）**同样全绿** ⇒ 现成 50 测试对**生产路径零覆盖**，唯一相关的测试绕过了 `prepare_panel`。
- 维持确认：`EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`（我实测到 **0** 个 resolved 仍报 `COMPLETE_H504_DEV`，对照组为绿，比同批报告的"1 个"更强）、`EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`、`EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`（机制确认，真实影响量未测故不升级）。
- 主动高危检查（负面结论）：**未发现前视泄漏**——切分按时间、特征前缀不变性 30/30 列零变化、`unknown`/`no_entry` 未被编码为 0；子 agent 用独立方法（扰动未来全部行情、783 行前缀 × 113 特征逐位不变）得到一致结论。
- 本轮**未**启动真实训练、未连本机、未注册或修改 Windows 任务；`real_market_fit_count = 0`，无新增实股结果。本仓**无** `docs/audits/validate_latest.py`，**不声称**通过该门禁。


## 最新源码落地后独立审计（2026-09-22 06:02 JST）：H504 链已入 main，但发现 3 个 P1 + 1 个 P2

- 完整报告：[`2026-09-22_06-02-39_JST.md`](./2026-09-22_06-02-39_JST.md)。
- 类型：`POST_INTEGRATION_SOURCE_AUDIT`；被审 HEAD `a8ae13ccf1c4a6a1baf82ad4e86087fbde83e4e4`，源码落地 commit `878cdeba5837a302004a8b3a656afee3d6a62b44`。
- 源码落地是真实工程进展：`src/ml/research_h504/`、runner/prompt、测试已在 `main`；但用户本机三小时和新实股 H504 fit 仍为 `NOT_VERIFIED / 0`。
- 新确认 `EML-P1-H504-OBSERVED-BAR-PROVENANCE-LOST`：`prepare_panel` reindex 后丢失原始 stock-session 是否真的存在 bar 的 provenance，labeler 后续会把真实 missing bar 混成 missing price。
- 新确认 `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`：dev 只要求候选数 `>=50`，未要求可判定 `label_joint` 数量 `>=50`，极少 resolved 样本也可能返回 `COMPLETE_H504_DEV`。
- 新确认 `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`：registry/runner 尚未代码级执行旧 48 次累计 fit 预算，失败/中断/重试的跨 session 计数仍靠 prompt 合同。
- 新登记 `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`：epoch 中途超时会保存部分 epoch 模型，再从该 epoch 整体重跑，改变部分样本的暴露次数；paired attribution 应优先回滚到最后完整 epoch，或实现 batch cursor/sampler 精确恢复。
- source runner 已是 `13200s`，但 tracked Windows XML 仍为 `PT2H30M`；实际注册任务值与真实三小时 receipt 本轮仍未读取，不能说三小时已经跑过。
- 下一本地优先顺序：source-bar provenance → resolved-aware fold → 48-fit budget → 实际 Windows task 核验 → 真实 candidates/labels/fold → 合法 H504 T0，若主任务阻塞则同 session 跑 `AUX_REAL_HISTORY` base-vs-plus。

## 最新源码落地：研究代码已写入 main，不再只有候选ZIP

- 用户最新明确授权研究源码、测试和本地执行入口写入GitHub。
- **源码提交：[878cdeba5837a302004a8b3a656afee3d6a62b44](https://github.com/fy-god/pro-web-60d-strategy/commit/878cdeba5837a302004a8b3a656afee3d6a62b44)**。
- 完整交付记录：[2026-09-22_03-49-55_JST.md](./2026-09-22_03-49-55_JST.md)，文档首次提交 `ca37508b15e8f0ce70b6e7fd3199ac08d1324df2`。
- [研究源码目录](https://github.com/fy-god/pro-web-60d-strategy/tree/878cdeba5837a302004a8b3a656afee3d6a62b44/src/ml/research_h504)；[本地接入说明](https://github.com/fy-god/pro-web-60d-strategy/blob/878cdeba5837a302004a8b3a656afee3d6a62b44/RESEARCH_QUICKSTART.md)。
- 源码提交共23个路径：16个研究Python模块、2个测试文件、2个runner/prompt修改、3个说明与验证文件。原始行情、权重、旧H10结果、Actions及实际Windows注册任务未改。
- 已实际支持 `--stage all --resume --offline`，包含独立日历、候选、H504标签、T0 HGB、AUX TCN、完整开发预测与收据。
- 远端 `scripts/run_fixup.py` 已改为13200秒；`fixup_prompt.txt` 已替换旧“只修P0/P1、同报告直接退出”。因此此前对这两个文件的旧状态描述必须按旧SHA阅读。
- 本轮隔离测试：**50 passed in 12.66s**，范围为新增研究代码及launcher mock，含合成拟合。研究模块tree=`60086cf074a73c6956088c81aab5aa7ab3261b95`；测试tree=`7b5d79c3f0f8872f11726514f54bf286ab990a72`，与实际测试字节一致。
- [验证记录与哈希](https://github.com/fy-god/pro-web-60d-strategy/blob/878cdeba5837a302004a8b3a656afee3d6a62b44/docs/research/h504_integration_validation.json)；[pytest原始输出](https://github.com/fy-god/pro-web-60d-strategy/blob/878cdeba5837a302004a8b3a656afee3d6a62b44/docs/research/h504_integration_pytest.txt)。

### 四种状态分别记录

| 项目 | 当前证据 |
|---|---|
| GitHub研究源码 | 已在main；可直接拉取，不再要求从聊天附件拼装 |
| 软件测试 | 本轮隔离50项通过；完整旧仓库套件未重跑 |
| 用户本机runtime/三小时 | LOCAL_APPLY_PENDING / NOT_VERIFIED；本轮未连接本机 |
| 新实股H504成绩 | real_market_fit_count=0 |

当前是T0+AUX初始研究实现，不是所有T1—T5、MLP、OOF/meta、独立校准与正式发布都已完成。registry不是全局预算控制器，checkpoint恢复不宣称batch级位一致。实际Windows任务上限仍要本地核验；提交源码不等于注册任务或启动训练。

## 最近一次独立审计（保留，不被源码集成记录替代）

- [2026-09-22_03-34-01_JST.md](./2026-09-22_03-34-01_JST.md)。
- 被审源码 `8287b33da26978f1d513b7880baf06a9103d2879`；报告首次发布提交 `05556a9a5d4d95b52605357c1c1dceedf309b0fc`，后续记录提交 `bbc82825c79c7f354179f7198514ab00b96d2c5f`。
- 其中旧生产链缺陷、旧候选测试的证据争议及工作树事故记录保留原文。当前只落实研究模块与本地入口，不宣称旧H10认证/发布链所有问题已经修复。

## 三小时执行要求与原候选来源

- [单次三小时 v5 合同](./2026-09-21_01-43-18_JST.md)：有效10800秒、正常wall12600秒、runner13200秒；实际Windows上限另验。
- [上一版候选集成报告](./2026-09-22_01-57-29_JST.md)：属于当时的ZIP候选记录，不等于当时已入库。
- [前次候选恢复链报告](./2026-09-21_14-06-49_JST.md)。

## 完整历史索引（不可变保留）

[源码落地前完整LATEST：全部历史报告、独立复核、争议和开放问题](https://github.com/fy-god/pro-web-60d-strategy/blob/bbc82825c79c7f354179f7198514ab00b96d2c5f/docs/audits/expert-ml/LATEST.md)。没有删除任何历史审计报告；旧“当前状态”按其固定SHA解释。

下一份值得更新的市场证据：本机实际数据/日历/候选指纹、合法fold、真实训练日志、checkpoint、全开发预测与execution_receipt。软件入库是实际工程交付，不是H504成功率提升。
