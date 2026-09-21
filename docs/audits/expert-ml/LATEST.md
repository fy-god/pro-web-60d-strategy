# 专家／ML最新研究与审计索引

## 最新研究推进（2026-09-21 18:03 JST）：H10折支持稳定性＋holdout产物契约检查

- 完整报告：[`2026-09-21_18-03-47_JST.md`](./2026-09-21_18-03-47_JST.md)。
- 类型：`ARCHIVED_REAL_RESULT_REANALYSIS_AND_AUDIT_CANDIDATE`；本轮 `real_market_fit_count=0`，不是H504新成绩。
- 被审默认分支：`c56f89865d777f525118112bd16ea753de44efc5`；tree：`2138c10739c148ccf523d6ea21382ea770bdbb09`；Open PR=0。
- 报告发布提交：`8b3034d77c418c85919170f7074e909e8540f187`；报告blob：`084faa36ed54533c4e978d383de24570bd5b47ae`，已按返回提交回读。
- **纠正15:48报告一处计数笔误**：当前 `src/ml/final_holdout.py` 初始payload相对tracked `reports/ml_final_holdout.json` 缺失的是**4个**字段，不是3个：`date_clustered_method`、`date_clustered_95_block1`、`date_clustered_95_signal_dates_only`、`holdout_calendar_sessions`。当前 `audit_reports.py` 的 `TOP_LEVEL_FIELDS` 没覆盖这四键，因此629检查仍抓不到该producer/artifact漂移。
- **H10归档新分析**：`fam_rf_5` pooled precision 20.84%，四折为22.88%/18.36%/18.06%/20.71%，最大单折信号占49.02%，signal-HHI折算有效支持折2.75；三条HGB候选最大单折占80.31%–85.88%，有效支持折仅1.34–1.49。RF的20.84%不是靠一个几百信号的小折抬高，值得作为未来未曝光H10时间块的冻结候选；仍不是RF>HGB的配对显著性证明，更不是H504成绩。
- null控制继续接近基率：permuted-label mean 3.1067% vs base 3.0842%；noise 4.0628% vs base 4.0894%，lift 0.9935x。
- 当前沙箱实际实现并测试 `audit_holdout_contract.py` 与 `analyze_h10_stability.py`，`3 passed`；附件zip SHA256=`295df8569525572319923e5f46c069882344c430358f755c53ee1a47ff50d609`。这是软件/归档分析，不是本机三小时训练。
- 用户本机runtime仍 `LOCAL_APPLY_PENDING`，单次三小时仍 `NOT_RUN`：上一独立审计已证明 `ProWeb60d-Fixup` 根本未注册；没有start/execution receipt、真实registry/checkpoint/predictions前不得称完成。

## 最近一次独立源码/本机复核（保留，不被本次归档分析替代）

- 完整报告：[`2026-09-21_15-48-00_JST.md`](./2026-09-21_15-48-00_JST.md)。
- 类型：`INDEPENDENT_AUDIT_AND_PROVENANCE_RECONCILIATION`。
- 被审默认分支：`5d1b365cd6c2a80a74b18fbf12e47e766203eb93`。
- 核心事实保持有效：本机 `ProWeb60d-Fixup` 未注册；自最后产品源码提交后多轮审计无人自动消费；仓库生产者 `src.ml.final_holdout` 本机真实重跑91.4s，H10点估计 844/6202=13.61%、base 2.8958%、lift 4.70x完全复现；tracked clustered CI陈旧；候选v4只存在审计沙箱证据，不能当仓库已落地产物。
- 本次仅把其“缺3字段”文字计数更正为4；不撤销其点估计复现、CI陈旧、fixup未注册等主结论。

## 最近候选执行链（保留）

- [`2026-09-21_14-06-49_JST.md`](./2026-09-21_14-06-49_JST.md)：三小时执行收据、epoch级resume候选v4；仓库未落地、实股fit=0。
- [`2026-09-21_10-08-25_JST.md`](./2026-09-21_10-08-25_JST.md)：可执行研究流水线v3候选；仓库未落地。
- [`2026-09-21_06-03-05_JST.md`](./2026-09-21_06-03-05_JST.md)：session-clock H504候选v2。
- [`2026-09-21_02-07-54_JST.md`](./2026-09-21_02-07-54_JST.md)：H504合同/FeatureSpec/fold-support/VIR候选。
- [`2026-09-21_01-43-18_JST.md`](./2026-09-21_01-43-18_JST.md)：单次连续三小时执行合同。

## 历史索引归档

本次不删除任何历史报告。更新前的完整长索引固定在：

- [`LATEST.md@c56f898`](https://github.com/fy-god/pro-web-60d-strategy/blob/c56f89865d777f525118112bd16ea753de44efc5/docs/audits/expert-ml/LATEST.md)

> 当前最重要的项目边界：H10已有本机可复现真实OOS证据；H504仍没有合法新实股训练结果。下一次真正改变项目状态的证据应是用户本机非文档产物（start receipt、真实registry/checkpoint、全量predictions、execution receipt），而不是继续增加候选版本号。
