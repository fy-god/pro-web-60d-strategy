# 专家 / ML 最新轮审

## 最新独立复核：`06-02-02` 的 RSI 二值专家 0/100 经离线重算坐实

- 完整报告：[`2026-09-20_07-26-54_JST.md`](./2026-09-20_07-26-54_JST.md)
- `publication_kind`：`INDEPENDENT_RECHECK`。这是**独立复核报告**，不替代下方专项研究与执行方案。
- `audit_time_jst`：`2026-09-20T07:26:54+09:00`
- `reviewed_source_sha`：`8cadbd2a0210b2e2cfa475fb4a60ef46f3ed7155`
- `reviewed_tree_sha`：`46886f7af77e96a3438bb1d4b9c38658c25d3b9e`（`git rev-parse HEAD^{tree}` 实测）
- 本轮实际运行：`git merge --ff-only origin/main`（`efb6e1a..8cadbd2`，exit 0）；`python -m pytest tests/ -q -p no:cacheprovider` → **15 passed, exit 0**；仓库根同样 **15 passed, exit 0**（无计数差异）；离线重算 100 卡；矩阵列数核验；H504 算术复算。**本轮未复制上游报告的 `BLOCKED_ENV`**——本机 Python 与 pytest 均正常执行。
- 源码层自 `32155eca` 起无任何变更（其间提交全为 `docs/` 与 `reports/AUDIT_STATUS.md`），故四条开放项按回归处理、不重复展开。
- **独立重算坐实该报告核心声明**：用仓库**真实实现**（`ExpertCard.from_mapping` + `rsi_mean_reversion.predict`）重算 100 张真实卡 → `predicted_yes_count=0`，与归档 `scores.json` **一致**；`score min/mean/max = 0.0354 / 0.2095 / 0.4926`，距阈值 `0.68` 差 **0.1874**。归档算术对全部 36 策略自洽（`tp+fp+fn+tn=total=100`、`tp+fn=positive_count=50`、`accuracy=(tp+tn)/total`，0 处矛盾）。
- **本轮对该报告的加强（新增机制分离）**：失活是**两层原因叠加**，不是单纯阈值偏高。(a) `rsi_oversold`（权重 **0.30**，`rsi_mean_reversion.py:46`）在本归档上**结构性近乎失效**——仅 3/100 张卡 RSI14≤45、0/100 张 ≤25，该项均值 **0.0037**、最大 **0.1388**；(b) 阈值 `0.68` 偏高，而其余四项满额仅 `0.70`。**阈值扫描在 `0.68/0.60/0.55/0.50` 下均为 0 次触发**，直到 `0.49` 才 1 次 → 「从不触发」对该归档**稳健**，**仅调阈值无效**已数值排除。
- **定性维持**：策略实现与其自身 `FORMULA`（`:23-27` 对齐 `:59`/`:65`）一致，失活源于输入分布与阈值设计而非实现错误，故该报告「是研究发现、不是 P0/P1 代码 bug」可接受。36 个策略中 **6 个**预测为 0，RSI 是**离群者**。
- 四条开放项经独立回归**全部仍在**：`EML-P1-RSI-META-LEAK`（**潜在**泄漏）、`EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`、`EML-P2-LABEL-NOT-H504-CLOSE`、`EML-P2-PANEL-WRITE-SIDE-EFFECT`。
- **新增：绕过分组过滤的调用点比上轮多两处** —— `src/ml/precision_ceiling.py:109`、`src/ml/null_tests.py:67`（另有已报的 `final_holdout.py:222`、`concentration.py:56`、`validate_rf.py:72`、`profile_stages.py:28`；`crosssec.py:86` 为正确调用）。全仓库**无**白名单兜底（`git grep -E "FeatureSpec|WHITELIST|allowlist" -- src/` 为空），`tests/` 亦**无**覆盖；唯一相关守卫 `check_groups()` 仅打印 `WARNING`（`search.py:249-252`）。
- **`EML-P1-RSI-META-LEAK` 当前为潜在而非已泄漏**：两个真实矩阵均为 **91 列 = 82 特征 + 恰好 9 个 META 列**，无 `known_at`/`deadline`/`label_end`；82 特征与 `FEATURE_GROUPS` 并集精确相等。风险在未来追加时间合同列时兑现。
- H504 时间支持独立复算**与前两轮一致**：`564 / 382 / 1069`，`overlap=False` → 仅 887 会话下正式 H504 时间外验证应记 `BLOCKED_DATA/AWAITING_EVIDENCE`，**禁止**随机切分成熟历史。
- 状态三轴：`execution_status=COMPLETED`、`research_verdict=CONFIRMED`、`evidence_status=VERIFIED`、`evidence_type=SYNTHETIC`（`cards_100` 为 `evaluation.py:19-20` 硬构造的 50/50 练习集，非自然市场基率）。**本轮实股 H504 fit = 0，没有新增实股结果。**

## 上一份完整报告：RSI 连续信息融合与本地研究队列

- 完整报告：[`2026-09-20_06-02-02_JST.md`](./2026-09-20_06-02-02_JST.md)
- `publication_kind`：`AUDIT_AND_RESEARCH_QUEUE_UPDATE`
- `audit_time_jst`：`2026-09-20T06:02:02+09:00`
- `reviewed_source_sha`：`efb6e1a7718a5d540107db9c1f1557994f94f5e8`
- `reviewed_tree_sha`：`e9582078d611ff4349d960fe5fb33bda52a66d23`
- 报告发布提交：[`240e9d8258431d205a6651ba443bc687915f63af`](https://github.com/fy-god/pro-web-60d-strategy/commit/240e9d8258431d205a6651ba443bc687915f63af)
- 当前 open PR：0。
- 当前 `src` / `experts` / `tests` tree SHA 仍为 `c53a70dc...` / `b2f2d035...` / `6774c80f...`；上一轮后没有新的产品／模型源码提交，当前 HEAD 的新变化仍是 docs 与 `AUDIT_STATUS.md`。
- 本轮新实证来自仓库真实练习归档 `data/cards_100/scores.json`：`sample_count=100`、`positive_count=50`，而 `rsi_mean_reversion` 的 `predicted_yes_count=0`、`positive_recall=0`、`yes_precision=0`。这只说明该二进制 RSI 复合专家在该真实 card 归档上失活，**不是 H504 或自然市场精度结论**。
- 新研究子实验：`EML-EXP-KDJ-PATH-001-REAL/RSI-CONT-02`。不再以“RSI<30”或固定0.68阈值为主，而比较 `RSI14`、表面变化、fresh/new contribution、roll-out contribution、价格支撑破坏、ATR归一化破坏和可选 `RER_ATR` 交互；主要结论来自整组加入／移除后重新训练。
- 本轮把上一版 RER 的验证要求收紧：`N+E=ΔRSI` 是构造恒等式，不再计为预测性质；新增测试必须是可失败的真实历史／真实 card 诊断。
- 当前审计沙箱 Python/container 执行入口本轮返回 `ClientError`，因此没有冒称新增 pytest/HGB/MLP/TCN fit；实股 H504 fit 仍为0。下一步由本地 agent 实际推进 8 个工作包。

### 本轮本地执行顺序

1. **WP-RSI-01**：保存 HEAD/dirty，盘点本地更早历史并生成 `fold_support.json`；没有合法 H504 train→dev 时禁止随机切成熟历史。
2. **WP-RSI-02**：新增 RSI-Recovery Vector 与显式 FeatureSpec 白名单：`rsi14/delta/new/rollout/rollout_share/support_break_log/support_break_atr/RER_ATR`。
3. **WP-RSI-03**：在 `cards_100` 复现 RSI 复合专家 0/100 发布，再导出 raw score/component/RSI/RER 连续分量；只作机制 benchmark。
4. **WP-RSI-04**：完整真实历史统计 `ΔRSI3>0 && new3<=0` 的频率及 year/position/KDJ/volatility/liquidity 分层。
5. **WP-RSI-05**：若有合法 H504 时间折，固定 candidate/label/split/policy 跑 A—H 的 Logistic/HGB 归因；若无，标 `BLOCKED_DATA` 并改做 prospective ledger。
6. **WP-RSI-06**：只有表格模型显示稳定方向才跑 MLP/TCN RSI 增量，不为增加工作量扩网络。
7. **WP-RSI-07**：由开发 FP/FN 选一个机制做一次配对再训练；负结果记 `COMPLETE_NEGATIVE`。
8. **WP-RSI-08**：基础模型完成后再做真实 OOF/meta、独立校准、frozen policy 和 causal publication ledger。

预算继续占用主批次原有 `48 fits / 180 minutes` 账本，本 RSI 子实验建议最多使用其中 20 个真实 fit，不新开预算、不重跑同 hash 实验。

---

## 上一份独立复核：03-06-03 RSI 分解报告

- 报告：[`2026-09-20_03-41-46_JST.md`](./2026-09-20_03-41-46_JST.md)
- `reviewed_source_sha`：`5da1758e81d74f0dab42c7cdb21861e2caea4990`
- 报告发布提交：[`b18e081e8183378e465ca752a5e6a81b7d91710d`](https://github.com/fy-god/pro-web-60d-strategy/commit/b18e081e8183378e465ca752a5e6a81b7d91710d)
- 独立复核确认 RSI 滚出反例、RSI代数关系和 H504 时间支持算术；同时指出 `N+E=ΔRSI` 为望远镜式重言式、`research_h504` / `experiment_registry` 当时并不存在于远端，并加重 `EML-P1-RSI-META-LEAK`。
- 仓库测试归档：该轮在用户本地环境实际记录 `15 passed`；这不是本轮沙箱重新运行结果。

## 上一份 RSI 专项候选研究

- 报告：[`2026-09-20_03-06-03_JST.md`](./2026-09-20_03-06-03_JST.md)
- `reviewed_source_sha`：`ed8b6313cba278442eade24508a707e95f629c92`
- 报告发布提交：[`2ffd9a955c786452dcd0bb09f08efcfa671f55cd`](https://github.com/fy-god/pro-web-60d-strategy/commit/2ffd9a955c786452dcd0bb09f08efcfa671f55cd)
- 该轮的 44 项候选 pytest、HGB/MLP 合成接口 fit 属私有沙箱软件验证，不是远端仓库实现，也不是 H504 实股成绩。

## 主研究执行方案：贯通研究批次 v2

- 任务书：[`2026-09-20_02-04-16_JST.md`](./2026-09-20_02-04-16_JST.md)
- `publication_kind`：`EXECUTION_PLAN_UPDATE`
- 任务书发布提交：[`5c1e5c5a5444b94aecfd03759638412faa94c5c1`](https://github.com/fy-god/pro-web-60d-strategy/commit/5c1e5c5a5444b94aecfd03759638412faa94c5c1)
- 主批次：真实数据与协议 → 因子实现/调试 → M1—M3及单项对照 → M4快照MLP / M5因果TCN → 消融 → 错误驱动配对再训练 → OOF/meta/CR → 校准/发布账本。
- 相同报告处理过不等于研究结束；registry 中仍有 READY/INTERRUPTED、checkpoint、待消融或待错误切片时必须续跑。

## 最近一次完整源码审计＋研究推进（历史指针）

- [`2026-09-20_02-00-47_JST.md`](./2026-09-20_02-00-47_JST.md)
- `reviewed_source_sha=32155ecae1a0a0be1877b780df0da12354c347ea`
- 报告发布提交：[`8dafee50ef084cf7398373b62790888e5b6faeaa`](https://github.com/fy-god/pro-web-60d-strategy/commit/8dafee50ef084cf7398373b62790888e5b6faeaa)

### 继续开放、但不在本索引重复展开的核心项

- H504 主任务仍需 `Close>4E`、独立 market-session、next-session no-entry、不延期复牌；旧 `low504` High/个股bar结果不能替代。
- `label_end/known_at` 必须贯穿所有 fit/imputer/scaler/selection/OOF/meta/calibration。
- publication 必须先冻结 signal，再 join outcome/execution；unknown/no-entry 不得事后删信号或补位。
- `EML-P1-RSI-META-LEAK`：旧 ML 特征选择为黑名单式，新增 `known_at/deadline/label_end` 前必须改显式 FeatureSpec。
- `EML-P1-EXECUTOR-NO-RESEARCH-QUEUE`：远端 `scripts/fixup_prompt.txt` 仍是“新报告→修P0/P1→同报告即退出”的旧合同；任务书已发布不等于用户本机执行器已经接入研究队列。
- 887 market sessions 不足以形成先成熟训练、再成熟 H504 时间外开发的完整随访折；本地若无更早授权历史，正式 H504 OOS 标 `BLOCKED_DATA/AWAITING_EVIDENCE`。

> 本索引严格区分：审计源码 SHA、文档发布 commit、本地／沙箱软件测试、真实市场 fit 与最终认证。docs 提交不代表模型升级；cards_100、H10、合成数据或 in-sample 结果都不能冒充 H504/Close/Low 正式成绩。