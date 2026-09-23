# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 03:48:00 JST）：云端"训练内 50.6% ⇒ 拟合能力存在"的推断**不被其引用的证据支持**；零假设同口径对照显示无信号构型也能到 29.84% 训练内

- 完整报告：[`2026-09-24_03-48-00_JST.md`](./2026-09-24_03-48-00_JST.md)。
- 被审 `main` 起点：`3110d22e04a9c740d1dae7135db518d7402fe9b0`；`git diff --stat e72c7258 3110d22e -- . ':(exclude)docs'` = **EMPTY**，**本轮无新产品源码提交**，Open PR=0。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。
- 上一轮云端报告：[`2026-09-24_02-01-50_JST.md`](./2026-09-24_02-01-50_JST.md)（本轮逐条复算的对象）。

### 本轮做了什么（不含新实股结果）

1. **云端 12 个数字全部逐一复现**（19,885 / 50.600955% / 1,790 / 15.977654% / 4.0878% / 3.91x / 34.6233pp / 31.6% / 1,406,181 / 57,505 / 26.7790% / 32.7273% / 消融 5 行 + 4 个 delta）⇒ **数字本身没有造假**。

2. **但 §1 的推断被证伪（本轮新结论）**：`outputs/ml/audit/nulls_audit.json` 是仓库**自己的零假设电池**，跑在**同一张 stride-5 网格**（`pooled_rows == n_rows == 281,227`；其 `real` 行 `insample_precision` 与云端引用的值**十五位小数相同**，并自证 `harness_vs_audit_precision_max_abs_diff = 0.0`）。同一口径下：

   | 构型 | 训练内 | OOS | gap | AUC |
   |---|---:|---:|---:|---:|
   | real（对照） | 50.6010% | 15.9777% | +34.623pp | 0.6306 |
   | **feat_gauss_auc0**（特征 N(0,1) + 标签 Bernoulli = 双重零假设） | **29.8416%** | 3.2673% | **+26.574pp** | **0.4976** |
   | oracle_strong（阴性对照，标签泄露） | 56.9575% | 39.0459% | +17.912pp | **0.7754** |

   阳性臂 AUC **0.4976 ≤ 0.5**（确证无信号）却已拿到真实 gap 的 **76.8%**；阴性臂 AUC **0.7754 ≫ 0.5** 证明该度量**能**区分信号与噪声。
   ⇒ **"训练内能到 50.6%"不是拟合能力的证据**（选择偏差 + 噪声高分切片就够），该句推断**不被其引用的证据支持**。
   报告全文 **0 次**提到零假设 / `nulls_audit` / `null_ceiling`（逐串实测计数）。

3. **`EML-P2-EVIDENCE-TYPE-NOT-IN-REUSE-SIGNATURE-002` 确认，并已做执行级证明**：签名键集（`src/ml/research_h504/run.py:150`，AST 展开）为 `{pipeline_hash, calendar_hash, task, data, cand_sha256, features, horizon, model_config}`，**不含 `evidence_type`**；`registry.py:19-23` 的 `latest_complete` 只比对 `signature` 与 `COMPLETE` 前缀，而 `evidence_type` 在整个 `registry.py` 中出现 **0 次**。实跑证明：先写入 `evidence_type='SYNTHETIC'`、`status='COMPLETE_H504'` 的行，随后同签名的 `REAL_MARKET` 运行会被 `latest_complete` 判定为"已完成"并发出 `REUSED_COMPLETE`，而该结果键集（`['experiment_id','model_id','signature','source_status','status','task_scope']`）**不含 `evidence_type`**；3 个阴性对照全部成立（异签名→None、非 COMPLETE 状态→None、`COMPLETED_AVAILABLE_RESEARCH_NOT_CERTIFIED` 也会通过前缀测试）。**这是来源标注（provenance）缺陷**，不会篡改一个正确标注的 fit。

4. **口径问题**：三份产物**不是同一个 OOS 总体** —— `ml_crosssec_final.json` 的 `n_rows` **281,227**（stride-5）vs `ml_precision_ceiling.json` 的 `oos_rows` **1,406,181**（`stride=1`, dense），base rate 分别为 `0.040878009579` 与 `0.040894450999`（十五位小数不同）。仓库自己在 `TARGET_70PCT.md:382-396` 有明确的"哪一节用哪张网格"表并写明 **No cross-grid subtraction is made anywhere**，`scripts/audit_reports.py:3001-3030`（gate `EML-P0-CROSSSEC-POP`）还要求 stride-5 运行必须内部自洽。新报告全文 **0 次**出现 `stride` / `dense` / `grid` / `281,227` / `population` / `网格`，**0 次**引用 `TARGET_70PCT`。
   另：`ml_precision_ceiling.json` 的 `recall`/`at_signals` 只对应 `max_precision_raw`（整数性检验：raw×N **8/8** 为整数，rank×N **5/8** 非整数），报告却把 rank 精度 32.7273% 与由 raw 推出的 0.2487% recall 写在同一句 —— **轻微不自洽**；两数都极小，不改变任何决策。

### 仍未修的完整清单

- `EML-P2-EVIDENCE-TYPE-NOT-IN-REUSE-SIGNATURE-002`（**本轮执行级确认**）。
- `scripts/run_fixup.py:23` `AGENT_TIMEOUT_SECONDS = 13200`；`:162 return 0 if rc==0 else 1`，文件内 `target_met` 出现 **0 次**；`receipts.py:173` 仅**记录** `target_met`。`scripts/register_fixup_task.ps1` 的 Windows task 上限 `PT2H30M`(=9000s) < 13200s（须以 **utf-16** 读 `run_fixup.task.xml`；按 UTF-8 解码会误判为缺失）。
- `REUSED_COMPLETE` / `QUEUE_DRAINED` 在 `tests/*.py`（共 4 个测试文件）中覆盖数 **0**。
- `outputs/charts_120d` 实测 **1920** 个跟踪文件（939 hit / 980 miss / 1 `index.html`），**每个策略目录 40 个文件 = 20 hit + 20 miss = 50.00%**，`src/make_charts.py:319/382-383/417` 源码自称 balanced sample 且明写 **"this is NOT the hit rate"** —— 禁止当作命中率引用。

### 测试真数

净提取（`git archive origin/main`，绕过脏工作树）内：`python -m pytest -q` → **65 passed in 23.81s, exit 0**；`-v` 第二次独立计数 → **65 passed in 21.87s, exit 0**。本仓库**无** `pyproject.toml` / `pytest.ini`，故 `-q` 会照常打印汇总行。

### 三小时四状态

- 云端／本轮 prompt：**未改**；本轮没有管理排程。
- GitHub 审计／任务书：**已更新**。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**。
- 本机单次连续 10800 有效秒：**NOT_VERIFIED**。

tracked 13200s 只是 runner 硬超时，不是完成三小时的证据；`PT2H30M` 短上限本轮无本机证据证明已修。

## 历史报告（链接直接保留）

- [`2026-09-24_02-01-50_JST.md`](./2026-09-24_02-01-50_JST.md)
- [`2026-09-23_23-41-00_JST.md`](./2026-09-23_23-41-00_JST.md)

## 前一版索引（不可变保留）

[截至 `3110d22e04a9c740d1dae7135db518d7402fe9b0` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/3110d22e04a9c740d1dae7135db518d7402fe9b0/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。
