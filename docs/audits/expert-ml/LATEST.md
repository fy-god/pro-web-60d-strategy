# 专家 / ML 最新轮审

## 最新研究执行方案：贯通研究批次 v2

- 完整任务书：[`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)
- `publication_kind`：`EXECUTION_PLAN_UPDATE`，不是一次新的全仓模型审计或市场训练结果。
- `audit_time_jst`：`2026-09-20T02:04:16+09:00`
- 本次执行链核验源码：`32155ecae1a0a0be1877b780df0da12354c347ea`
- 任务书发布提交：[`5c1e5c5a5444b94aecfd03759638412faa94c5c1`](https://github.com/fy-god/pro-web-60d-strategy/commit/5c1e5c5a5444b94aecfd03759638412faa94c5c1)
- 文件blob：`9935f12f8285f808a00cebdc0f8707b1491ff17d`。
- 首批ID：`EML-EXP-KDJ-PATH-001-REAL`；接续X17/X18，SEQ与CR用子实验。
- 云端现有专家／ML任务已更新，JST 01/05/09/13/17/21时段不变；本地提示词／launcher候选尚需用户授权的本地执行器接入，不宣称用户机器已经开始训练。
- 新终点：真实数据与协议→因子实现/调试→M1—M3配对训练→M4快照MLP/M5因果TCN→必要消融→一次有依据的错误驱动再训练→独立校准/发布账本/可复算指标。
- 接续机制：相同报告下仍有READY/INTERRUPTED任务就续跑；不再仅按last_processed直接结束。单次最多75分钟，整批累计180分钟/48次实际fit跨轮续算；不是要求耗满时间。
- 本次沙箱候选23项测试通过，包含量压32组合、因子/TCN前缀、梯度与重载、累计预算、launcher失败退出及临时Git补丁应用；仅软件测试，没有实股训练结果。
- 依赖策略调整：G0隔离安全、G1本实验有效性、G2发布认证分别处理。下文旧审计的发布安全问题继续开放，但G2不能无限阻断通过G0/G1的隔离开发研究；不因CR未完成拖延首批M1—M5。

## 最近一次完整源码审计（保留原索引记录）

以下各节保留2026-09-19 22:04审计的证据和开放问题；“本轮”“当前”均指该次审计，不代表本次重新穷尽验证。新的本地执行顺序以上述v2任务书为准，最后成功源码审计指针不因计划更新被替换。

- 完整报告：[`2026-09-19_22-04-07_JST.md`](./2026-09-19_22-04-07_JST.md)
- `audit_time_jst`：`2026-09-19T22:04:07+09:00`
- `reviewed_source_sha`：`82aefeb583ac6f039cc67ae2582c30803fc7cb32`
- `reviewed_tree_sha`：`a619e1ef75ae8fd97bd0cbd3c814b886cb9285b9`
- 上一份本对话成功审计源码：`318fb47db474195176d101d32dad82bcea11d4e9`
- 报告发布提交：[`3dbaa67e00b3bdbaff8828b6d3ce6b68b73ffa31`](https://github.com/fy-god/pro-web-60d-strategy/commit/3dbaa67e00b3bdbaff8828b6d3ce6b68b73ffa31)
- 报告文件 Git blob：`eb17bd1f1f5d7c80fa1eec62a267ec5d8ce6c49c`；已按发布提交回读核验。
- 当前 open PR：0。
- 本轮没有市场模型重训、远程训练、交易或收益验证；审计文档提交不代表模型升级。

## 本轮真实增量

上一审计源码 `318fb47...` 之后没有新的标签、特征、训练、校准、ledger 或模型实现提交；后继提交只有上一轮审计报告、索引和定时 `AUDIT_STATUS`。因此上一轮模型问题不能因 HEAD 变化自动视为已修。

本轮最大新增确认错误位于报告认证链：当前 `reports/AUDIT_STATUS.md` 同时写着 `PASS / 629 checks / 0 problems` 和 `Remote drift = 2 path(s)`。源码显示 `scheduled_report_audit.py` 只 fetch+diff，不同步本地 HEAD，就在旧工作树运行 checker；status push 失败后才 rebase 到新远端，且 rebase 后不重新运行 checker。独立临时 Git 反例已复现“旧树 PASS -> rebase 新失败report -> 最终远端仍 PASS”。

## 新增确认与风险

- `EML-P0-AUDIT-STALE-ATTEST`【P0，新增确认】：PASS 没有绑定最终发布树；remote 在审计后变化时，旧 PASS 可以被 rebase 后发布到新树。应在 detached/frozen `AUDITED_SHA` 上检查，并在发布前确认 remote HEAD 未变化；否则废弃并重跑。
- `EML-P1-AUDIT-DRIFT-PASS`【P1，新增确认】：`write_status()` 的 `ok = code == 0 and not unstable` 忽略 `changed`，所以有 remote drift 仍可显示 PASS；应显式区分 PASS / FAIL / STALE / UNSTABLE。
- `EML-P1-AUDIT-PUSH-SCOPE`【P1，静态风险】：首次 `git push origin HEAD:main` 仍可能夹带预先存在的本地 ahead commit；当前未确认发生。建议 status publisher 从 frozen remote SHA 生成单一白名单提交。
- `EML-P0-FIXUP-SYNC-FAILOPEN`【P0，持续未修】：`run_fixup.py` 丢弃 fetch 返回码、rebase失败只记日志，随后仍可启动 `danger-full-access` agent。
- `EML-P1-FIXUP-REMOTE-ACK`【P1，新增确认缺口】：fixup 的 `last_processed.txt` 与日志位于被忽略的 `logs/`；最新报告后没有产品源码 commit，远端只能知道“没有修复提交”，不能判断任务没运行、失败、NO_NEW_REPORT、无法复现或无代码变化。

## 继续开放的模型／评估问题

当前固定 HEAD 已重新读取，以下仍未修：

- `EML-P0-H504-HIGH-CLOSE`：`low504` 仍按未来 High 严格超过 4E，不是主目标 Close>4E。
- `EML-P0-SESSION-ALIGN`：entry 与 horizon 仍按下一条／后续个股bar，不是独立 market session。
- `EML-P0-YEAR-KNOWN-AT`：年度训练／历史阈值评分仍缺逐行 `label_end/known_at`。
- `EML-P0-KNOWN-AT-GAP`：holdout 的 market-session purge 近似与实际个股bar标签时钟不一致。
- `EML-P0-ML-COHORT`：cross-sectional 评分前按未来标签完整性删test row，未来未知高分股可被删除并让下一名补位。
- `EML-P0-LEDGER-ORDER`：`score_signals()` 先删 unresolved 再 dedupe，未来完整性可改变历史第一事件。
- `EML-P0-COOLDOWN-GRID`：cooldown 时钟从 signal dates 重建，目标股票去重可依赖其他股票信号。
- `EML-P1-DOWNVOL-EMPTY`：五日 down/up 互斥分组各 `min_periods=3`，`down_vol_ratio5` 无法形成有效混合窗口比值。
- `EML-P1-ZERO-SIGNAL-BASE`：`summarise()` 删除0信号fold后再算候选自然基率。
- `EML-P1-RULE-SHAPE`：深回踩和大gap仍会因clip获得与温和形态相同的满分。
- `EML-P1-FRONTIER-TIES`：同分组内部前缀仍被当成 scalar threshold operating point。

已修控制继续保留，不重复报为未修：严格 target 比较器一致、scan/baseline selection mask 共用、Close 标签原始 float64 entry boundary 修复。

## 主改造与实施顺序

本轮主改造升级为 **Attested Causal Research Pipeline**：先把报告checker和fixup发布链绑定到不可变SHA，再推进 `joint_close4x_H504_low80_v1` + discrete-time competing-risk causal stack。

实施顺序：

1. **WP0 `scheduled_report_audit` frozen-SHA attestation**：修 stale PASS、统一 verdict、白名单单提交发布。
2. **WP1 fixup fail-closed + deterministic release gate**：agent只产diff+manifest，launcher做path/tests/audit/commit/push gate。
3. **WP2 TaskSpec / market calendar / PIT / provenance**。
4. **WP3 label + `known_at` 单一真源**。
5. **WP4 低位机制、量压、专家家族**。
6. **WP5 固定候选总体 + 真正 OOF + H504 competing-risk**。
7. **WP6 独立校准 + 因果 publication ledger**。
8. **WP7 计数、event Recall、依赖不确定性、正确 scalar frontier**。
9. **WP8 release manifest + clean-SHA attestation**。

## 下一优先实验

继续 `X18-H504-CR-KDJ-PATH`，不因没有新市场结果而人为换编号：在同一冻结 H504 Close/Low 候选总体下比较 KDJ+position、all-raw HGB、修复量压、competing-risk hazard、OOF expert family、OOF meta；加入 drop-KDJ / drop-position / drop-pressure、raw-vs-clip、负控制、多种子和预定义未见股票组。只有 WP0–WP3 基础契约通过且 H504 时间预算足够后才开展。

备选仍为 `X19-Residualized-Cross-Section`、`X20-Expert-Quality-Gate-Residual`。

## 当前归档结果边界

- H10 / +30% / High RF 开发 walk-forward：`4765 / 22867 = 20.8379%`，pooled base `4.089445%`，4/4 folds above base。
- H10 / +30% / High 2026 historical holdout：`844 / 6202 = 13.6085%`，base `2.8958%`，1194 stocks、150 signal dates，归档 date-clustered 95% 约 `[10.24%, 17.59%]`；该区间有 prior project exposure，不是 pristine lockbox。
- 当前 H504 / Close / Low 联合目标仍没有可认证的 TP／发布分母、自然基率、event Recall、未知／不可执行数、校准或 cluster-aware interval。
- 当前 `629 checks / 0 problems` 只能作为报告一致性 checker 的归档输出；本轮已确认其 PASS 尚未可靠绑定最终发布SHA。

## 前一份本对话报告

- 报告：[`2026-09-19_18-00-42_JST.md`](./2026-09-19_18-00-42_JST.md)
- `reviewed_source_sha`：`318fb47db474195176d101d32dad82bcea11d4e9`
- 报告发布提交：[`7711b4635eb07951d3c50243c340787e036d64f4`](https://github.com/fy-god/pro-web-60d-strategy/commit/7711b4635eb07951d3c50243c340787e036d64f4)

## 更早本对话报告

- [`2026-09-19_04-05-29_JST.md`](./2026-09-19_04-05-29_JST.md)，`reviewed_source_sha=0df81c65a5a2765027d6447c3cf24e4760e0c5e8`。
- [`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)，`reviewed_source_sha=14a2e834985248029f23750b80782c9fa5b36f12`。

> 本索引严格区分：被审计源码SHA、审计报告发布commit、索引commit、定时status commit和后续fixup代码commit。审计文档提交不代表模型升级；软件反例不等于市场精确率提升。完整证据、工作包、对照矩阵和可复制agent执行段见最新完整报告。
