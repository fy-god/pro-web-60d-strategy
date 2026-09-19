# 专家 / ML 最新轮审

## 最新报告

- 完整报告：[`2026-09-19_18-00-42_JST.md`](./2026-09-19_18-00-42_JST.md)
- `audit_time_jst`：`2026-09-19T18:00:42+09:00`
- `reviewed_source_sha`：`318fb47db474195176d101d32dad82bcea11d4e9`
- `reviewed_tree_sha`：`48f1d2d5c93131ecec9fa31f0855e867f459ae87`
- 上一份本对话成功审计源码：`0df81c65a5a2765027d6447c3cf24e4760e0c5e8`
- 报告发布提交：[`7711b4635eb07951d3c50243c340787e036d64f4`](https://github.com/fy-god/pro-web-60d-strategy/commit/7711b4635eb07951d3c50243c340787e036d64f4)
- 报告文件 Git blob：`28d26a1cc9201700e91ca96f476001d811fe380a`；已按发布提交回读核验。
- 当前 open PR：0。
- 本轮没有市场模型重训、远程训练、交易或收益验证；审计文档提交不代表模型升级。

## 本轮真实增量

从上一审计源码到本轮固定源码，关键标签／低位／ML文件 Git blob 均未变化；新增的实质代码主要是 `318fb47...` 引入的自动 fixup 执行链：`scripts/run_fixup.py`、`scripts/fixup_prompt.txt`、Windows 计划任务注册文件和两项 probe。该链路读取本目录最新报告后，让 headless agent 改码、验证、commit 并直接 push `main`，因此本轮把发布控制作为最大新增瓶颈。

本轮在隔离环境执行了 10 组软件／算术反例，不是市场训练：量压空列、cooldown 他股依赖、future-resolved 改变首信号、零信号折基率、market-session purge 与个股bar标签终点、fixup 同步失败控制流、dry-run 副作用、fixup 时刻漂移、规则评分形状、frontier ties。

## 新增确认与风险

- `EML-P0-FIXUP-SYNC-FAILOPEN`【P0，确认未修】：`scripts/run_fixup.py` 未检查 `git fetch` 返回码，`git rebase` 失败也只记日志；同步失败仍会启动 `danger-full-access` agent。下一步必须先改成 fail-closed，并在 rebase 失败时 abort，验证干净 base 后才能启动 agent。
- `EML-P0R-FIXUP-UNSCOPED-MAIN`【高风险设计】：生产 launcher 没有确定性 path allowlist / post-diff gate；当前安全边界主要依赖自然语言 prompt。建议 agent 只产本地 diff + `fix_manifest.json`，由 launcher 校验 base/report/issue/path/tests 后再 commit/push。
- `EML-P1R-FIXUP-STATE-NONTRANSACTIONAL`：`last_processed.txt` 与远端成功提交没有事务绑定；建议以远端回读后的结构化 commit trailer 为真源。
- `EML-P1R-FIXUP-PROMPT-CONTROL`：自由文本审计报告同时充当 full-access agent 控制输入；建议增加可验证 `auto_fix` schema，正文只作证据上下文。
- `EML-P2-FIXUP-DRYRUN-MUTATES`【确认】：`--dry-run` 在 fetch/rebase 之后判断，不是纯只读。
- `EML-P2-FIXUP-SCHEDULE-DRIFT`【当前配置漂移】：仓库 fixup 仍按旧专家/ML时段设计，相对当前本对话审计时点延迟约 3 小时 15 分，而非源码注释所称 1 小时。

## 继续开放的模型／评估问题

以下均已在本轮当前源码重新读取或用反例复核，不能因新增调度代码而视为已修：

- `EML-P0-H504-HIGH-CLOSE`：仓库 `low504` 仍以未来 High 严格超过 4E 判 bull，不是当前主任务的 Close>4E。
- `EML-P0-SESSION-ALIGN`：entry 与 horizon 仍按下一条／后续个股bar，不是独立 market session；停牌会改变 E 和截止日。
- `EML-P0-YEAR-KNOWN-AT`：年度训练与历史阈值评分仍缺逐行 `label_end/known_at` 隔离。
- `EML-P0-KNOWN-AT-GAP`：holdout 的 market-session purge 终点近似与实际个股bar标签器语义不一致，稀疏个股可跨界。
- `EML-P0-ML-COHORT`：横截面评分先用未来标签完整性过滤 test cohort，未来未知高分股可被删掉并让下一名补位。
- `EML-P0-LEDGER-ORDER`：`score_signals()` 先删 unresolved 再 dedupe，未来完整性可改变历史第一事件。
- `EML-P0-COOLDOWN-GRID`：cooldown 时钟仍从信号子集日期重建，目标股票去重结果会依赖其他股票是否发信号。
- `EML-P1-DOWNVOL-EMPTY`：五日 down/up 互斥分组各 `min_periods=3`，32 种五日组合均无法同时形成有限比值。
- `EML-P1-ZERO-SIGNAL-BASE`：`summarise()` 删除 0 信号折后再计算候选自然基率，模型行为可改变基率分母。
- `EML-P1-RULE-SHAPE`：-8% 与 -30% 回踩都满分；+6% 与 +20% gap 都满分，与文字定义不一致。
- `EML-P1-FRONTIER-TIES`：同分组内部前缀仍可能被算进“threshold frontier”，但标量 `score>=threshold` 实际不可实现该截断。
- `EML-P1-RESULT-SCHEMA`：当前 lowzone producer 已生成阈值来源／跳过年份／baseline population 字段，已发布 CSV 仍是旧 schema。

已修控制继续保留，不重复报为未修：严格 target 比较器一致、scan/baseline selection mask 共用、Close 标签原始 float64 entry boundary 修复。

## 主改造与实施顺序

本轮建议采用 `joint_close4x_H504_low80_v1` + discrete-time competing-risk causal stack。候选、Outcome、Publication、Execution 分表；H504 统一 market-session clock，risk-first；KDJ 保留并升级为路径状态，量压修复后作为新增信息；专家 raw component 与 quality/gate 分离，strict threshold clones 按 family 去重；二层只能消费真实 OOF；独立校准与 policy 冻结后一次 final test。

实施顺序：

1. **WP0 自动 fixup release gate**：先修 fail-open，再把 push 权限从自由 agent 收回到 launcher 的确定性验证层。
2. **WP1 TaskSpec / market calendar / PIT / provenance**。
3. **WP2 label + `known_at` 单一真源**。
4. **WP3 低位机制、量压、专家家族**。
5. **WP4 固定候选总体 + 真正 OOF**。
6. **WP5 H504 competing-risk + OOF meta**。
7. **WP6 独立校准 + 因果 publication ledger**。
8. **WP7 计数、event Recall、依赖不确定性、正确 scalar frontier**。
9. **WP8 版本 hash 与机器可读发布验收**。

## 下一优先实验

`X18-H504-CR-KDJ-PATH`：在同一冻结 H504 Close/Low 候选总体下，比较 simple KDJ+position、all-raw HGB、修复量压、competing-risk hazard、OOF expert family、OOF meta。加入 drop-KDJ / drop-position / drop-pressure、raw-vs-clip、负控制、多种子和预定义未见股票组。只有 WP0–WP2 基础契约通过且 H504 时间预算足够后才开展；新点子仍是待验证假设。

备选：`X19-Residualized-Cross-Section`、`X20-Expert-Quality-Gate-Residual`。

## 当前归档结果边界

- H10 / +30% / High RF 开发 walk-forward：`4765 / 22867 = 20.8379%`，pooled base `4.089445%`，4/4 folds above base。
- H10 / +30% / High 2026 historical holdout：`844 / 6202 = 13.6085%`，base `13809 / 476860 = 2.8958%`，1194 stocks、150 signal dates，归档 date-clustered 95% 约 `[10.24%, 17.59%]`；该区间有 prior project exposure，不是 pristine lockbox。
- 当前用户 H504 / Close / Low 联合目标仍没有可认证的 TP／发布分母、自然基率、event Recall、未知／不可执行数、校准或 cluster-aware interval，不能借用 H10 或 High 任务数字。

## 前一份本对话报告（历史保留）

- 报告：[`2026-09-19_04-05-29_JST.md`](./2026-09-19_04-05-29_JST.md)
- `reviewed_source_sha`：`0df81c65a5a2765027d6447c3cf24e4760e0c5e8`
- 报告发布提交：[`4bac1e79cbdcae2a4a21c6270ff93987ca94a13a`](https://github.com/fy-god/pro-web-60d-strategy/commit/4bac1e79cbdcae2a4a21c6270ff93987ca94a13a)
- 索引补传提交：`ba25883bd049cae11f3909e242b3148f6453733d`

## 更早仓库归档

- [`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)，`reviewed_source_sha=14a2e834985248029f23750b80782c9fa5b36f12`。

> 本索引区分审计源码SHA、审计报告发布commit与后续自动fixup代码commit。审计文档提交不代表模型升级；软件／算术反例不等于真实市场精确率提高。完整证据、10项反例、九个工作包和可复制agent执行段见最新完整报告。
