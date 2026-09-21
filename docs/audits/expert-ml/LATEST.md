# 专家／ML线研究与审计索引

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