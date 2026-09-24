# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 21:59:50 JST）：专家候选信息在 H504 fit 前被擦掉；量压与 RSI 两个 raw 字段存在确定性语义错误

- 完整报告：[`2026-09-24_21-59-50_JST.md`](./2026-09-24_21-59-50_JST.md)。
- 报告提交：`e693b53bc5dca2b476acc51ff14841eef120a3eb`。
- 被审 `main` 起点：`26f629db484519f04f158a96031892d2e410823c`；Open PR=0。
- 上一轮以后没有新的产品源码或模型产物提交；本轮只做源码审计、隔离软件复现和 docs 同步。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**；单次连续10800有效秒：**NOT_VERIFIED**。

### 本轮新增核心结论

1. **【P1 · 已确认】`EML-P1-H504-EXPERT-CANDIDATE-FEATURES-ERASED-BEFORE-FIT-001`**：`build_layers()` 产生 recall_tier 与 raw family；`build_candidate_manifest()` 只留下 `code/date/recall_tier`；`label_h504_candidates()` 又不保留 recall_tier；`run_h504_hgb()` 最后只把 outcome 与 snapshot feature frame 合并。当前 T0 是“专家规则限定候选总体 + snapshot ML”，**不是 expert features 与 ML 的直接融合**。T1=`T0+family raw` 在当前 CLI 下没有 PIT-safe 输入桥。
2. **【P2 · 已确认】`EML-P2-LOWZONE-DOWN-VOL-RATIO5-IMPOSSIBLE-MINPERIODS-001`**：当前 `down_vol_ratio5` 分别对 down/up 稀疏序列做 `rolling(5,min_periods=3)`；同一5行窗口不可能同时有>=3 down和>=3 up，因此两边不能同时 finite。隔离反例 40 行交替涨跌得到 **0/40 finite**。后续不能让 imputer 把这个结构性坏字段伪装成量压因子。
3. **【P2 · 已确认】`EML-P2-LOWZONE-RSI-ZERO-LOSS-BECOMES-NAN-001`**：当前 lowzone RSI 在 `avg_loss=0` 时经 `_safe_div()` 变 NaN；连续上涨因此不是 RSI=100，而是 missing；平盘也不是50。WP3/T4 的 RSI raw 必须先修边界语义再进模型。
4. archived `reports/lowzone_baselines.json` 不是当前严格 H504 成绩，但 old low504 tier rate 本身明显非单调（tier>=1约5.94%、tier>=5约4.20%），因此首轮不应只把 `recall_tier=1..5` 当一个线性序数；建议 nested `tier_ge_*` + exact-tier one-hot，并与 raw family 分开。
5. 推荐保持 `candidate_manifest / candidate_feature_sidecar / outcome_ledger` 三表分离，用 immutable `candidate_id` 在训练边界前合并；sidecar 强制 `known_at<=signal_date`、future/outcome 列 fail-closed，并把 sidecar/schema/hash 纳入 experiment signature。

### 本轮隔离候选

- `eml_auto21_expert_feature_bridge.zip`
- SHA-256：`40022488f199d7581c45b95bae4d9320ed7620563a23c12fe2e8e0289b0cc610`
- 软件测试：**8 passed in 0.08s**。
- 覆盖：expert sidecar、immutable candidate_id join、tier一致性、future/outcome列拒绝、nested/exact tier编码、量压可实现修复、RSI 100/0/50 边界语义。
- 该候选不写产品源码，不计48-fit，不计 real_train_seconds，不是市场成绩。

### 下一次真正有资格叫“模型进展”的首个配对

在同一真实 candidate/outcome/fold 上优先做：

```text
A0 = T0 snapshot only
A1 = A0 + candidate tier nested/exact
A2 = A1 + repaired RSI raw + repaired directional-volume raw
```

HGB/RF 各做同容量配对，保存 full dev predictions、candidate_id/fold_id、TP/signals/precision/recall/base rate/lift、AP/Brier/logloss、risk/timeout/no-entry/unknown 与日期/股票集中度。无合法 H504 fold 就明确 `BLOCKED_PROTOCOL_H504`，不能缩短目标凑分。

### 继续开放但本轮不重复展开

- observed-bar/calendar separation 与 KDJ filler poison；
- independent-calendar `market_session_id`；
- risk-known/close-missing oracle；
- resolved-dev support gate；
- frozen publication policy；
- non-overlapping fold plan；
- evidence_type 进入 registry signature；
- pipeline hash 覆盖 build_matrix/features 等真实依赖；
- 48-fit 跨进程预算控制；
- `target_met=false` 不能成功结束；
- 完整 T1-T5 / MLP / H504-TCN / ablation / error-driven queue 未产品化；
- tracked Windows task XML 仍为 `PT2H30M`，机器实际注册值仍未核验。

## 上一版索引（不可变保留）

[截至 `26f629db484519f04f158a96031892d2e410823c` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/26f629db484519f04f158a96031892d2e410823c/docs/audits/expert-ml/LATEST.md)。

上一份完整报告：[`2026-09-24_18-07-23_JST.md`](./2026-09-24_18-07-23_JST.md)。历史审计 Markdown 未删除；旧状态按各自固定 SHA 与审计时点解释。H10/旧 low504 归档只用于研究方法诊断，不得冒充当前严格 H504 成绩。
