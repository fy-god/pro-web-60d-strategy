# 专家 / ML 最新轮审

## 最新研究执行方案：贯通研究批次 v2

- 完整任务书：[`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)
- `publication_kind`：`EXECUTION_PLAN_UPDATE`，不是一次新的全仓模型审计或市场训练结果。
- `audit_time_jst`：`2026-09-20T02:04:16+09:00`
- 本次执行链核验源码：`32155ecae1a0a0be1877b780df0da12354c347ea`
- 任务书发布提交：[`5c1e5c5a5444b94aecfd03759638412faa94c5c1`](https://github.com/fy-god/pro-web-60d-strategy/commit/5c1e5c5a5444b94aecfd03759638412faa94c5c1)
- 文件 blob：`9935f12f8285f808a00cebdc0f8707b1491ff17d`。
- 首批研究 ID：`EML-EXP-KDJ-PATH-001-REAL`；接续 `X17-KDJ-PRESSURE-PATH` / `X18-H504-CR-KDJ-PATH`，SEQ 与 CR 使用子实验。
- 新工作终点：真实数据与协议 → 因子实现/调试 → M1—M3及单项对照 → M4快照MLP / M5因果TCN → 必要消融 → 一次有依据的错误驱动再训练 → OOF/meta/CR → 独立校准/发布账本/可复算指标。
- 相同报告已经处理不等于研究结束：registry 中仍有 `READY/INTERRUPTED`、可恢复 checkpoint、待消融或待错误切片时继续推进；只有没有新报告、没有未完成队列、没有新数据/环境变化时才 `NO_NEW_WORK`。
- 单次本地研究上限建议 75 分钟，整批累计 180 分钟 / 48 次真实 fit 跨轮续算；上限不是必须耗满的目标。
- 该任务书记录的 23 项候选软件测试属于其独立沙箱执行结果，不是 H504 实股训练或正式神经网络比较；本索引不把它改写为市场成绩。

## 最近一次完整源码审计＋研究推进

- 完整报告：[`2026-09-20_02-00-47_JST.md`](./2026-09-20_02-00-47_JST.md)
- `publication_kind`：`AUDIT_AND_EXECUTION_PLAN_UPDATE`
- `audit_time_jst`：`2026-09-20T02:00:47+09:00`
- `reviewed_source_sha`：`32155ecae1a0a0be1877b780df0da12354c347ea`
- `reviewed_tree_sha`：`fba9afc0b6083b1099850e60280ffee0d4e2aefc`
- 上一份成功源码审计：`82aefeb583ac6f039cc67ae2582c30803fc7cb32`
- 报告发布提交：[`8dafee50ef084cf7398373b62790888e5b6faeaa`](https://github.com/fy-god/pro-web-60d-strategy/commit/8dafee50ef084cf7398373b62790888e5b6faeaa)
- 报告文件 Git blob：`4143fae7c47dc915ef9b58f0a93b3a2f40896f26`；已按发布提交回读核验。
- 当前 open PR：0。
- 本轮没有市场模型重训、远程训练、交易或收益验证；审计文档提交不代表模型升级。

### 本轮新增确认

- `EML-P0-AUDIT-FETCH-FAIL-PASS`【P0】：当前已发布 `reports/AUDIT_STATUS.md` 实际同时记录 `PASS / 629 checks / 0 problems` 与 `git fetch failed (exit 1): incorrect old value provided`。`scheduled_report_audit.py` 把 fetch 失败折叠成空 `changed` 列表与文本 note，顶层 PASS 只看 checker exit 和 unstable，因此同步失败仍可认证 stale local tree。修复要求 frozen `AUDITED_SHA`、同步失败直接 `SYNC_FAILED`，远端变化则 `STALE`，不得 PASS。
- `EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`【P1】：当前 `scripts/fixup_prompt.txt` 仍以“最新报告→只修 P0/P1→同报告已处理则 `NO_NEW_REPORT`”为唯一工作合同，不读取 experiment registry、checkpoint、待消融预测或未完成训练队列；这是本地 agent 工作量过小的直接控制面原因。
- `EML-P1R-H504-TEMPORAL-SUPPORT`【P1风险/研究约束】：当前 dense H10 元数据只有 887 market sessions；单看日历，H504 完整随访最多约剩 383 个成熟 decision sessions，若再要求 60 日历史 warm-up，上界约 324，真实支持还会被停牌、no-entry、缺bar和价格口径继续削减。必须先产出 `fold_support.json`，不能把 H10 folds 机械改为 H504，也不能缩短 horizon 凑折。

### 本轮审计沙箱状态

- GitHub 源码与机器结果读取、报告写入和索引更新成功。
- 当前审计沙箱的 container/Python 执行工具在启动层返回 `ClientError`，因此本轮没有把合成 smoke、pytest、HGB/MLP/TCN fit 冒充成已执行；状态为 `BLOCKED_ENV`。
- 该限制不证明用户本机 `D:\ccc\pro-web-60d-strategy` 缺数据或缺 PyTorch。真实训练应由本地执行器读取授权数据路径后登记到 `experiment_registry.jsonl`。

## 第一批研究矩阵

`EML-EXP-KDJ-PATH-001-REAL` 在第一个合法 H504 开发折、seed 17 的起始队列：

1. `M0`：自然基率常数，不计 fit。
2. `M1`：KDJ + 长期位置 Logistic。
3. `M2`：纠错后的 snapshot HGB。
4. `M2P`：M2 + repaired pressure only。
5. `M2K`：M2 + KDJ-path only。
6. `M3`：M2 + KDJ-path + pressure HGB。
7. `M4`：snapshot MLP `64→32→1`。
8. `M5`：128-market-session causal TCN + 同 snapshot branch；width 32、kernel 3、6 个双卷积残差块、dilation 1/2/4/8/16/32，理论 receptive field 253 sessions。

首轮只跑一个合法 dev fold；支持、预算和错误分析允许时再扩 3 folds、seed 17/29/43。保留 2—4 fits 给错误驱动的配对再训练。`48 fits` 是整批累计上限，不是 48 configs × 3 seeds × 3 folds。

## 当前继续开放的模型／评估问题

当前固定源码已重新读取，以下仍未修：

- `EML-P0-H504-HIGH-CLOSE`：旧 `low504` 仍按未来 High 严格超过 4E，不是主目标 Close>4E。
- `EML-P0-SESSION-ALIGN`：entry 与 horizon 仍按下一条／后续个股 bar，不是独立 market session。
- `EML-P0-YEAR-KNOWN-AT`：年度训练／历史阈值评分仍缺逐行 `label_end/known_at`。
- `EML-P0-KNOWN-AT-GAP`：holdout 的 market-session purge 与实际个股-bar标签时钟不一致。
- `EML-P0-ML-COHORT`：cross-sectional 评分前按未来标签完整性删 test row。
- `EML-P0-LEDGER-ORDER`：`score_signals()` 先删 unresolved 再 dedupe。
- `EML-P0-COOLDOWN-GRID`：cooldown 时钟从 signal dates 重建。
- `EML-P1-DOWNVOL-EMPTY`：五日 down/up 互斥分组各 `min_periods=3`，旧 `down_vol_ratio5` 无法产生有效混合窗口比值。
- `EML-P1-ZERO-SIGNAL-BASE`：`summarise()` 删除 0-signal fold 后再算候选自然基率。
- `EML-P1-RULE-SHAPE`：深回踩和大 gap 仍会因 clip 获得与温和结构相同满分。
- `EML-P1-FRONTIER-TIES`：同分组内部 prefix 仍被当成 scalar-threshold operating point。
- `EML-P0-FIXUP-SYNC-FAILOPEN`：fixup fetch/rebase 失败仍可启动 full-access agent。
- `EML-P0-AUDIT-STALE-ATTEST`：checker PASS 尚未与最终发布树原子绑定。
- `EML-P0-AUDIT-FETCH-FAIL-PASS`：同步失败仍可顶层 PASS。

已修控制继续保留，不重复报为未修：strict target 比较器一致、scan/baseline selection mask 共用、Close 标签 raw float64 entry boundary 修复。

## 当前归档结果边界

- H10 / +30% / High RF 开发 walk-forward：`4765 / 22867 = 20.8379%`，pooled base `4.089445%`，4/4 folds above base。
- 当前 dense H10 matrix 元数据：`2,680,715` rows、`3,193` stocks、`887` sessions、82 features；High base `3.08934%`，Close base `2.02919%`。
- 旧 `low504` 的归档 bull rate 约 `4.21%` 仍来自 High-based、个股-bar时钟任务，禁止当作新 H504/Close/market-session 主任务自然基率。
- 当前真正 H504 / Close / Low 联合目标仍没有可认证的 TP／发布分母、自然基率、event Recall、unknown/no-entry、校准或 cluster-aware interval。

## 上一份完整源码审计

- [`2026-09-19_22-04-07_JST.md`](./2026-09-19_22-04-07_JST.md)
- `reviewed_source_sha=82aefeb583ac6f039cc67ae2582c30803fc7cb32`
- 报告发布提交：[`3dbaa67e00b3bdbaff8828b6d3ce6b68b73ffa31`](https://github.com/fy-god/pro-web-60d-strategy/commit/3dbaa67e00b3bdbaff8828b6d3ce6b68b73ffa31)

## 更早本对话报告

- [`2026-09-19_18-00-42_JST.md`](./2026-09-19_18-00-42_JST.md)，`reviewed_source_sha=318fb47db474195176d101d32dad82bcea11d4e9`。
- [`2026-09-19_04-05-29_JST.md`](./2026-09-19_04-05-29_JST.md)，`reviewed_source_sha=0df81c65a5a2765027d6447c3cf24e4760e0c5e8`。
- [`2026-09-19_03-00-00_JST.md`](./2026-09-19_03-00-00_JST.md)，`reviewed_source_sha=14a2e834985248029f23750b80782c9fa5b36f12`。

> 本索引严格区分：最新研究执行方案、最近一次完整源码审计、审计报告发布 commit、索引 commit、定时 status commit 与后续本地 fixup/research code commit。审计文档提交不代表模型升级；候选软件测试不等于市场训练；H10 结果不替代 H504/Close/Low 证据。完整工作包、本地执行器替换提示词和验收队列见上述两份 2026-09-20 报告。