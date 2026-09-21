# 专家／ML线研究与审计索引

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
