# 专家／ML线研究与审计索引

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
