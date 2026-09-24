# 专家／ML线研究与审计索引

## 最新审计（2026-09-24 18:07 JST）：当前 H504 只评第一个合法 dev；相邻“第二折”默认重叠 62/63

- 完整报告：[`2026-09-24_18-07-23_JST.md`](./2026-09-24_18-07-23_JST.md)。
- 报告提交：`b83601035cb95dbb083ab85914b086a0c0167ae9`。
- 被审 `main` 起点：`aa7df5cf1253b989fa7df3fb1f56721534ddeb1a`；Open PR=0。
- 上一轮以后没有新的产品源码或模型产物提交；本轮只做源码审计、隔离软件复现和 docs 同步。
- 本轮真实 A 股 H504 fit 增量：**0**；`TARGET50_REACHED=NO`；`TARGET70_REACHED=NO`。
- 本机 runtime：**NOT_VERIFIED / LOCAL_APPLY_PENDING**；单次连续10800有效秒：**NOT_VERIFIED**。

### 本轮新增核心结论

1. **【P1 · 已确认】`EML-P1-H504-FIRST-LEGAL-SPLIT-ONLY-AND-SLIDING-OVERLAP-001`**：`train_h504.first_legal_split()` 直接返回 `enumerate_mature_splits(...).iloc[0]`，`run_h504_hgb()` 因而只训练/评价**最早的一个**合法 dev block；当前正式接口没有 fold id、第二 dev block 或 multi-fold evaluation。
2. `fold_support.enumerate_mature_splits()` 的 `dev_start_i` 每次只前进 1 个 market session。默认 `dev_block_sessions=63` 时，相邻两行 dev window **重叠 62/63 = 98.41%**。因此 WP7 的“第二合法开发块”绝不能实现为 `splits.iloc[1]`，否则只是同一时间块的滑窗伪复验。
3. 正式 fold plan 必须在打开预测前冻结，并要求 `next.dev_start_i > previous.dev_end_i + embargo_sessions`。若历史只支持一个独立 untouched dev，状态应是 `BLOCKED_PROTOCOL_H504_SECOND_BLOCK`，而不是拿相邻滑窗凑第二折。
4. 50%/70% 目标后续必须同时报告 **per-block + pooled** 的 `signals / TP / precision / recall / base rate / lift / AP / Brier / logloss`，零信号 block 也保留；不能用一个高 precision block 覆盖另一个失败 block。
5. 上一轮的 **train → calibration → untouched dev + frozen publication policy** 结论继续有效；本轮补的是跨时间的独立复验层。

### 本轮隔离候选

- `eml_auto20_h504_fold_plan_guard.zip`
- SHA-256：`0a9f21d8e2669edef17bcd620f2df590564820827decff1a4380f238d3881c67`
- 软件测试：**5 passed in 0.09s**。
- 覆盖：当前 first-split 行为、相邻滑窗重叠、H504 63-session 的 62-session 重叠、严格 non-overlap 选择、block 间 embargo。
- 该候选不写产品源码，不计48-fit，不计 real_train_seconds，不是市场成绩。

### 下一次真正有资格叫“模型进展”的证据

```text
真实 candidate/outcome ledger
冻结且不重叠的 fold plan
合法 train → calibration → DEV_A
若历史支持：独立 DEV_B（不与 DEV_A 重叠）
真实 checkpoint / full predictions
frozen_policy.json
per-fold + pooled TP / signals / precision / recall / base rate / lift
TARGET50_REACHED 或 TARGET50_NOT_REACHED
```

机器任务图必须把 T0-T5、MLP/TCN、消融和 error-driven refit 接到明确 fold id；不能修完一个问题、复用一个旧 signature 或跑完单个最早 dev 后就 `QUEUE_DRAINED`。

### 继续开放但本轮不重复展开

- tracked task template `PT2H30M=9000s < 10800s target`；
- `target_met=false` 仍不能阻止成功退出；
- evidence class 复用隔离不足；
- 完整 T1-T5 / MLP / TCN / ablation / error-driven queue 仍未产品化；
- observed-bar/calendar separation、risk-known/close-missing、oracle metadata gate、price basis 等 G1 项仍需真实训练前处理；
- frozen H504 publication policy 尚未接入产品源码。

## 上一版索引（不可变保留）

[截至 `aa7df5cf1253b989fa7df3fb1f56721534ddeb1a` 的上一版完整 `LATEST.md`](https://github.com/fy-god/pro-web-60d-strategy/blob/aa7df5cf1253b989fa7df3fb1f56721534ddeb1a/docs/audits/expert-ml/LATEST.md)。

上一份完整报告：[`2026-09-24_13-59-17_JST.md`](./2026-09-24_13-59-17_JST.md)。历史审计 Markdown 未删除；旧状态按各自固定 SHA 与审计时点解释。H10 历史结果只用于研究方法诊断，不得冒充 H504 成绩。
