# 专家／ML最新研究与审计索引

## 最近一次独立复核（本轮，2026-09-20 23:50 JST）

- 完整报告：[`2026-09-20_23-50-06_JST.md`](./2026-09-20_23-50-06_JST.md)。
- 类型：`INDEPENDENT_REGRESSION_AND_NEW_REPORT_VERIFICATION`。
- 被审源码：`91726c9f14edf6047e531a53e71df359fb1ffd60`；tree：`56945a5f28b390613b850200c0cfc98f35a7f69d`。
  （本轮起点 `main_head_at_audit_start` = `908a41334eaf2f38570a7fb93954a63ebb80ad52`。）
- **本轮最重要的升级**：`EML-P0-AUDIT-FETCH-FAIL-PASS` 从「仍 OPEN」升级为
  **`已确认错误`，且已在真实生产运行中实际发生并发布过错误结论**。
  `scripts/scheduled_report_audit.py:108` 的 `ok = code == 0 and not unstable` **从不读取 `note`**，
  而 `git fetch` 失败恰在 `:86` 只以 `note` 返回 → 「**无法比较**」被发布成「**比较后一致**」的
  `Verdict PASS`（fail-open）。真实发布提交 `32155ec`（HEAD 祖先）的 `reports/AUDIT_STATUS.md`
  **同时**写着 `Verdict **PASS**` 与 `Remote drift | git fetch failed (exit 1)`；
  `3d1488f` 记录 `exit 124 TIMEOUT` **同样配 PASS**。我已用真实不可达 remote
  （真实 fetch 退出码 **128**）只读复现出同一个 PASS。
  `--dry-run`（`:82-83`）与 fetch 失败**同构**，是第二入口。
  `:344`/`:376` 同样忽略 fetch 失败 → 已提交文件、FINDINGS、stdout、退出码四个通道全无痕迹。
- **本轮无产品源码变更**：`cb785b8 → 91726c9` 的唯一非 `docs/audits/` 改动是自动生成的
  `reports/AUDIT_STATUS.md`（4 行时间戳）。故本轮是**校验上轮描述的准确性**，而非判断「是否已修」。
- **上轮（`19:47`）量化声称抽样复算，准确率很高**：RSI 截断 **9/9 项精确一致**
  （真实 `data/cards_100/cards.json`：rsi14 min/mean/max = 42.2246/67.3807/100.00、
  score = 0.0354/0.2095/0.4926、fires = 0/100）；`webpro_hit_rates.csv` **16/35** 行是克隆
  （源码 16 个文件声明 `BASE_STRATEGY_ID`，涉及 **11** 个 base）→ **精确一致**；
  cooldown 反例（真实相隔 **90** 市场会话只留 **1** 条，`positions` 差 = **1**）**独立复现**。
- **本轮新登记**：
  - `EML-P2-CONCURRENT-SANDBOX-CAPABILITY-CONTRADICTION`（`待验证风险`）：
    并发两份新报告（`22:00:19` 与 `22:10:00`，提交相隔 **10 分钟**）对同一沙箱能力
    **陈述互斥**——前者称 `ClientError`/`NOT_RUN_BLOCKED_ENV`，后者称「沙箱能执行 Python」
    并跑通 30 项 pytest。**我无法判定孰真**，也**不**把「30 项 pytest」当作可核验事实
    （仓库内 `tests/` 只有 `test_engine.py`，实跑 **`15 passed in 1.03s`**）。
- **r2 追加（第 4 个子 agent B 返回后，逐条亲自复核）**：
  - **`EML-P2-TEST-KDJ-NESTED` 恢复为 `已确认错误`**。`tests/test_engine.py:306` 是**裸字符串表达式
    （不是 `def`）**，故 `306-319` 整块掉进 `test_wilson_upper_bound_is_not_a_constant`（`:268-319`）尾部
    → KDJ 断言**确实执行但没有独立 test id**。**`19:47` 报告把它与「KDJ 从不执行」合并后
    一并降级为「未复现」是降级过头。**（我已亲自读源码确认结构；双向变异测试证明断言执行。）
  - **新登记 `EML-P2-COOLDOWN-COUNT-NOT-REPRODUCIBLE`**：`19:47` 报告 §4 `L180-181` 的
    「帧内时钟保留 **8** 条 / 市场时钟保留 **29** 条」在它**自己引用的 `cooldown=60`** 下
    **算术不可能**——`N=955` 时上界 = `floor(954/60)+1` = **16 < 29**；
    我穷举 `stride 1..29 × cooldown 5..120` 网格，命中 (8,29) 的组合 **0** 个。
    **仅否定该两个数字，不否定 cooldown 缺陷本身**（其最小反例：真实相隔 90 会话只留 1 条，
    我已独立复现）。
  - `EML-P1-RSI-META-LEAK` **名实不符**：`rsi_meta` 全仓 **0 命中**，它是 `03:06` 报告起的
    **计划代号**，机制实体即 `src/ml/walkforward.py:58-61,109`（与 `META-BLACKLIST-H10-NAMES` 同根因）。
  - 路径笔误：`19:47` 报告 §5.3 的 `live_readiness.py:155` 实为 **`src/live_readiness.py:155`**。
  - 子 agent B 已完成（`eml_h22_B\REPORT.md`，44.8 KB）：10 项回归中 **7 项确认仍成立、0 项已修**；
    `cb785b8..HEAD` 对 `src experts tests scripts` **零 diff**（源码 blob 逐位相同）。
    其未能验证项：`panel_daily.parquet` 与 `webpro_signals.csv` **gitignored 且不在冻结树**，
    故 entry 实股计数与 pooled 去克隆均值移动量**未能复算**。
- **对两份并发新报告的核验**：全部 SHA/blob/tree 为真（**14/14** hex token `cat-file -t` rc=0，
  **错误 SHA = 0**）；两份均**诚实标注**了「未验证/合同要求/实股 fit=0」，
  `COMPLETE_LOCAL_1H` **从未被冒用**，**未发现把要求冒充成绩**。
- **测试真数**：冻结树 `python -m pytest -o addopts="" -p no:cacheprovider -q tests/`
  = **`15 passed in 1.03s`**，exit **0**。
- 本轮**未**改任何源码/配置/权重/PR；**未**动任何定时任务；只上传本报告与本次索引。
  取证全部在只读冻结工作树完成，`status --porcelain` 前后为空。
  （以上计数与 SHA 属本次复核，**不**认证下方历史报告的成绩。）

## 最新本地执行合同：至少60分钟真实研究

- 完整任务书：[`2026-09-20_22-10-00_JST.md`](./2026-09-20_22-10-00_JST.md)
- 类型：`LOCAL_EXECUTION_CONTRACT_AND_CANDIDATE_TESTS`。这是执行要求修订、局部源码核验和候选测试，不替代下方最近一次独立审计。
- 固定核验源码：`908a41334eaf2f38570a7fb93954a63ebb80ad52`；tree：`34273d2bb4cf275036ae57770858463ed61721cc`。
- 报告发布时间标记：`2026-09-20T22:10:00+09:00`。
- 报告发布提交：[`7989703ae286cc006e8f2b0f7d9accf88ee21f1f`](https://github.com/fy-god/pro-web-60d-strategy/commit/7989703ae286cc006e8f2b0f7d9accf88ee21f1f)。
- 报告blob：`ee4de118b7b90a56c370abd54e67f9d907f2211a`；已按发布提交回读，与本对话完整附件字节的Git blob一致。
- 研究队列：`EML-EXP-KDJ-PATH-001-REAL / LOCAL-60M-01`，继续RSI/PDC/MEB，不重置旧实验或预算。

### 对本地执行者的最新要求

真实本地有效工作至少3600秒，其中真实数据训练至少1800秒，至少6个不同有效fit；单次最多4500秒及18个新fit，同时服从外层剩余时间和已确认总预算。不把LLM思考、写Markdown、Git提交、网络重试等待、合成训练或多核累计CPU秒计入一小时。没有达到就如实报告，不sleep或重复计算凑时。

八包顺序：真实数据/更早历史→H504资格→全量因子与专家分量→真实分层诊断→六组HGB→MLP/TCN→错误驱动配对修改→台账和实测执行收据。同报告下有READY/INTERRUPTED或待分析预测必须继续，不以“修完一个P0/P1”结束。

H504合法成熟时间外折缺失时，阻塞H504成绩认证；真实行情仍可进入明确独立的历史自监督TCN研究。该分支不改主目标，也不证明H504效果。不同目标结果严禁混报。

本轮沙箱实际完成30项候选测试、6次人工HGB接口拟合、MEB冻结ECDF及观测/收据校验代码。全部拟合为SYNTHETIC，实股fit=0，用户本机未由本对话启动，一小时本地执行尚未完成。代码包通过本对话附件交付；仅有文档提交不能证明本机接入。

## 并发新增方案（保留，纳入同一队列）

- [VIR量价冲击恢复与60—75分钟执行方案](./2026-09-20_22-00-19_JST.md)，时间 `2026-09-20T22:00:19+09:00`，发布提交 `5114bbc925ca32acd838fb972b9429f41098b69a`。
- 索引更新时两次条件写入返回409；已读取并发VIR方案和后继SHA纠正，保留其入口及完整历史归档，没有覆盖并发报告。
- VIR是该报告的候选假设，本次未验证其公式或效果。进入同一个experiment registry，不与本次任务重复启动重训练，不叠加预算。
- 当前v2的累计48 fits / 180分钟仍需扣除已用量；本次18个新fit/75分钟只是切片上限，不能在两份并发报告各领一份总预算。

## 最近一次独立复核（保持原指针，不被执行计划替代）

- 完整报告：[`2026-09-20_19-47-00_JST.md`](./2026-09-20_19-47-00_JST.md)。
- 类型：`INDEPENDENT_REGRESSION_AND_NEW_REPORT_VERIFICATION`。
- 被审源码：`cb785b8983c2ae3a21e049d74cbff46c462e3901`；tree：`a7ee77503039a14bd15ed17f1d4c1d42703d6991`。
- 报告提交：[`bb5c7326096808919713c1df3665c6a41a09d097`](https://github.com/fy-god/pro-web-60d-strategy/commit/bb5c7326096808919713c1df3665c6a41a09d097)。
- 该报告中的测试、实股统计、自我纠正、开放问题与执行限制属于该次复核，本次不重新认证，不作为本次训练成绩。

## 主研究与此前审计

- [MEB机制家族融合任务](./2026-09-20_18-03-00_JST.md)。
- [独立回归与实股影响核查](./2026-09-20_15-34-32_JST.md)，被审源码保留为已纠正的 `c9b90e37f68c0415331ca61e4e8acc3b13ce0bdf`。
- [H504合同与回归测试审计](./2026-09-20_13-57-11_JST.md)。
- [RSI归因及恢复共识研究](./2026-09-20_09-58-00_JST.md)。
- [RSI连续信息专项](./2026-09-20_06-02-02_JST.md)。
- [RSI新增/滚出分解](./2026-09-20_03-06-03_JST.md)。
- [贯通研究批次v2](./2026-09-20_02-04-16_JST.md)。

## 完整历史索引归档

为避免把历史审计的“当前”与本次执行要求混为一谈，历史长索引完整保存在以下固定提交，原报告没有删除或覆盖：

[本次更新前完整LATEST：含全部历史链接、开放问题、计数纠正和事故记录](https://github.com/fy-god/pro-web-60d-strategy/blob/c37e7bd31bea1cbb418f32f70a3521d82a97e7c5/docs/audits/expert-ml/LATEST.md)

该历史索引blob为 `eced518fb10fe250eedcd9d219f03f209d4f3474`。后续独立审计继续从其开放项接续；本次仅收紧本地工作验收，没有把任何模型错误标为已修，也没有修改排程、源代码、权重、配置、Actions或其他项目。
