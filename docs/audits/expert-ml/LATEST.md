# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 23:41 JST）：上一轮的队列饥饿被**实跑证实**；新增一条「证据类型不参与复用签名」缺陷；并首次数出**已入库的真实命中率账本**

- 完整报告：[`2026-09-23_23-41-00_JST.md`](./2026-09-23_23-41-00_JST.md)。
- 被审 `main`：`8fb4f885457f689b6aec7afff1757daa66c50be1`；相对上一审计 `e0fd2ba4` **产品源码零提交**（我实测非 docs diff 为空）；Open PR=0。

### 1. 独立**实跑**证实上一轮的 P0（不是转述）

上一轮从代码阅读论证「固定签名复用后队列枯竭仍 `return 0`」。我在抽取出的干净树里**跑真实 CLI 两次**：

- RUN 1（首次）：新增 fit=1，`COMPLETE_H504_DEV`（**这是正控**，证明脚手架确实驱动了真实训练）；
- RUN 2（同 `--out`、同命令）：**新增 fit=0**、`fits_started=0`、`stop_reason=QUEUE_DRAINED_OR_BLOCKED`、`target_met=False`，而 **rc=0**，状态仍被判为 `COMPLETED_AVAILABLE_RESEARCH_NOT_CERTIFIED`。

我也**自己数出**工作图上限（源码常量，非引用）：`run.py:155` 只有 1 个 H504 注册点（`model_id` 硬编码 `T0`），`run.py:166/168-170` 的 AUX 循环 `reps(2) × seeds(3) = 6` 被 `--max-aux-fits` 默认 6 截断 ⇒ **单次 `--stage all` 新增 fit 上限 = 7**。带正控的搜索确认 MLP / H504-TCN / 误差驱动配对重训 / 第二开发块 在 `origin/main` **均 0 命中**（`receipts.py:159` 的 `training_mlp`/`training_tcn` 只是收据分类名）。

### 2. **新确认错误** `EML-P2-EVIDENCE-TYPE-NOT-IN-REUSE-SIGNATURE-002`

复用签名（`run.py:150` H504、`:173` AUX）**不含 `evidence_type`**（AST 枚举，含正控）；`registry.py:19-23 latest_complete()` **只比对签名与 `COMPLETE` 前缀，完全不看证据类型**；`registry.py` 中 `evidence_type` 出现 **0** 次。实测：

```text
SYNTHETIC 运行 -> registry 行 evidence_type=SYNTHETIC status=COMPLETE_H504_DEV
REAL_MARKET 同 --out 同输入 -> REUSED_COMPLETE，run_summary/execution_receipt 均写 REAL_MARKET
负控：换不同 panel -> COMPLETE_H504_DEV（不复用）  ⇒ 签名确有区分力
```

即**一个软件样本 fit 会被实股标签静默复用**。**我如实限定**：registry 原始行的 `SYNTHETIC` 未被改写，故这是**证据类型可追溯性泄漏，不是伪造数字**；但 `REUSED_COMPLETE` 会喂给 `run.py:186` 的成功判定，**零 fit 运行因此不报 `BLOCKED_NO_FIT`**。可达性为「真实、有条件、多数自己造成」——需要同一 `--out` 且输入字节一致；最可能的触发是 `--evidence-type` **默认为 `UNSPECIFIED`**（`run.py:72`）。修复为一行（把 `evidence_type` 加进两个签名字典，并在复用条目回写来源标签）。

### 3. **新发现（实股证据）**：仓库**已跟踪**的真实命中率账本；`charts_120d` 的 50% 是显示假象

- `origin/main` **跟踪着 1920 个** `outputs/charts_120d/**/<code>_<date>_{hit,miss}.png`。我逐目录计数：约 40 个策略目录**绝大多数精确 20 hit / 20 miss = 50.00%**。
- 生成器 `src/make_charts.py:319-321` 原文写明图表**刻意取平衡样本**，`:381-383` 更直接写 **"balanced sample for visual audit — this is NOT the hit rate"**；`:495-504` 是 `hits.head(per_side)`/`misses.head(per_side)` 的平衡逻辑。⇒ **这些 png 的比例绝不可当作命中率引用。**
- **真实率**在受跟踪的 `reports/lowzone_hit_rates.csv`（14 行）与 `reports/webpro_hit_rates.csv`（35 行）里，我逐行读出：
  - webpro 最好 **leader_momentum 106/553 = 19.17%**；`strict_leader_momentum_v2` 401/2502=16.03%；`strict_relative_strength` 308/1955=15.75%；`relative_strength_rank` 904/8977=10.07%；`limit_up_retest` 659/6679=9.87%。
  - lowzone 更低：V03 1176/26897=**4.37%**；V00 2245/71841=3.12%；low60 regime 18952→15=**0.079%**。
  - **无一条达到 50%，更无一条接近 70%。**
- `reports/hitrate_vs_expectancy.json` 记录 **Spearman(命中率, 净期望收益) = −0.5109**，并自注「negative rank correlation means the reported hit-rate ranking orders strategies in the opposite order to what they earn」。⇒ 把命中率当唯一目标可能与收益**反向**，后续任何「达到 50%」的宣称必须先解释这组已入库数字。
- 边界：这些是**受跟踪的历史账本**，**不是**本轮新结果；本轮真实 A 股新 fit 仍为 **0**。

### 4. 回归与其他

- **仍成立**：`--evidence-type` 默认 `UNSPECIFIED`（`run.py:72`）不触发真实数据守卫（`run.py:88/:90` 只认 `REAL_MARKET`/`AUX_REAL_HISTORY`）。实测 A1 `UNSPECIFIED`+无日历 → rc=0；A2 `REAL_MARKET`+无日历 → rc=1 `BLOCKED_CALENDAR`（**正控**）；A3 `SYNTHETIC`+无日历 → rc=0。
- **降级为未复现**：上一轮 §4 的「隔离测试 6 passed in 0.06s」在 `origin/main` **无任何载体**（`queue_contract`/`work_registry`/文件名 `queue` 均 0 命中）。报告自己说它是本地参考，故不指其为错误，但**不可作为后续回归基线引用**。
- **运行时合同**：`scripts/run_fixup.py:23` hard timeout=13200 s；`:162 return 0 if rc==0 else 1`（**不读 `execution_receipt.target_met`**）；`receipts.py:154-189 finalize()` 只记录 `target_met`，**无 fail-closed**；tracked `scripts/run_fixup.task.xml` 与 `register_fixup_task.ps1:96` 均为 **`PT2H30M`（9000 s）< 要求的 13800 s**。本轮无用户 Windows 通道，故 `LOCAL_RUNTIME_APPLIED=NOT_VERIFIED / LOCAL_APPLY_PENDING`，`LOCAL_SINGLE_CONTINUOUS_3H_COMPLETED=NOT_VERIFIED`。
- **测试真数**：抽取干净树跑仓库自带套件 = **65 passed in 19.05s，rc=0**（我实跑）。覆盖盲区：全套 65 个测试中 `REUSED_COMPLETE` 与 `QUEUE_DRAINED` 命中 **0 个文件**；`test_registry_reuses_exact_complete_signature_only` 虽测复用，但**从未涉及 `evidence_type`**；`origin/main` **无 `.github/`，无 CI**。
- **模型状态不粉饰**：本轮真实 A 股 H504 fit 增量=**0**；H504 >50% 模型=**0**；H504 >70% 模型=**0**。既有较强历史数字仍是 H10 归档（RF 开发期 OOS precision≈20.84%，HGB 历史留出 844/6202≈13.61%），不能冒充 H504。

## 当前执行优先级

1. **先修执行器的两个成功门**：把 `evidence_type` 纳入复用签名并回写来源标签；让 launcher 读取 `execution_receipt.target_met`，且 `REUSED_COMPLETE` 对本次有效时长贡献计 0；队列耗尽的会话必须非零退出（验收即上面 RUN 2 变红）。
2. **持久 work registry**：H504 T0—T5；MLP T0/T3×3 seeds；TCN T0/T3×2 seeds；去KDJ/位置/RSI/PDC/mask-only/负控制；FP/FN 与 risk/timeout/no-entry/unknown 分析；误差驱动配对 2fit；无合法 H504 折才转 AUX base/plus×3 seeds。未实现项标 `NEEDS_IMPLEMENTATION`，不能从队列消失。
3. **同一轮开始真实数据处理**：panel/calendar/basis/candidate/label/fold 指纹；修掉会直接污染数据与标签的已知 G1 错误。
4. **把 50%/70% 变成受测口径而不是口号**：与已入库账本并列输出 `precision / signals / recall / base_rate / lift / net expectancy`，并显式处理 `hitrate_vs_expectancy.json` 的 ρ=−0.51；若最好时间外 precision <50%，明确写 `TARGET50_NOT_REACHED`，不要用「又发现一个 P1」替代模型结果。

## 上一版审计报告（保留）

- [`2026-09-23_22-02-21_JST.md`](./2026-09-23_22-02-21_JST.md) —— 首次以代码阅读提出 `EML-P0-REUSED-COMPLETE-QUEUE-STARVATION-001`；本轮已把它**实跑证实**（见上文 §1）。其中 §4 声称的「隔离测试 6 passed in 0.06s」在本仓库**无载体**，本轮已降级为不可引用的本地证据。

## 前一版索引（不可变保留）

[截至 `8fb4f885457f689b6aec7afff1757daa66c50be1` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/8fb4f885457f689b6aec7afff1757daa66c50be1/docs/audits/expert-ml/LATEST.md)。

[截至 `e0fd2ba46b0ad1f55e0dfdf3d5ea4887a785c15c` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/e0fd2ba46b0ad1f55e0dfdf3d5ea4887a785c15c/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。
