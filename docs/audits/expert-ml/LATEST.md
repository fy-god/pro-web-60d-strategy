# 专家／ML线研究与审计索引

## 最新研究推进（2026-09-22 01:57 JST）：H504 executable candidate v5 —— candidate ledger 接入训练链，修三类“假可运行”证据风险

- 完整报告：[`2026-09-22_01-57-29_JST.md`](./2026-09-22_01-57-29_JST.md)。
- 类型：`CANDIDATE_IMPLEMENTATION_AND_EXECUTION_PLAN_UPDATE`；`REAL_MARKET_NEW_FIT=0`，不是新的H504实股成绩。
- 被审源码：`9bb1011d46a23718925bcab36f42d3494e71e060`；tree：`20958632f92e2dee6ad03dc9190031a51f74d2a0`；Open PR=0。
- 当前产品树仍没有 `src/ml/research_h504/`；`fixup_prompt.txt` 仍会对已处理报告直接 `NO_NEW_REPORT`，`run_fixup.py` 仍为5400秒硬超时，因此用户本机三小时继续是 `LOCAL_APPLY_PENDING / NOT_VERIFIED`。
- 沙箱候选v5把 causal low-zone `recall_tier>=1` candidate manifest 真正接入 `--stage all`；actual candidate-aware `fold_support.json` 与 calendar-only structural reference 分开，不再用“日历够长”冒充“候选支持够”。
- 集成执行抓出并修复三类证据风险：① calendar structural split可READY而实际候选仍不足；② 默认HGB `min_samples_leaf=300` 时旧100条train门槛连一次二叉切分都不可能，现门槛为 `max(100,2*min_samples_leaf)`；③HGB signature遗漏超参会复用旧完成实验，现绑定完整模型配置并显式记录 `REUSED_COMPLETE`。
- H504与AUX registry/result新增 `task_scope=H504_JOINT/AUX_HISTORY`；T0 snapshot baseline排除 `vir*`、`vp_*`、`kdj_low_*` 研究增量，后续T3−T0才可干净归因。
- 候选沙箱实跑 `40 passed in 31.85s`；另跑完整1180-session/12-stock/2664-candidate合成链，candidate→H504 label→actual fold→T0 fit→156条dev prediction→receipt贯通。该集成显式使用测试用 `min_samples_leaf=20`，receipt `real_train_seconds=0`、`target_met=false`，只算软件证据，不算市场成绩。
- 对话候选包 `eml_auto9_candidate_v5.zip`：SHA256 `2f0325a39d2ac552426d6ea388782f47c4b645dab053e0d8e0703b43a9196960`；v4→v5 patch SHA256 `da2fd6be8158dc5369d6743d4dd17cded6336d671dbaa69291f4b0a556db6cb0`。
- 下一次真正改变项目状态的证据仍必须来自用户本机：`local_start_receipt`、真实 `candidate_manifest/fold_support`、`REAL_MARKET` 或 `AUX_REAL_HISTORY` registry/checkpoint、完整predictions及 `execution_receipt`。

## 最新补充审计（2026-09-21 23:44 JST）：11/11 遗留项全部仍坏；并更正我自己的口径 —— 去重对净值的方向取决于统计量

- 完整报告：[`2026-09-21_23-44-53_JST.md`](./2026-09-21_23-44-53_JST.md)。
- `reviewed_source_sha`: `4a4910ed3ba070a8809cc6ad49ad29079564d7e1`；类型：`ARCHIVED_REAL_MARKET_REEVAL` ＋ `REAL_CODE_MEASUREMENT`；`REAL_MARKET_NEW_FIT = 0`，**未重训**。
- **11 个遗留项全部 `已确认错误`（0 已修 / 0 未复现）**，含 `EML-P0-FIXUP-SYNC-FAILOPEN`（`run_fixup.py:180/:183-184/:233-238`，远程不可达仍 `exit 0` 打印 `fix-up ok`）、`EML-P0-AUDIT-FETCH-FAIL-PASS`、`EML-P0-AUDIT-STALE-ATTEST`、`EML-P1-AUDIT-DRIFT-PASS`、`EML-P1-META-BLACKLIST-H10-NAMES`（注入 21 列 → **20 列被收进特征**）、`EML-P1-HOLDOUT-ARTIFACT-SCHEMA-DRIFT`（字面 25 vs tracked 27）、`EML-P1-SEARCH-REPORT-SCHEMA-DRIFT`（`ranked_unfiltered` 在 **0/15** tracked 报告中）、date-clustered CI 陈旧（已发布区间比当前 `block=5` 定义**窄 40.2335%**）。
- **【更正我自己，最重要】** 我在上一份 `2026-09-21_23-32-12_JST.md` §6 沿用了早前的 **−32.38%** 而未加限定。本轮在**真实 646,718 行账本**上实跑：重复 `(code,date)` **55.5547%**；去重后 **`gross_mean_return` 0.0044660826 → 0.0071822910（+60.8186%）**，但 **`gross_median_return` −0.0054054054 → −0.0010483829（−80.6049%）** ⇒ **方向取决于统计量**，均值**抬高**而中位数**压低**。因此 −32.38% 判定 **未复现（量级与符号都不对）**；**缺陷本身仍成立**，但**不得再写成单一负数**。
- **机制**（`src/live_readiness.py`）：`:72` 直接把**多策略**账本 merge，`:87` 取其均值，**全文件从无 `drop_duplicates`** ⇒ 同一 `(code,date)` 最多被 35 个策略各计一次。
- **我独立复核了子 agent 的三个承重断言**（非采信）：① `labels.dedupe_signals` 单股票 97 会话 → 保留 **1/2**，加入填充股票 → **2/2** ⇒ **证实**，且表明该项**标签错了**（真因是 `labels.py:233` 用**本帧日期**构造 `session_index`，应叫 **frame-local**，不是墙钟）；② 破坏 `ml_final_holdout.json` → checker `exit 1`（`590 checks, 6 problems`），删文件 → `exit 1`（`590/5`）⇒ **checker 其实 fail-CLOSED**，fail-open **仅在 git-fetch 包装层**；③ 去重数字与子 agent 逐个一致（`0.0044660826` / `0.0071822910` / `resolved 283,768` / `+60.8186%`）。
- **两处范围/标签更正**：`EML-P0-COOLDOWN-INDEPENDENT-CLOCK` → 缺陷成立但应叫 **frame-local**；`EML-P0-ARR-ARTIFACTS-ABSENT` 与 `EML-P0-AUDIT-FETCH-FAIL-PASS` → **范围收窄**（前者只有 `2026-09-20_03-06-03_JST.md:187` 越界断言；后者 fail-open 只在 fetch 包装层）。
- 本轮 `程序修复 = 0`；`任务定义变更 = 1`（`live_readiness` 必须声明每个统计量在去重下是否口径一致，因为均值与中位数方向相反）；`真实模型增益 = 0`。
- **未跑全量测试套件** ⇒ 不宣称零回归。`docs/audits/validate_latest.py` 在本仓库**不存在** ⇒ 未运行、**不编造通过**。
- 破坏性注入**只在 `%TEMP%` 副本**；仓库只被**只读**访问。**未改源码**，**未动排程**，**未触碰** `scripts/register_fixup_task.ps1` 与 `.gitattributes`。

## 最新独立审计（2026-09-21 23:32 JST）：被审报告头条成立，但它「无法重建修正排名」被推翻

- 完整报告：[`2026-09-21_23-32-12_JST.md`](./2026-09-21_23-32-12_JST.md)。
- `reviewed_source_sha`: `7dfababe91fa4b6174d852b0ac2e2eb63034af4a`（= `origin/main`，`ls-remote` 回读一致）。
- 类型：`ARCHIVED_REAL_MARKET_REEVAL` ＋ `PROVENANCE_AND_RECONCILIATION` ＋ `REAL_CODE_MEASUREMENT`；本轮 `REAL_MARKET_NEW_FIT = 0`，**没有**新的实股成绩，**未重训**。
- **被审报告 `2026-09-21_22-03-39_JST.md` 的头条成立**：`src/ml/search.py:230-234` 的 help 写 `--min-signals` 是「`a config must clear across every fold`」，而唯一闸门 `:356-360` 只比较 pooled `oos_signals`；`per_fold_signals`（`walkforward.py:478`）**从不参与**资格判断。反例表逐格复现：`wide_logistic_37` [1902,101,321,84]、`wide_hgb_14` [6023,1279,119,300]、`wide_logistic_36` [2213,83,410,60]，位于宽网格第 2/3/4 位。
- **红队收窄该条**：`src/ml/*.py` 全仓搜索**不存在**任何逐折信号下限；但 `search.py:337-350` 的注释把「signal floor」与「completed every fold」**分开**写，与该 pooled 实现**自洽**。⇒「文档逐折」一侧**仅由那一句 help string 承担**。
- **推翻它「不能重建修正排名」的结论（`:63`）**：`reports/ml_search_wide.json` 的 `len(ranked) == n_configs == 58`，且 **58/58 行都带 `per_fold_signals`** ⇒ 修正排名**可以**仅用 tracked 数据重建。我重建：**存活 39/58**，冠军**不变**（`wide_rf_32` 20.8379%，min_fold=1545），但发布者的第 2/3/4 名**全部被取消资格**。红队独立重建得**同一结果**。
  准确边界（采纳子 agent A 措辞）：**排名可重建；不能恢复的是 producer 的自述元数据**（`min_signals`/`ranked_basis`/`ranked_unfiltered`/`oos_base_rate_by_label` 全缺）与任何需重新拟合的结果。
- **新发现 `EML-P1-SEARCH-ARTIFACT-PREDATES-FILTER`**：该归档产物**早于资格过滤器**。键集指纹缺 `ranked_basis`/`min_signals`/`ranked_unfiltered`，且含 **6 行 `n_folds<4`**（`wide_hgb_0/1/6/7/12/13`）——现 producer 会丢掉它们。红队以 `git rev-list --all` **加强**：该 JSON 的任何已提交版本都从未含这些键，而生成它的提交 `59d2b2c` 的 `search.py` 已含并会写出它们。
- **新发现 `EML-P1-LEADERBOARD-WRONG-EVEN-UNDER-POOLED-RULE`**（红队贡献）：上述 **6 行连现存总计闸门都过不了**，却已在已发布榜单中 ⇒ 榜单错的理由**独立于**逐折问题。
- **新发现 `EML-P1-MIN-SIGNALS-FIX-COLLIDES-WITH-MIN-FOLDS`**：被审报告提议的逐折修法**未指明语义**，两种语义后果相反——`rows with n_folds<folds_requested = 58/58`，补 0（语义 B）⇒ **0/58 存活** ⇒ 触发 `search.py:361-369` 的 `else` 回退 ⇒ **守器自我关闭**；只算已上报折（语义 A）⇒ 39/58。
- **新发现 `EML-P1-ZERO-SIGNAL-FOLD-INVISIBLE`**（红队贡献）：`folds_requested=5` 但 `max(n_folds)=4`，`summarise()`（`walkforward.py:437`）丢零信号折 ⇒ 「逐折下限」在缺折时**空洞**，且 `across every fold` 在当前产物上**无法验证**。
- **新发现 `EML-P1-ELIGIBILITY-RULE-UNREACHABLE-BY-TEST`**：资格规则**内联在 `main()`**，任何测试都够不到——这正是它长期存活的原因。修补把它提为命名函数 `min_fold_signals`。
- **已验证修复 + 真探测力**（全部在 `%TEMP%` 纯净副本）：修复版 `exit=0 5 passed`；未修版 `exit=2 ImportError`（规则不可达）；**变异 M1**（helper 在、过滤条件退回 pooled）`exit=1 1 failed, 2 passed` ⇒ **探测力是真的**，不是"打完补丁测试通过"。
- **仓库自带审计全绿却在漂移之上**：实跑 `python scripts/audit_reports.py` → `exit=0`，`{"checks": 629, "problems": 0, "notes": 12}`（独立复现，非引用）。
- **对被审报告 §2 的纠正**（`EML-H22-WILSON-COLUMN-MISLABELED`，**待验证风险**）：其 Wilson 数值全部复现（rf 16.2201 / ET 17.6066 / hgb 16.0876，z=1.96），但「最差折 Wilson 下界」一列对 3 行中的 **2 行不是**最差精度折的界（`hgb_14` 的 16.09% 取自一个 **119 信号折**）。其方向性结论不受影响。
- 引用缺陷（子 agent A）：被审报告引 `lowzone.py#L250-L280`，该文件仅 263 行；真实 V00 `min_tier=1` 在 **`:206-212`**。
- **未复现**：被审报告 §4 的 6 个沙箱候选文件与 2 个 SHA256 摘要——`git ls-files --error-unmatch` 逐一 `exit 1`，磁盘上也不存在 ⇒ 其 `5 passed in 0.06s` **不可作为项目证据**（作者已自标"沙箱"，**不是造假**）。
- 本仓库**不存在** `docs/audits/validate_latest.py`（`Test-Path` False）⇒ 未运行，**不编造通过**。
- **未改任何源码**；补丁/测试/重建**全部在 `%TEMP%` 副本内。**未触碰** `scripts/register_fixup_task.ps1` 与 `.gitattributes`（他人未提交改动）。

## 最新研究推进（2026-09-21 22:03 JST）：搜索逐折支持门槛错误＋PIT candidate ledger 候选

- 完整报告：[`2026-09-21_22-03-39_JST.md`](./2026-09-21_22-03-39_JST.md)。
- 类型：`ARCHIVED_REAL_RESULT_REANALYSIS_AND_CANDIDATE_IMPLEMENTATION`；`REAL_MARKET_NEW_FIT=0`，不是新的 H504 市场成绩。
- 被审默认分支：`4d233e32901168531aaa881d9984b90089b1c8f1`；tree：`f7897e90401c47f889a1853d3b3ae139c42a2f78`；Open PR=0。
- 报告提交：[`adfcb8ef6f724eea2ea73c4b2385a68e8b518796`](https://github.com/fy-god/pro-web-60d-strategy/commit/adfcb8ef6f724eea2ea73c4b2385a68e8b518796)。
- **新 P1 `EML-P1-SEARCH-MIN-SIGNALS-NOT-PER-FOLD`**：`src/ml/search.py` 的 CLI/help 明确说 `--min-signals` 是“每个 fold 都必须达到”的支持下限，但 eligibility 实际只检查 pooled `oos_signals`。归档真实反例：`wide_logistic_37` 2408 总信号但四折为 `1902/101/321/84`；`wide_hgb_14` 为 `6023/1279/119/300`；两者仍被排在宽网格第2/3位。`wide_rf_32` 和 `wide_extratrees_26` 四折均真正清过250门槛。
- **归档 H10 新稳健性重算**：RF pooled precision 20.84%，最差折 Wilson 95% 下界16.22%；`wide_extratrees_26` pooled 18.99%，但四折 precision 仅 18.80%–19.33%，最差折 Wilson 下界17.61%，折间 SD 仅0.246pp。它适合作为未来未曝光 H10 时间块的“稳健性控制”，不迁移成 H504 结论。
- **H504 接口候选**：实现从 causal `lowzone.build_layers` 的 `recall_tier>=1` 直接生成 PIT candidate manifest 的候选，不读 label/entry/future 列、不在 candidate 阶段 cooldown；候选链为 `PIT layers -> candidate_manifest -> session-clock H504 oracle -> fold_support -> T0..T5`。
- 沙箱候选实跑 `5 passed in 0.06s`；包含真实归档四配置的 ranking-guard 反例测试。候选 ZIP SHA256=`4fe45a463c7d8b0069b2f2c70015a26a8beb61b333bd7016cb23ab0f22b1b9a0`。这仍是软件/归档分析，真实市场 fit=0。
- 用户本机三小时研究仍无新 start/execution receipt，继续为 `LOCAL_APPLY_PENDING / NOT_RUN`；下一次改变 H504 项目状态的证据必须是本机真实 candidate/outcome/fold-support/registry/checkpoint/full predictions/receipt。

---

## 最新审计（2026-09-21 19:52 JST）：新提交审查＋守卫变异测试＋折聚类不确定性

- 完整报告：[`2026-09-21_19-52-00_JST.md`](./2026-09-21_19-52-00_JST.md)。
- 类型：`ARCHIVED_REAL_MARKET_REEVAL` ＋ `PROVENANCE_AND_RECONCILIATION`；本轮 `real_market_fit_count=0`，**不是**新的实股成绩，也**未重训**。
- 被审新提交：`8b3034d77c418c85919170f7074e909e8540f187`、`92a4d17b7ec691692968f6adde97e14083349848`（=`origin/main`，`ls-remote` 回读一致）。前一份独立审计绑定 `c56f89865d777f525118112bd16ea753de44efc5`。
- 这两个提交是**纯文档提交**：`git diff --name-only c56f898..origin/main` 只有 `docs/audits/expert-ml/**` 两个文件；`src/ scripts/ tests/ reports/ configs/ .github/` 变更数**全为 0**（**80 个提交 / 33 份报告**未触及产品源码）。
- **核心纠正「缺 4 个字段而非 3 个」经我 AST 独立复算为真**：producer 字面量 **25** 键 / tracked JSON **27** 键 / 缺 `date_clustered_method`、`date_clustered_95_block1`、`date_clustered_95_signal_dates_only`、`holdout_calendar_sessions`。口径提示：`4` 指**顶层初始字面量**键；排除 producer 自标 `<- old definition` 的 `date_clustered_95_signal_dates_only` 则为 3 —— 报告未声明口径。
- 我实跑仓库自带审计：`629 checks run, 0 problem(s)`（exit 0），**漂移存在而审计全绿** —— 盲区确认（`TOP_LEVEL_FIELDS` 不含那 4 键；`ARTIFACT_SHAPES=15` 只是最小键数下限）。
- **发布物陈旧区间仍成立**：tracked `date_clustered_95` 宽 `0.0734944` vs 当前 `block=5` 定义宽 `0.1229692` ⇒ **窄 67.3179%**；tracked 值恰等于 `block1` 变体。陈旧窄区间出现在 `README.md`、`TARGET_70PCT.md`、`docs/REVIEW_RESPONSE.md`。
- **我实现的守卫已过变异测试**（被审报告只「提议」）：真实陈旧 JSON → **FAIL（抓住）**；补齐后 → **PASS**；仅多出无关键 → PASS。同时指出其措辞在 **`n==0`** 路径会**误判正确输出**，必需集必须**只取字面量键**。
- **我补上被审报告缺失的区间与稳健性检验**（纯归档 JSON，秒级）：按折聚类的 delete-one-fold jackknife 诚实区间比朴素区间宽 **4.81×–37.35×**（`fam_rf_5` `[14.55, 27.13]%`；三条 HGB 下界**跌破 0**）；**留一折重算，丢第 0 折冠军即由 `fam_rf_5` 变为 `fam_hgb_0`** ⇒ 「RF 优势不是小折抬高」需加限定：它对**丢掉大折并不稳健**。
- **`LATEST.md` 重写静默丢弃 11 条历史报告索引**（`26+/78-`，89→37 行），另丢 24 个 SHA 令牌与若干开放项陈述；**11 个 `.md` 文件本身未删除**，且有 `LATEST.md@c56f898` permalink 缓解（我验证该 permalink 可解析）。被审报告正文未提及此点。
- **`3 passed` 与两个候选脚本不在仓库**：`audit_holdout_contract.py` / `analyze_h10_stability.py` 在任何 164 个可达提交中**从未被添加**，仅出现在两份 `.md` 正文里；本仓测试实为 **`15 passed in 5.33s`（exit 0，整仓 collect 15 个）**。作者已明确标注「沙箱」，故判定 **未复现（附件不在仓库）**，**不是造假**，但**不得当作项目证据引用**。
- `docs/audits/validate_latest.py` 在本仓库**不存在** ⇒ 无法运行，不编造通过。
- 子 agent：A/B/D 已返回并逐条复核采纳（**无一条被推翻**）；**C 未完成、我在推送后停止、无任何输出，不计为证据**。B 的运行在冻结副本内产生了 **gitignored** 文件（`data/panel_daily.parquet` 等），我已核实并**删除恢复纯净**；外层仓库未被触碰。
- **【§14 补充，子 agent C 返回后新增，我已逐条独立复核】发现比被审报告所纠正者更严重的同类漂移**：`src/ml/search.py:410-431` 的 producer 有 **15** 个键，而 tracked `ml_search_models.json` / `ml_search_ablation.json` 各只有 8 键（**缺 8**）、`ml_search_wide.json` 有 11 键（**缺 4**）。其中 `ranked_unfiltered` —— producer 用来提供「`--min-signals` 下限没有藏掉候选」的**机器可读保证** —— 在**任何 tracked `.json` 产物中命中数为 0**（只在代码与文档里出现）⇒ **当前没有任何机器可读产物能独立验证该过滤没藏掉候选**，而 H10 结论正建立在这些搜索产物上。`ml_null_tests.json` 同样缺 `leak_factor` 与 `permuted_labels.n_folds`/`per_fold_signals`。新命名：`EML-P1-SEARCH-REPORT-SCHEMA-DRIFT`、`EML-P2-ZERO-SIGNAL-COMMENT-STALE`。
- **【§14.3 机制归因更正】**：`src/ml/final_holdout.py:242-243` 的注释称 signal-dates-only 会丢掉「~158 个 holdout 会话中的约 8 个」无信号会话，但 tracked `distinct_dates = 150` 而重跑 `holdout_calendar_sessions = 150` ⇒ **无信号会话 = 0**，且 producer 自己的方法字符串（`:315`）就写 `including the 0 that carried no signal`（**同文件自相矛盾**）。因此 **67.3% 的加宽完全来自 `block=1 → block=5`**，与宇宙是否含无信号会话无关。67.3% 这个数字本身正确，更正的是机制归因。
- **【§14.4】** `ml_search_models.json` 的 `fam_rf_5` 与 `ml_search_wide.json` 的 `wide_rf_32` **逐位相同**（同一运行两个名字），且 58 个宽网格 config 无一超过它 ⇒ **20.84% 是该家族极大值，存在选择效应**，与「丢第 0 折冠军即易主」互相印证。
- **【§14.5 我更正自己的表述】**：`\ProWeb60d-ReportAudit` **确实已注册并在运行**（每 4 小时，`Next Run 2026/9/21 19:15:00`）；先前「无调度器」的说法**不精确**。准确说法：`ProWeb60d-Fixup` 确实未注册，但另有一个只做报告一致性检查的 `ReportAudit` 在跑，**它不执行任何 producer**（`audit_reports.py` 的 `subprocess` 提及数 = 0，`.github` 不存在）。另更正：`date_clustered_95` 本身**不会**写进 `AUDIT_STATUS.md`。
- **【§14.6】**「有效支持折 2.75」度量的是**信号数量在折间的分散度**，不是 pooled precision 的泛化不确定性；C 用折间方差得 RF t(3) `[16.75%, 24.93]%`，与我的 jackknife `[14.55%, 27.13]%` **同向同量级**（两种方法均为估计，不合并）。被审报告的方向性判断（RF 比 HGB 稳）**成立**，但其 `:160` 所述理由（样本重叠）不是主因。
- **更正上一份记录**：`EML-P2-TEST-KDJ-NESTED` 被 15:48 标为「已修复」是**错的** —— `tests/test_engine.py:306` 的 KDJ 断言体**嵌套在** `test_wilson_upper_bound_is_not_a_constant`（L268–319）内部，`test_kdj_continuous_across_year_boundary` **不是 `def`**，pytest 中 KDJ 仅 1 个 id；**仍未修**。

## 上一轮（保留）：2026-09-21 18:03 JST — H10 折支持稳定性＋holdout 产物契约检查

- 完整报告：[`2026-09-21_18-03-47_JST.md`](./2026-09-21_18-03-47_JST.md)。
- 类型：`ARCHIVED_REAL_RESULT_REANALYSIS_AND_AUDIT_CANDIDATE`；本轮 `real_market_fit_count=0`，不是H504新成绩。
- 被审默认分支：`c56f89865d777f525118112bd16ea753de44efc5`；tree：`2138c10739c148ccf523d6ea21382ea770bdbb09`；Open PR=0。
- 报告发布提交：`8b3034d77c418c85919170f7074e909e8540f187`；报告blob：`084faa36ed54533c4e978d383de24570bd5b47ae`，已按返回提交回读。
- **纠正15:48报告一处计数笔误**：当前 `src/ml/final_holdout.py` 初始payload相对tracked `reports/ml_final_holdout.json` 缺失的是**4个**字段，不是3个：`date_clustered_method`、`date_clustered_95_block1`、`date_clustered_95_signal_dates_only`、`holdout_calendar_sessions`。当前 `audit_reports.py` 的 `TOP_LEVEL_FIELDS` 没覆盖这四键，因此629检查仍抓不到该producer/artifact漂移。
- **H10归档新分析**：`fam_rf_5` pooled precision 20.84%，四折为22.88%/18.36%/18.06%/20.71%，最大单折信号占49.02%，signal-HHI折算有效支持折2.75；三条HGB候选最大单折占80.31%–85.88%，有效支持折仅1.34–1.49。RF的20.84%不是靠一个几百信号的小折抬高，值得作为未来未曝光H10时间块的冻结候选；仍不是RF>HGB的配对显著性证明，更不是H504成绩。
- null控制继续接近基率：permuted-label mean 3.1067% vs base 3.0842%；noise 4.0628% vs base 4.0894%，lift 0.9935x。
- 当前沙箱实际实现并测试 `audit_holdout_contract.py` 与 `analyze_h10_stability.py`，`3 passed`；附件zip SHA256=`295df8569525572319923e5f46c069882344c430358f755c53ee1a47ff50d609`。这是软件/归档分析，不是本机三小时训练。
- 用户本机runtime仍 `LOCAL_APPLY_PENDING`，单次三小时仍 `NOT_RUN`：上一独立审计已证明 `ProWeb60d-Fixup` 根本未注册；没有start/execution receipt、真实registry/checkpoint/predictions前不得称完成。

## 最近一次独立源码/本机复核（保留，不被本次归档分析替代）

- 完整报告：[`2026-09-21_15-48-00_JST.md`](./2026-09-21_15-48-00_JST.md)。
- 类型：`INDEPENDENT_AUDIT_AND_PROVENANCE_RECONCILIATION`。
- 被审默认分支：`5d1b365cd6c2a80a74b18fbf12e47e766203eb93`。
- 核心事实保持有效：本机 `ProWeb60d-Fixup` 未注册；自最后产品源码提交后多轮审计无人自动消费；仓库生产者 `src.ml.final_holdout` 本机真实重跑91.4s，H10点估计 844/6202=13.61%、base 2.8958%、lift 4.70x完全复现；tracked clustered CI陈旧；候选v4只存在审计沙箱证据，不能当仓库已落地产物。
- 本次仅把其“缺3字段”文字计数更正为4；不撤销其点估计复现、CI陈旧、fixup未注册等主结论。

## 最近候选执行链（保留）

- [`2026-09-21_14-06-49_JST.md`](./2026-09-21_14-06-49_JST.md)：三小时执行收据、epoch级resume候选v4；仓库未落地、实股fit=0。
- [`2026-09-21_10-08-25_JST.md`](./2026-09-21_10-08-25_JST.md)：可执行研究流水线v3候选；仓库未落地。
- [`2026-09-21_06-03-05_JST.md`](./2026-09-21_06-03-05_JST.md)：session-clock H504候选v2。
- [`2026-09-21_02-07-54_JST.md`](./2026-09-21_02-07-54_JST.md)：H504合同/FeatureSpec/fold-support/VIR候选。
- [`2026-09-21_01-43-18_JST.md`](./2026-09-21_01-43-18_JST.md)：单次连续三小时执行合同。

## 历史索引归档

本次不删除任何历史报告。更新前的完整长索引固定在：

- [`LATEST.md@c56f898`](https://github.com/fy-god/pro-web-60d-strategy/blob/c56f89865d777f525118112bd16ea753de44efc5/docs/audits/expert-ml/LATEST.md)

> 当前最重要的项目边界：H10已有本机可复现真实OOS证据；H504仍没有合法新实股训练结果。下一次真正改变项目状态的证据应是用户本机非文档产物（start receipt、真实registry/checkpoint、全量predictions、execution receipt），而不是继续增加候选版本号。