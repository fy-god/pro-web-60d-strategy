# 专家／ML线研究与审计索引

## 最新审计（2026-09-29 21:08:16 CST）：registry 只凭 COMPLETE 文本状态复用，未核验模型、完整预测与 artifact hash

- 完整报告：[`2026-09-29_21-08-16_CST.md`](./2026-09-29_21-08-16_CST.md)。
- 报告提交：`0031820a28f482cd14e26f151bb214579fcac3e0`。
- 被审产品源码起点：`79ed7ea73b1a093f580fce103721269ef580a144`；该起点相对当时 `main` 为 identical，Open PR=0。
- 本轮只新增审计文档并更新索引；未修改产品源码、tests、scripts、Actions、SCHEDULE、研究配置、模型、权重或原始行情。
- 用户 Windows 本机真实新增 fit：**UNKNOWN**；48-fit used/remaining：**UNKNOWN**。
- `TARGET50_REACHED=NOT_PROVEN`；`TARGET70_REACHED=NOT_PROVEN`。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**；单次连续10800有效秒：**NOT_VERIFIED**。

### 本轮新增核心结论

**【P1 · 已确认】`EML-P1-REGISTRY-REUSE-TRUSTS-COMPLETE-WITHOUT-ARTIFACT-ATTESTATION-001`**

当前 `Registry.latest_complete(signature)` 只检查：

```text
signature match
status startswith COMPLETE
```

随后 `run.py` 可直接生成 `REUSED_COMPLETE`，但不会重新验证：

- H504 `model.pkl`；
- H504/AUX 完整 `dev_predictions.csv`；
- `metrics.json`；
- AUX best checkpoint；
- artifact 路径、字节数与 SHA-256；
- prior execution receipt 的 artifact manifest。

因此，旧 registry row 即使对应的模型、checkpoint 或完整预测已删除、截断、覆盖或损坏，当前代码仍可能把它当成可复用 COMPLETE，并跳过真实训练。

### 要求的修复顺序

```text
experiment identity
→ matching COMPLETE row
→ task_scope / evidence_type 核验
→ artifact manifest schema 核验
→ required artifact roles 完整性核验
→ 重新计算每个 required artifact 的 size / SHA-256
→ 全部一致才允许 REUSED_COMPLETE
```

H504 COMPLETE 至少绑定：

```text
model
dev_predictions
metrics
```

AUX COMPLETE 至少绑定：

```text
best_checkpoint
dev_predictions
metrics
```

旧 status-only COMPLETE 应标记为 `LEGACY_UNCERTIFIED_ARTIFACTS`，不得静默升级为认证结果。artifact 不可复用且确需重训时，仍须先通过 G0/G1 与 persistent 48-fit `RESERVE`，不能无预算自动重训。

### 本轮隔离候选

- `eml_auto51_registry_artifact_attestation_guard.zip`
- SHA-256：`9949f64ce9be7b7997176561467197300555050ddd1d80e4c9d0ac7a283897ac`
- 软件测试：**8 passed in 0.07s**。
- 覆盖：status-only COMPLETE 错误复用、legacy manifest 缺失、模型/预测缺失、模型 bytes 变化、required role 缺失、task scope 不匹配，以及完整 artifact manifest 的合法复用。
- 该候选在隔离沙箱生成，不写产品源码、不计48-fit、不计 real_train_seconds，也不是市场成绩。

### 本地下一批必须连续推进的工作

1. 枚举本地 `experiment_registry.jsonl` 的全部 COMPLETE rows。
2. 对每行定位真实 model/checkpoint/full prediction/metrics，并生成 role/path/size/SHA-256 manifest。
3. 将缺失、损坏或 legacy status-only COMPLETE 标为 uncertified；保留旧行，不覆盖历史。
4. 先完成 pipeline/code-key/missing-session/KDJ/breadth/beta 等 G1 修复，再判断哪些旧实验必须重算。
5. 需要重训时先走 persistent 48-fit reservation；失败、OOM、中断和 retry 均按真实 attempt 入账。
6. 新 COMPLETE 必须先通过 model reload、完整预测重生成和 artifact attestation，再 append registry。
7. session receipt 记录本轮 reuse/retrain 决策及所核验的 artifact hashes。
8. 即使存在合法 `REUSED_COMPLETE`，三小时 session 仍须独立满足 `effective_seconds>=10800`；模型可复用不等于本轮三小时研究完成。

### 仍未解决、不能冒充模型进展

- tracked Windows task XML 仍为 `PT2H30M`；机器实际注册值未核验；
- 48-fit 跨进程 persistent ledger 尚未得到本机回传认证；
- `target_met=false` 仍可能被 completed-style 状态掩盖；
- 完整 T1-T5、MLP、H504-TCN、消融和 error-driven paired retrain 队列尚未完整产品化；
- 没有新的严格 REAL_MARKET H504 checkpoint、full prediction 或可复算命中率证据。

## 上一版索引（不可变保留）

[截至 `79ed7ea73b1a093f580fce103721269ef580a144` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/79ed7ea73b1a093f580fce103721269ef580a144/docs/audits/expert-ml/LATEST.md)。

上一份索引中的完整报告：[`2026-09-24_21-59-50_JST.md`](./2026-09-24_21-59-50_JST.md)。历史审计 Markdown 未删除；旧 H10、旧 low504、AUX、synthetic 或软件测试结果只能按各自固定 SHA、任务口径和证据类型解释，不得冒充当前严格 REAL_MARKET H504 成绩。
