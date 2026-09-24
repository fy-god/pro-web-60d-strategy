# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 13:59 JST）：H504 现在没有冻结 publication policy，`COMPLETE_H504_DEV` 不能回答 50%/70%

- 完整报告：[`2026-09-24_13-59-17_JST.md`](./2026-09-24_13-59-17_JST.md)。
- 被审 `main` 起点：`6050d6e4abfaac9efc8f55629a7973717238d1f1`；Open PR=0。
- `0a5f5932..6050d6e4` 只有上一份审计报告与 `LATEST.md` 两个 docs 路径变化，产品研究源码没有新提交。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**；单次连续10800有效秒：**NOT_VERIFIED**。

### 本轮新增核心结论

1. **【P1 · 已确认】`EML-P1-H504-NO-FROZEN-PUBLICATION-POLICY-001`**：当前 `src/ml/research_h504/train_h504.py` 的 HGB 只输出 `logloss / brier / average_precision` 和 raw dev `score`；没有 `threshold / signals / TP / FP / precision / recall / publication_rate / TARGET50_REACHED`。因此 `COMPLETE_H504_DEV` 目前只代表 score model 跑完，**不是 50%/70% 命中率认证**。
2. `src/ml/research_h504/run.py` 也没有 calibration block 或 frozen threshold；如果事后直接在同一 dev 上扫阈值找 50%，会把 dev 同时当 policy-selection 与 evaluation，重新产生选择偏差。
3. 正确协议应为 **train → calibration → untouched dev**：模型在 train 拟合；publication policy 只在 calibration 预注册 grid 上选择；threshold/rank budget 在打开 dev 前冻结；dev 只做一次 TP/signals/precision/recall 评价。
4. unknown/no-entry 不能在结果出来后从 issued set 删除并补位。应同时保存 `issued_signals / resolved_signals / unknown / no_entry / precision_resolved / precision_issued_lower_bound`；target gate 首轮建议用更保守的 issued-denominator lower bound。
5. 当前 `fold_support.py` 的 train→dev dense 理论下界是 `2H+2=1010` sessions；若要 train→calibration→untouched dev 三段均 full maturity，dense 理论下界是 **`3H+3=1515` market sessions**（H=504）。本机真实历史是否达到该支持仍 `NOT_VERIFIED`。

### 本轮隔离候选

- `eml_auto19_h504_precision_policy.zip`
- SHA-256：`14d930846fe5f877b939107a91879e15f9b009ff491d6db8fd724c2009057928`
- 软件测试：**6 passed in 0.05s**。
- 候选接口：`PolicySpec`、`choose_policy_on_calibration()`、`apply_frozen_policy()`、`evaluate_fixed_issued_set()`、`minimum_dense_sessions_train_calib_dev()`。
- 该候选不写产品源码，不计48-fit，不计 real_train_seconds，不是市场成绩。

### 下一次真正有资格叫“模型进展”的 H504 证据

必须同时出现：

```text
真实 candidate/outcome ledger
合法 train→calibration→dev support
真实 fit/checkpoint
calibration predictions
frozen_policy.json
untouched dev predictions
TP / signals / precision / recall / base rate / lift / AP / Brier / log-loss
TARGET50_REACHED 或 TARGET50_NOT_REACHED
```

若历史不支持三段 full-maturity，状态必须是 `BLOCKED_PROTOCOL_H504_POLICY`；可以继续 score 模型/AUX/forward ledger，但不能拿同一 dev 调 threshold 后再报 50%。

### 继续开放但本轮不重复展开

上一轮 11:40 JST 已确认的运行时问题仍未见产品源码提交修复：tracked task template `PT2H30M=9000s < 10800s target`、`target_met=false` 不阻止成功退出、evidence class 复用隔离不足、机器任务图没有覆盖完整 T1-T5/MLP/TCN/ablation/error-driven queue。更早的 G1 数据/标签问题同样仍开放。

## 上一版索引（不可变保留）

[截至 `6050d6e4abfaac9efc8f55629a7973717238d1f1` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/6050d6e4abfaac9efc8f55629a7973717238d1f1/docs/audits/expert-ml/LATEST.md)。

上一份完整报告：[`2026-09-24_11-40-00_JST.md`](./2026-09-24_11-40-00_JST.md)。历史审计 Markdown 未删除；旧状态按各自固定 SHA 与审计时点解释。H10 历史结果只用于研究方法诊断，不得冒充 H504 成绩。