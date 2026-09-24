# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 09:59 JST）：先修“几分钟下班”的执行器，再把模型预算转向 causal regime + 候选总体富集

- 完整报告：[`2026-09-24_09-59-34_JST.md`](./2026-09-24_09-59-34_JST.md)。
- 被审 `main` 起点：`7c8596e654dc1a376df195540d3b4aa72347b055`；本轮开始时 Open PR=0，产品研究源码相对上一轮无新提交。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**；单次连续10800有效秒：**NOT_VERIFIED**。

### 本轮新增的模型研究诊断

1. **HGB 的 pooled 16.44% 被强烈的折间信号密度偏斜支配。** `wide_hgb_2` 四折 precision 为 14.56% / 24.72% / 21.09% / 33.60%，但 **83.78%** 的信号都出现在最弱的第一折；pooled=16.44%，四折等权均值=23.49%。这说明“市场阶段下应该发多少信号”本身是核心建模问题，下一步优先 causal regime conditioning / rank budget，而不是继续加树深。
2. **RF 是更稳健的 H10 方法学基准。** `wide_rf_32` 四折约 22.88% / 18.36% / 18.06% / 20.71%，pooled=20.84%，等权均值=20.00%；离50%仍远，但折间稳定性明显好于 HGB。真实 H504 首轮不应只有 HGB，至少固定同一 candidate/outcome/fold 比较 Logistic/HGB/RF/ExtraTrees。
3. **旧 H10 score 仅靠阈值仍没有50%的证据。** dense OOS precision ceiling：raw max≈26.78%，rank 在至少50个信号时≈32.73%；因此下一步的50%假设必须来自候选总体重定义、因果 regime、hard-negative discrimination 或真正的新信息，而不是 threshold cosmetics。

### 本轮执行器候选

隔离沙箱实现了 `eml_auto18_research_queue_candidate.zip`，SHA-256 `cf3c313fe7a1a92cd4f6c26e73d743599e4b54baa332a28bdf8e4885b9bf300e`，单测 **7 passed in 0.07s**。它把 v5 中目前只写在任务书里的工作真正编码成 queue node：H504 T0-T5、MLP、TCN、六项消融、第二dev、error mechanism/control 与 AUX fallback；`REUSED_COMPLETE` 不算新工作，`INTERRUPTED` 优先续跑，`evidence_type` 进入 signature，under-target 且仍有 READY/NEEDS_IMPLEMENTATION/INTERRUPTED 时不得成功退出。

### 当前执行器仍开放的硬问题

- `run.py --stage all` 机器化的主线仍只有 **H504 T0 1 fit + 有限 AUX-TCN**；T1-T5 / H504 MLP/TCN / ablation / error-driven refit 仍不是持久任务节点。
- `Registry.latest_complete(signature)` 仍不校验 evidence class；真实和合成来源隔离不足。
- `ResearchSessionReceipt` 只记录 `target_met`，runner 不用它控制成功退出。
- `scripts/run_fixup.py` 仍最终依据 child rc；`target_met=false` 也可能外层成功。
- tracked runner timeout=13200s，但 `register_fixup_task.ps1` 仍生成 `PT2H30M`，且会 delete/create task；不符合 v5 的既有任务窄修改要求。

### 下一次真实本机研究的第一波 6 fit

固定同一 H504 candidate/outcome/fold，只先跑：

1. `T0_clean_hgb`
2. `T0_clean_rf`
3. `T1_pruned_hgb`
4. `T1_pruned_rf`
5. `T2_regime_hgb`
6. `T2_regime_rf`

其中 regime 只能使用 t 及以前已知的 breadth / index drawdown-volatility / liquidity-turnover / cross-sectional dispersion。每个 fit 必须保存**全部 dev candidate predictions**以及 TP/signals/precision/recall/base rate/lift/AP/Brier/log-loss/逐折结果。随后必须做高置信 FP/FN 切片，并只基于一个有支持机制做 `ERR_MECH` + `ERR_CONTROL` 配对重训。没有这些产物，pytest 或 Markdown 不算模型进展。

## 前一版索引（不可变保留）

[截至 `7c8596e654dc1a376df195540d3b4aa72347b055` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/7c8596e654dc1a376df195540d3b4aa72347b055/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除；旧状态按各自固定 SHA 与审计时点解释。H10 历史结果只用于研究方法诊断，不得冒充 H504 成绩。