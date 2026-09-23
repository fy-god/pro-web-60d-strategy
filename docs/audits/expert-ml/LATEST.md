# 专家／ML线研究与审计索引

## 最新审计（2026-09-23 22:02 JST）：固定签名复用把研究队列吃空，直接解释“几分钟结束但没有新模型”

- 完整报告：[`2026-09-23_22-02-21_JST.md`](./2026-09-23_22-02-21_JST.md)。
- 被审 `main` 起点：`e0fd2ba46b0ad1f55e0dfdf3d5ea4887a785c15c`；本轮开始时产品源码相对上一审计没有新研究提交；Open PR=0。
- **新 P0** `EML-P0-REUSED-COMPLETE-QUEUE-STARVATION-001`：当前 `src/ml/research_h504/run.py --stage all` 的机器任务图实际上只有 **H504 T0 HGB + 最多6个 AUX-TCN**。T1—T5、H504 MLP/TCN、消融、第二开发块与误差驱动配对重训并未注册为自动 work item。已有签名命中 `registry.latest_complete()` 时只追加 `REUSED_COMPLETE`，不产生新 fit；固定签名全部复用后没有下一节点可领，随后 `QUEUE_DRAINED_OR_BLOCKED` 且 `return 0`。这不是“三小时研究完成”，而是**队列根本没有继续展开**。
- `scripts/fixup_prompt.txt` 已经明确要求10800秒、继续 READY/INTERRUPTED、实现 T1—T5、不要只写 Markdown；因此继续加长 prompt 不是修复。必须把 v5 任务变成持久 work registry，并让 `REUSED_COMPLETE` 对本次有效工作计时为0。
- 外层 `scripts/run_fixup.py` 仍主要依据 child rc 返回成功，没有读取 `execution_receipt.target_met` 做成功门；所以短会话仍可穿透到 launcher 成功退出。
- **模型状态不粉饰**：本轮真实 A 股 H504 fit 增量=0；H504 >50% 模型=0；H504 >70% 模型=0。现有较强历史数字仍是 H10 归档：RF 开发期 OOS precision≈20.84%，HGB 历史留出=844/6202≈13.61%；不能冒充 H504。
- **EXECUTION_PLAN_UPDATE**：下一次本地执行先物化持久队列：H504 T0—T5；MLP T0/T3×3 seeds；TCN T0/T3×2 seeds；去KDJ/位置/RSI/PDC/mask-only/负控制；FP/FN与risk/timeout/no-entry/unknown分析；误差驱动配对2fit；无合法H504折才转 AUX base/plus×3 seeds。未实现项必须标 `NEEDS_IMPLEMENTATION`，不能从队列消失。
- 本轮隔离 queue-contract 候选：**6 passed in 0.06s**，覆盖“只有 REUSED_COMPLETE 不得成功退出”“T0复用但T1未实现时必须领取 IMPLEMENT”“48-fit用尽仍继续分析”“达到10800秒才允许target-met退出”。这是软件证据，不是市场成绩。
- tracked runner hard timeout=13200s；tracked `scripts/run_fixup.task.xml` 仍为 `PT2H30M`。本轮没有用户 Windows 执行通道，因此 `LOCAL_RUNTIME_APPLIED=NOT_VERIFIED / LOCAL_APPLY_PENDING`，`LOCAL_SINGLE_CONTINUOUS_3H_COMPLETED=NOT_VERIFIED`。

## 当前执行优先级

1. **先修“会五分钟下班”的执行器**：持久 work registry + under-target fail-closed + launcher读取execution receipt；不要再靠 prompt 文本约束。
2. 同一轮开始真实数据处理：panel/calendar/basis/candidate/label/fold 指纹；修掉会直接污染数据与标签的已知 G1 错误。
3. 有合法 H504 折就连续做新的真实 T0→T5 fit，再继续 H504 MLP/TCN 与消融；没有合法折就明确 `BLOCKED_PROTOCOL_H504` 后做 AUX_REAL_HISTORY，但不能拿 AUX 数字冒充长期四倍任务。
4. 每个模型必须保存 checkpoint、完整预测、TP/signals/precision/recall/base-rate/lift、Brier/logloss/AP、逐折与时间块结果；若最好时间外 precision <50%，明确写 `TARGET50_NOT_REACHED`，不要再用“又发现一个P1”替代模型结果。

## 前一版索引（不可变保留）

[截至 `e0fd2ba46b0ad1f55e0dfdf3d5ea4887a785c15c` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/e0fd2ba46b0ad1f55e0dfdf3d5ea4887a785c15c/docs/audits/expert-ml/LATEST.md)。

历史审计 Markdown 未删除。旧状态按各自固定 SHA 与审计时点解释。
