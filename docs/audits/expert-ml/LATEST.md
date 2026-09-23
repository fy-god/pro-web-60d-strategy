# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 02:01:50 JST）：50% 不是“拟合不出来”，而是**训练内 50.6% → 时间外约 16% 的泛化崩塌**；现有 H10 score 仅靠阈值也摸不到 50%

- 完整报告：[`2026-09-24_02-01-50_JST.md`](./2026-09-24_02-01-50_JST.md)。
- 被审 `main` 起点：`e72c7258537b0e5c70bee6d5253faaa45fcf6b73`；本轮开始时无新的产品源码提交，Open PR=0。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。历史 H10 只用于诊断研究方法，绝不冒充 H504。

### 本轮新增的量化诊断

1. `reports/ml_crosssec_final.json`：`fam_hgb_0` 训练内 global-threshold **19,885 signals / 50.600955% precision**；OOS 同类 global-threshold **1,790 signals / 15.977654% precision**，从训练到时间外掉 **34.6233 个百分点**。当前主要矛盾是泛化，不是模型连训练集都拟合不了。
2. `reports/ml_precision_ceiling.json`：现有 H10 分数在 OOS 的 raw max precision 约 **26.7790%**；rank-score 即使只要求最少50个信号，最高也约 **32.7273%**（534 signals，recall≈0.2487%）；250/500信号约 **28.6385%**。所以“只继续拉阈值”没有证据能到50%。
3. `reports/ml_search_ablation.json`：all-features OOS **16.4375%**；删 `cross` 后 **18.5295%**（+2.0921pp），删 `momentum` 后 17.3894%，删 KDJ 后 16.3825%。至少在该 H10 历史实验里，全量特征并非越多越好，cross 家族存在明显时间外拖累；KDJ 的这组边际增益接近0。这个结论只用于重排 H504 实验优先级，不允许借 H10 消融删除 H504 的 KDJ/长期位置核心。

### 下一次真实本机研究必须做什么

- 首先对 H504 真实 candidate/outcome ledger 做 base-rate 分层：success/risk/timeout/no-entry/unknown、年份、股票、流动性、上市年限、价格位置、长期回撤、KDJ 路径、candidate family；同时冻结 calendar/basis/known_at/label_end 与全部指纹。
- 同一合法时间折做配对：`T0_clean(KDJ+长期位置+最小价量)` → `T1_pruned(只加健康 family raw，默认不全量带 cross)` → `T2_hardneg(专门研究最像正例但最终 risk/timeout 的 hard negatives)`；HGB、Logistic、RF、ExtraTrees先做稳定基准，只有表格模型出现真实增益再进 MLP/TCN。
- 每个 fit 保存完整 dev predictions；最后切最高分 FP 为 risk/timeout/高位反弹误判/流动性或数据问题，依据一个有支持机制做一次配对修改再训。若时间外 precision <50%，必须明确 `TARGET50_NOT_REACHED`。

### 仍开放的执行器阻塞

上一轮 [`2026-09-23_23-41-00_JST.md`](./2026-09-23_23-41-00_JST.md) 已经通过真实 CLI 复现：签名全复用后新增 fit=0、`target_met=false`，runner 仍可 `return 0`；同时确认 `evidence_type` 不参与复用签名。本轮没有产品源码更新，因此两个问题仍开放。没有持久 work registry 和 target enforcement，本机任务仍可能几分钟结束。

### 三小时四状态

- 云端／本轮 prompt：**未改**；本轮没有管理排程。
- GitHub 审计／任务书：**已更新**。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**。
- 本机单次连续 10800 有效秒：**NOT_VERIFIED**。

tracked 13200s 只是 runner 硬超时，不是完成三小时的证据；之前 tracked Windows task 仍有 `PT2H30M` 短上限，本轮无用户本机证据证明已修。

## 前一版索引（不可变保留）

[截至 `e72c7258537b0e5c70bee6d5253faaa45fcf6b73` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/e72c7258537b0e5c70bee6d5253faaa45fcf6b73/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。
