# 专家／ML线研究与审计索引

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
