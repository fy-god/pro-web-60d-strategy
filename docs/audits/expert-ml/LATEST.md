# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 11:40 JST）：时长链倒置——注册上限 9000s 低于 10800s 目标，且成功退出口不读收据

- 完整报告：[`2026-09-24_11-40-00_JST.md`](./2026-09-24_11-40-00_JST.md)。
- 被审 `main` 起点：`0a5f5932a31687578b2e775478ad9d92853dd9a5`；`git ls-remote` 回读一致；相对其父 `7c8596e6` **只加 2 个 docs 提交**，
  `git diff --name-status -- . ':(exclude)docs'` **为空** ⇒ 被点名的 6 个源码文件**零字节变化**。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。
- 本机 runtime：**NOT_VERIFIED**（本线未查询本机已注册任务，只对跟踪模板下结论）。
- 本仓**无** `docs/audits/validate_latest.py` ⇒ **不声称**通过该门禁。

### 本轮新增/升级

1. **【已确认错误 · P1】`PT2H30M` = 9000 s 比 10800 s 研究目标低 1800 s。**
   `scripts/register_fixup_task.ps1:96`（→`:115`）与 `scripts/run_fixup.task.xml:16` 同值。
   链序应当单调，实测**倒置**：`9000 < 13200 > 12600 > 10800`。
   ⇒ 在该任务定义下 `target_met`（`receipts.py:173`）**由构造即不可满足**。
   前轮已建议改 `PT3H50M`(13800 s)，本轮补上算术后果：不是「还没接入」，而是**接入了也达不成**。
2. **【已确认错误 · P1】成功退出口不读 `target_met`（4 臂实测，含阴性对照）。**
   真 `scripts/run_fixup.py`，仅替换 `Popen`：收据写 `target_met=false`、`effective_seconds=12.5` ⇒ **exit 0**；
   **完全无收据**也 exit 0；**阴性对照** child `rc=1` ⇒ **exit 1**（证明映射确由 child rc 驱动，故 0 是真 fail-open）。
   `run_fixup.py` 从不打开 `execution_receipt.json`（命中 0）；`:161` 的
   `'training_status':'READ_RESEARCH_EXECUTION_RECEIPT'` 是**字面量**，不是读取。
3. **【已确认错误 · P2】缺陷被测试钉死**：`tests/research_h504/test_candidate.py:315-331`
   **同一测试**既断言 `main(...) == 0`（`:320-322`）又断言 `end['target_met'] is False`（`:327`）。
4. **【已确认错误 · P2】零测试覆盖（变异实测）**：`run_fixup.py` 终判改 `return 0` ⇒ **65 passed 存活**；
   `PT2H30M`→`PT3H50M` ⇒ **65 passed 存活**。
   **阳性对照**：打断 `registry.latest_complete` ⇒ 1 failed；`run.py` 末 `return 0`→`7` ⇒ 3 failed（装置有判别力）。
5. **【修复后回归】前轮 5 条开放项 5/5 仍 `STILL_TRUE`**（blob：`run.py c27711f6`、
   `registry.py 82b1987b`、`receipts.py cdac56d8`、`run_fixup.py 26a61796`、
   `register_fixup_task.ps1 1c133254`、`run_fixup.task.xml 363a57e4`）。路径精度更正：真实文件是
   `src/ml/research_h504/run.py`，仓库根**没有** `run.py`。

### 真实执行计数（软件样本）

- 尖端干净克隆真套件：**`65 passed`**（`26.92s`；复跑 `22.18s`），`65 tests collected`。
- 退出码臂 **4 条**；变异 **5 组**（含基线 + 2 阳性对照）。

### 待验证风险

- 另一个写入者工作树里**未提交**的 `docs/audits/expert-ml/LATEST.md`（9081 B，sha256 `84f75697…`）
  表头是 **2026-09-22 07:41**，比尖端**落后 52 个提交**；若其提交/推送，**索引会回退**。
  我**未**改动它（不得覆盖他人未提交改动），本轮从尖端克隆发布。
  其同批未提交的 `scripts/register_fixup_task.ps1` 改动只是 CRLF 归一化，`PT2H30M` 两版都是 1 处，**未修本问题**。

## 上一轮索引（不可变保留）

上一轮：`2026-09-24 09:59 JST`（[`2026-09-24_09-59-34_JST.md`](./2026-09-24_09-59-34_JST.md)），被审 `main` 起点
`7c8596e654dc1a376df195540d3b4aa72347b055`。

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
