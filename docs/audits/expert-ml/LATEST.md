# 专家／ML线研究与审计索引

## 补充（2026-09-22 22:05 JST）：开放项清单存在一个**无正文**的 ID（可追溯性断裂，P3）

- 完整报告：[`2026-09-22_22-05-00_JST.md`](./2026-09-22_22-05-00_JST.md)。
- 18:13 轮 §6 写「以下仍按**已有 ID** 开放」，但其中 `EML-P1-H504-FOLD-SUPPORT-USES-CACHED-TIMEOUTS-BEFORE-DEV-START` 在纯净全树中**恰好只出现 1 次**（`2026-09-22_18-13-20_JST.md:242`，即该清单行本身），`git log --all -S` 全历史只命中报告自身那一个提交。对照：清单其余三项分别出现 5 / 3 / 2 次且都有正文章节。
- **后果**：该开放项的判据/触发/反例在发布记录中无处可查，**不可回归核对**、只能被转抄。
- **如实限定**：其底层静态缺陷为真且另有正文（`fold_support.py:63` 签名不接受 label/resolved，结构 41 split vs 真实 dev `resolved=0`），本项**只**指出该 ID 的可追溯性断裂，严重度 **P3**，不推翻该缺陷。
- 本轮无实股证据；未改源码；未启动训练。

## 补充（2026-09-22 21:35 JST）：以真实 CLI 反例推翻「dedupe fail-closed 恒不可达」

- 完整报告：[`2026-09-22_21-35-00_JST.md`](./2026-09-22_21-35-00_JST.md)。
- 仓库既有 `EML-P1-H504-DEDUPE-FAILCLOSED-UNREACHABLE` 断言 `session_clock.py` 的 fail-closed 分支在缺 `--calendar` 时**恒不可达**。实测**推翻**：`--stage dedupe` 的时钟取自 panel，但校验的是 **signals 文件**（两者独立）。不带 `--calendar`、不带 `--evidence-type` 时，signal 日期为**周六**（`2020-01-04`）、**早于** panel 区间（`2019-12-31`）、**晚于** panel 区间（`2020-05-01`）三种情形**均 rc=1**，异常为 `ValueError: signal dates absent from market calendar`；signal 恰为 panel 日期时 rc=0 写出 1 行。⇒ **分支可达**。
- **保留的弱表述**：「不可达」措辞删除；真实缺陷改为**校验源不足**（无独立日历时无法对照交易所日历），并附实测的**静默位置压缩**（panel 缺真实交易日时 `2020-01-07/2020-01-09` 变相邻，`cooldown=1` 仍保留 3/3 行、rc=0、无异常）。
- **另一处更正**：15:40 轮 §6 的 `registry.py（26 行）` 实为 **25 行**。
- 本轮无实股证据；未改源码；未启动训练。

## 补充（2026-09-22 21:05 JST）：别名键空间分裂——一个逻辑证券两条账本行、两个入场价，且不报错

- 完整报告：[`2026-09-22_21-05-00_JST.md`](./2026-09-22_21-05-00_JST.md)。
- 这是对 [`2026-09-22_20-30-00_JST.md`](./2026-09-22_20-30-00_JST.md) 中「§3.3 别名冲突未复现」的**可执行化**：实测同一日期同时存在 `code=1`（t+1 `open=51.0`）与 `code="000001"`（t+1 `open=11.0`）时，`prepare_panel` **不抛异常**且重复守卫 `duplicated(['code','date'])` **不触发**（绕过），标签阶段对**一个逻辑证券**产出**两条账本行、两个不同 `entry_open`（11.0 / 51.0）**，全程无异常。
- **方向更正**：peer 原文预言「碰撞/合并」；实测是**分裂**（不碰撞、不合并）——分裂比碰撞更隐蔽，因为碰撞会报错。
- **触发路径**：只有外部 `--candidates`（`run.py:117`，跳过 `build_candidate_manifest`）。同数据走 manifest 会在 `candidate_manifest.py:58` **fail closed**（`ValueError: duplicate candidate key(s)`）。
- **未出厂**：仓库自身管线始终补零（5 个真实产物非 6 位计数 **0**），且不存在任何 H504 账本产物（`real_market_fit_count=0`）。故记为**待验证风险 / 首跑前置门**，非已确认错误。
- 本轮无实股证据；未改源码；未启动训练。

## 本轮复核（2026-09-22 20:30 JST）：peer 的股票代码键 P1 降级为 P2，并实测一个特征连接 fail-open

- 完整报告：[`2026-09-22_20-30-00_JST.md`](./2026-09-22_20-30-00_JST.md)。
- 被审源码仍为 `8163db84e10f52057aab1216e969f2ee121ad54f`；本轮开始时 `main=84528cb98a9634a801747460370b085c670c75ec`。`git diff 8163db84..origin/main -- src tests` = **空**，故产品源码未变，既有开放项不宣称修复。
- **降级**：`EML-P1-H504-STOCK-CODE-KEY-NORMALIZATION-MISMATCH` → **P2**。机制经真实 CLI 端到端复现（未补零 panel + 补零 candidate ⇒ `no_entry`，改回补零 ⇒ `success/entry_open=10.0`），但在仓库自己的数据路径上**可达性 0**：`data_pipeline.py:46-53` 补零，实测 `panel_daily.parquet` / `lowzone_layers.parquet` / `features_cache` / `labelled_cache` / `shard_00` 共 5 个真实产物 `code` 全为 6 位、非 6 位计数 **0**。
- **更正 peer 三处**：① 浮点子声明不成立 —— `pd.Series([1.0]).astype(str).str.zfill(6) = '0001.0'`，不是 `'000001'`；② 方向反了 —— `candidate_manifest.py:39` 是**被测试锁定**的合规侧（`test_candidate.py:415-428`），另 5 处也补零，未补零的是 `data_io.py:25` 与 `task_spec.py:57,65`；③ §3.3「别名冲突」**未复现** —— 实测不碰撞也不合并，而是**键空间分裂**（两只不同股票）。
- **新增 P2 `EML-P2-H504-FEATURE-JOIN-NO-COVERAGE-GATE-001`**：`train_h504.py:34` 的 `merge(how='left')` 无 `indicator=`、无匹配率断言，`:13-15` 的 `_safe_impute` 把全 NaN 列变成**常量 0.0**。实测特征匹配率 **0.0000** 时仍报 `COMPLETE_H504_DEV`，`logloss=0.6931471805599454`（= ln2，差 1.1e-16）、`brier=0.25`、`AP=0.5`，与「特征为纯噪声」臂（0.7000778416543246）**状态相同**，且 `metrics` 中**无任何** match/join/coverage 字段。
- **诚实降级**：该特征连接缺口在 CLI 内**可达性 0** —— `run.py:111` 的特征与 `run.py:93` 的标签同源同一个 `panel`，CLI 无 `--features` 输入；实测「标签已解析但特征未匹配」的行数 = **0**，两谓词结构重合。故记待验证风险，非已确认错误。
- 训练阶段会 **fail closed**：键失配时返回 `BLOCKED_PROTOCOL_H504`（`resolved=0`），不会拟合出坏模型。
- 本轮实测基线（纯净树 `84528cb98a96`）：全仓 **65 passed / exit 0**（32.48s）。本仓库**无** `docs/audits/validate_latest.py`，故手册第 5 步门禁在本线**不适用**，本轮不声称 gate PASS。
- `real_market_fit_count` 增量 **0**；本轮无任何实股收益/命中率数字；未启动训练，未改源码。

## 最新补充审计（2026-09-22 18:13 JST）：candidate/panel 股票代码键不一致可把有效入场静默改成 `no_entry`

- 完整报告：[`2026-09-22_18-13-20_JST.md`](./2026-09-22_18-13-20_JST.md)。
- 被审源码仍为 `8163db84e10f52057aab1216e969f2ee121ad54f`；本轮开始时 `main=6e11203e72f055bf223c4336b28b5cdf48606c61`，相对被审源码仍只有 docs-only 审计变化，Open PR=0。
- **新增 P1 `EML-P1-H504-STOCK-CODE-KEY-NORMALIZATION-MISMATCH`**：`candidate_manifest.py` 对 `code` 做 `astype(str).str.zfill(6)`，而 `data_io.prepare_panel()` 与 `task_spec.label_h504_candidates()` 只做 `astype(str)`。因此 `1`/`"1"`/数值型 `1.0` 可在 candidate 侧变 `000001`、panel 侧仍为 `1`。
- **本轮实际反例**：存在合法 t+1 `Open=11.0` 的股票，panel key=`1`、candidate key=`000001`；当前 labeler 查不到 `arrays['000001']`，实际输出 `entry_open=NaN / outcome_class=no_entry / label_joint=NaN`。统一 key helper 后同一反例恢复 `entry_open=11.0`。
- 影响不只 Parquet：CSV loader 虽强制 string，但不会把 `"1"` 自动补成 `"000001"`；Parquet 更可直接保留 numeric dtype。大批 unpadded/numeric code 可因此批量伪造 `no_entry`，污染 outcome ledger、resolved/fold 支持、自然分母与真实 fit。
- 现有 H504 测试公共 `_panel()` 默认就是 `code="000001"`，所以此前 `65 passed` 没覆盖这条输入表示路径；本轮不把那 65 项冒充成本轮执行成绩。
- 沙箱候选 guard：当前语义反例 + 统一 canonicalizer；附加测试 **4 passed in 0.05s**。候选 ZIP SHA256=`f6827a23bb1fcbbe827f9582d65cb4db6d49d4f736569bdd2872a0f249f8500c`。这些是软件/合成数据证据，不是市场成绩。
- 修复顺序提升：真实 H504 前先统一 panel/layers/candidate/feature-source 的实体键，并在 canonicalize 后做 duplicate/alias collision guard；否则后续 label/fold/fit 指标没有研究含义。
- 三小时链仍无本机回执：source runner `13200s`，tracked XML 仍 `PT2H30M`，真实 registered timeout 未读；`LOCAL_RUNTIME_APPLIED=UNKNOWN / LOCAL_3H_COMPLETED=NOT_VERIFIED`。
- `real_market_fit_count=0`；无新增 H504 成功率；旧48-fit余额因没有本机台账回传，本轮不猜数字。

## 前次协议审计（2026-09-22 15:40 JST）：上游两条 P1 由静态断言升级为实测反例，并新证 3 个未登记 fail-open 面

- 完整报告：[`2026-09-22_15-40-19_JST.md`](./2026-09-22_15-40-19_JST.md)。
- 被审源码 `8163db84e10f52057aab1216e969f2ee121ad54f`；审计起点 `origin/main` = `74857e8f250adf2f40d79dda23245c4cdfce918b`。**待审仅 2 个 docs-only 提交**（`05225aa` 报告、`74857e8` 索引），`git diff 8163db84..74857e8f -- src tests` = **空**，故被审源码即当前产品代码。
- **升级为实测**：`EML-P1-H504-REAL-CALENDAR-GUARD-SELF-REPORT-FAILOPEN` —— 差分实验：同一 panel、同缺 `--calendar`，`REAL_MARKET` → **rc=1 `BLOCKED_CALENDAR`**，而**默认（不传 `--evidence-type`）→ rc=0 静默跑完**。收据实测 `real_train_seconds=0.0` **且** `synthetic_train_seconds=0.0`，训练时间**两个桶都不进**（上游只指出 real 桶）。
- **升级为实测**：`EML-P1-H504-AUX-FALLBACK-RUNS-WHEN-PRIMARY-READY` —— 用上游自己写出的验收测试跑出：主任务 `COMPLETE_H504_DEV` 时 `run_aux_tcn` 调用 **6** 次（seeds `17,29,43,17,29,43`），默认上限独立量得 **6**。
- **新增 `EML-P1-H504-HORIZON-GUARD-SAME-FAILOPEN`**：`run.py:90-91` 的 horizon 守卫与日历守卫**共用同一个错误枚举条件**。实测默认 + `--horizon 252` → **rc=0 跑完**；`REAL_MARKET` → rc=1。⇒ 一个默认值同时打穿两个守卫，「保持现有守卫」的修法低估了面。
- **新增 `EML-P1-H504-AUX-RUNS-WHEN-PRIMARY-NEVER-RAN`**：`run.py:162` 是 `:144` 的**兄弟分支**而非子分支，故**完全不给 candidate manifest** 时结果序列为 `['BLOCKED_CANDIDATE_MANIFEST', 'COMPLETE_AUX' × 6]`，主任务从未执行 AUX 仍跑满。
- **新增 `EML-P1-H504-DEDUPE-FAILCLOSED-UNREACHABLE`**：`session_clock.py:54-56` 承诺 signal 日期缺席即 fail closed，但 `--calendar` 缺省时 `cal` = panel 并集 ⇒ `unknown` **恒为空**，该分支**永不可达**。实测 `--stage dedupe` 无日历 → **rc=0 无报错**。
- **新增索引缺陷 `EML-DOC-STALE-P1-OBSERVED-BAR-IN-LATEST`**：同一 `LATEST.md` 内 `:11`/`:53` 写 P2、`:66` 仍写 `P1-H504-OBSERVED-BAR-PROVENANCE-LOST`，自相矛盾；本次已把 `:66` 修为 P2（降级本身早在 `2026-09-22_07-41-01_JST.md:25/:85` 有记录）。
- **归属更正（重要）**：`EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE` 与 `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION` **是上游既有发现**（分别见 07:41 与 10:12 报告，11:56 报告已端到端复现），**本轮不计作新发现**，仅记录独立复算的加强数字：T0 基线 **82/82 = 100%** 列来自未被 `pipeline_hash` 覆盖的文件；保列名变异（atr 14→13）后矩阵 sha 与列 sha 均变而**签名逐字节不变**。
- 三小时链：runner `13200`（`run_fixup.py:23`）；tracked XML 仍 `PT2H30M`（**UTF-16LE，普通 grep 会漏**）；`:133` 的 `registered_task_timeout` 是硬编码 `NOT_CHECKED_BY_THIS_SCRIPT`，**非测量值** ⇒ 真实注册值不可由仓库证明，`LOCAL_RUNTIME_APPLIED=UNKNOWN`。
- 合同措辞更正：v5 合同字面只说「H504 缺合法折时做独立 AUX 历史表征」，**未**要求 AUX 让位给 T1–T5/MLP/TCN 优先队列，后者是推论而非引文。
- 执行：全仓 `python -m pytest -q -o addopts= -p no:cacheprovider` 从仓库根 **65 passed / exit 0**（22.55s；`tests/research_h504` 50 + `tests/test_engine.py` 15）。
- `real_market_fit_count=0`；无新增 H504 成功率；本轮为执行契约/证据链/索引卫生修复，**不是模型增益**。


## 前次协议审计（2026-09-22 13:57 JST）：真实日历守卫默认 fail-open，AUX fallback 在 H504 READY 时仍无条件消耗拟合槽位

- 完整报告：[`2026-09-22_13-57-18_JST.md`](./2026-09-22_13-57-18_JST.md)。
- 被审源码 `8163db84e10f52057aab1216e969f2ee121ad54f`，tree `974f7b4e4ef10f586b53316260f79629b37e010b`；Open PR=0。相对上一产品源码点 `89b722d7...` 仍只有 docs 变化，故此前开放缺陷没有被源码修复。
- **新增 P1 `EML-P1-H504-REAL-CALENDAR-GUARD-SELF-REPORT-FAILOPEN`**：`--evidence-type` 默认 `UNSPECIFIED`，而缺 `--calendar` 的阻断只对 `REAL_MARKET/AUX_REAL_HISTORY` 生效。漏写 evidence type 时，`prepare_panel(..., None)` 会使用 panel 日期并集作为 market calendar；真实数据若存在全市场缺档/子宇宙日期缺口，`t+1/t+504/deadline/fold` 可按错误 session clock 计算。相同误配置还使 receipt 的 `real_train_seconds=0`。
- 仓库现有测试已经证明该 fail-open 路径可执行：`test_all_stage_runs_diagnostics_and_blocks_h504_without_candidate_manifest` 在无 calendar、无 evidence type 下要求 exit 0；synthetic 完整链也可在无独立 calendar 下走到 `COMPLETE_H504_DEV`。修复应把 `UNSPECIFIED` 对研究阶段改为 fail-closed，并显式记录 `calendar_source/path/hash`。
- **新增 P1 `EML-P1-H504-AUX-FALLBACK-RUNS-WHEN-PRIMARY-READY`**：`--stage all` 在 H504 T0 执行/复用后，只检查 `not args.skip_neural` 就无条件进入 AUX base/plus × seeds。默认最多 6 个 AUX fit；即使 H504 已 `COMPLETE_H504_DEV`，首次 session 仍可形成 1 个 T0 + 6 个 AUX 拟合。v5 合同把 AUX 定义为 H504 无合法 fold 时的 fallback，因此当前默认队列会在主任务 READY 时抢占有限 fit/wall 预算。
- 最小队列修复：默认仅在 `PRIMARY_BLOCKED` 时进入 AUX；主任务 READY/COMPLETE 时继续预登记的 H504 T1–T5/MLP/TCN，未实现就明确 `NEEDS_IMPLEMENTATION`，不能用 AUX 自动填满。若确需同行 AUX，必须显式预登记并进入全局 fit 台账。
- 旧开放项继续开放：完成态 artifact 未校验、resolved-dev 支持缺门、feature-source signature 不完整、48-fit 全局预算未强制、AUX 部分 epoch 重放、全 NaN dev 静默常数化。observed-bar provenance 维持 07:41 审计更正后的 P2。
- 执行链：源码 runner 已 `13200s`；tracked Windows XML 仍 `PT2H30M`，真实 registered task 未回读。本轮没有本机 receipt / REAL_MARKET registry / checkpoint / full predictions，所以 `LOCAL_RUNTIME_APPLIED=UNKNOWN`、`LOCAL_3H_COMPLETED=NOT_VERIFIED`。
- `real_market_fit_count=0`，无新增 H504 成功率。本轮是实时源码协议审计，不把软件结论换算成市场增益。

## 最新独立审计（2026-09-22 11:56 JST）：完成态复用无产物校验端到端复现，并新增守卫不对称证据

- 完整报告：[`2026-09-22_11-56-38_JST.md`](./2026-09-22_11-56-38_JST.md)。
- 被审源码 `reviewed_source_sha`: `89b722d7ab88f6a5fc5f381a14c742a1f53d44cc`；上一被审基线 `2b0232f8acb712569aeb5ce68f7291ab3fc7a5dc`。
- 该区间**产品研究源码零变化**：只有 2 个 docs 提交（`a33b9d2a…` 新增 10:12 报告、`89b722d7…` 更新索引）。因此本轮**没有**任何「已修复」结论。
- **维持 P1 `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`，并用真实入口端到端复现**：真实 `run.py --stage all` + `run_h504_hgb` 调用计数，run1 调用 1 次报 `COMPLETE_H504_DEV`；删除 `h504_T0/model.pkl` 与 `dev_predictions.csv` 后 run2 调用 **0** 次、状态 `REUSED_COMPLETE`、无 stale 标记。截断、同尺寸篡改、零字节同样命中。`registry.py:19-23` 全文 25 行无任何 path/存在性/sha256 校验。
- **本轮精确化（此前未写）**：仓库**已有**所需哈希机制 —— `receipts.py:15 sha256_file()`、`:33 hash_tree()`，并在 `:184` 写入 `execution_receipt.json`。缺陷不是「没有哈希」，而是 `latest_complete` 从不读它、`finalize()` 每轮**覆盖**该 receipt 销毁旧证据、且全仓无消费者。⇒ 最小修复是**持久化既有清单到 registry 行并 fail-closed**，比重造哈希便宜。
- **影响面收窄**：盲复用仅限 `--stage all`；`--stage h504-hgb` / `--stage aux-tcn` 不查 registry、总是重训。不降低严重度，因为 `all` 是文档化的生产调用方式。
- **新增守卫不对称（P1，此前报告只作定性描述）**：`train_h504.py:43` 是**唯一**支持度门，只查 `train.sum()`/`dev.sum()`；`resolved`（`:42`）**只被使用从未被守卫**。AST 枚举 `run_h504_hgb`(24-60) 仅 3 个 `if`（`:37/:43/:47`），`resolved` 与 `len(ydv)` 均不在任何守卫中；`:59` 仍无条件报 `COMPLETE_H504_DEV` 并写入 `n_dev_resolved`。实测 **0** 个 resolved 样本仍返回 `COMPLETE_H504_DEV`。
- **`EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE` 证据链补齐**：`run.py:94` 的 `glob('*.py')` 非递归，只覆盖 `src/ml/research_h504/` 下 **16** 个文件；该包**唯一**跨包导入在 `snapshot_features.py:78`（`from src.ml import build_matrix as bm`），`src/ml/build_matrix.py` 实为 **546** 行且又 `:44 from src import data_pipeline` ⇒ 二阶未覆盖。变异实验（ATR 窗口 14→13、**不改列名**）后 `pipeline_hash` 逐位不变、`latest_complete` 命中 ⇒ 会报 `REUSED_COMPLETE` 并跳过训练。T0 输入 **82/82 = 100%** 来自未覆盖文件。
  - **更正**：一处子 agent 报告把该导入记作 `snapshot_features.py:31`；实测 `:31` 是 `missing = req - set(panel.columns)`，正确为 **`:78`**。
- **我自己提出并已自行推翻的候选**：曾疑「签名无法区分 rich 与 minimal 特征分支」。实跑两分支列数为 **85 vs 33**，且签名载荷含 `'features'` 键（`run.py:150/173`）⇒ 列集合变化**会**改变签名，该候选**不成立**，不计入缺陷。据此把签名问题的措辞限定为「**不改列名的取值级**改动不可见」。
- **`EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED` 搜索路径已明确**：`fits_*` 全仓 12 处**全部**是写入或输出，**0 处**与上限比较；`global_fits|cumulative|total_fits` **0 命中**；`ledger` 全仓 29 处逐条核对**全部无关**（报告级/lowzone/tradeability/候选台账）。唯一强制比较是 `run.py:170` 的**单进程** `--max-aux-fits`（默认 6）。**这同时是条款漂移**：合同写「48 fits/180 min 硬上限」，代码不可强制 ⇒ 需在「落地台账门控」与「明确降级为非强制指引」之间抉择。
- **`EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING` 量级已实测**：24 批/epoch，中途超时存 `epoch=0` 但 optimizer 已 9 步；恢复后 epoch 0 整体重跑 ⇒ **9/24 = 37.5%** 锚点获二次梯度，总步数 81 = 9+3×24。`best.pt` 仅由完整 epoch 产生，故**选择**未污染，维持 P2。
- **`EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`**：实测 `_safe_impute` 使全 NaN 的 dev 行塌缩为**同一向量**（`drop_duplicates` 后 1 行），无缺失指示列；端到端 504 个 dev 行得到**同一个**分数 `0.5747904879932492`，状态仍 `COMPLETE_H504_DEV`、`average_precision=0.5`。
- **未复现**：对端 10:12 报告所指「沙箱 guard 3/3」与候选 ZIP SHA-256 `4c3343b1…`、验证 JSON `6a6f2763…` —— `git log --all -S` 与磁盘穷举均**未找到**该 ZIP 或任一哈希，`latest_complete_validated`/`STALE_COMPLETE_ARTIFACT`/`required_artifact` 在源码中 **0 命中**，仅见于对端 md 正文。对端已自述其为沙箱候选 guard，属**诚实的范围限定**；但其索引一句话概括易被误读为「当前生产代码已验证」，属**表述风险**。**§1 的 P1 不依赖该未复现项**。
- **真实数字**：全仓测试 AST **65**（40+10+15）；`pytest -q -o addopts= -p no:cacheprovider` 从仓库根 **exit 0 / 65 passed**；`tests/research_h504` **50 passed**；`tests/test_engine.py` **15 passed**；`real_market_fit_count=0`；本机三小时与 receipt **NOT_VERIFIED**（仓库与磁盘均无 `local_start_receipt.json`/`execution_receipt.json`/`experiment_registry.jsonl`）。
- **三轴**：执行=本轮审计动作真实执行；研究结论=完成态复用不具可审计性（工程/证据链结论，**不构成命中率结论**）；证据=上述均为**软件/合成面板**上的真实执行。三类区分：§1–§6 为**程序修复**；48-fit 上限为**任务定义变更**；**真实模型增益 = 0**。
- **并发写入者警示**：本地 HEAD `4b1f3f6e…` 与远端**分叉**且**不在真实远端历史中**（`cat-file -e` False、`is-ancestor` False），相对 `origin/main` 还显示**删除 3 份对端报告** ⇒ 本轮**不以其为基线**。另：`git clone <本地路径>` 得到的 `origin` 是**本地路径**，其 `origin/main` 是该仓**本地** `main` 而非 GitHub 远端；须以 `git ls-remote <url> refs/heads/main` 为权威 tip。
- 本仓**无** `docs/audits/validate_latest.py` ⇒ **不声称**通过任何门禁。

## 最新补充审计（2026-09-22 10:12 JST）：registry 完成态复用缺少底层产物完整性验证

- 完整报告：[`2026-09-22_10-12-36_JST.md`](./2026-09-22_10-12-36_JST.md)。
- 报告首次发布提交：`a33b9d2a624178d510810c565ab549af2e6340e2`；被审 HEAD：`95dca888e95beaf2da04f5b09af424f6e2bc3995`，tree：`54926a21a3dd4b31df55593d6a762c1bb6cb0d6b`。
- **新增 P1 `EML-P1-H504-REUSE-TRUSTS-REGISTRY-WITHOUT-ARTIFACT-VERIFICATION`**：`Registry.latest_complete()` 只检查 signature 与 `COMPLETE*` status；`run.py` 命中后直接 `REUSED_COMPLETE` 跳过 H504/AUX 训练，不验证模型、完整开发预测、checkpoint 或训练日志是否存在，更不校验 SHA-256。
- `train_h504.py` 虽写出 `model.pkl / dev_predictions.csv / metrics.json`，但完成结果没有把这些关键文件的 path+sha256 写入 registry。因此 registry 行可以在底层证据已删除/损坏后继续“证明完成”。
- 沙箱 synthetic guard 复现：缺 model/prediction 时当前逻辑仍命中 complete；候选 guard 拒绝；完整文件+hash 允许复用；完成后篡改 prediction 则按 hash mismatch 拒绝。3/3 场景符合预期。候选 ZIP SHA256=`4c3343b1d67e400a980085d34ab069cfba9a0c891bae0c237322a9c3f06ea690`。
- 本轮仍 `real_market_fit_count=0`；没有新的本机 start/execution receipt，故单次连续三小时为 `NOT_VERIFIED`。源码 runner 已是13200秒，但 tracked Windows XML 仍是 `PT2H30M` 模板，不能用模板推断机器注册值。
- 相对上次被审基线没有产品研究源码变化；signature 外部特征依赖、resolved dev 支持、全局48-fit门、AUX部分epoch恢复等旧开放项继续开放，本轮不重复计作新增。
- 下一本地优先级：先把 `COMPLETE_*` 改成 artifact-manifest + hash 的 fail-closed 复用，再做全局fit预算与resolved-aware支持；随后真实 candidate/label/fold，合法则T0/T3，否则同session继续AUX_REAL_HISTORY。

## 最新独立审计（2026-09-22 07:41 JST）：H504 研究管线复核，新增 2 条未被发现的缺陷，并更正 1 条严重度

- 完整报告：[`2026-09-22_07-41-01_JST.md`](./2026-09-22_07-41-01_JST.md)。
- 被审源码 `reviewed_source_sha`: `2b0232f8acb712569aeb5ce68f7291ab3fc7a5dc`；被审区间 `8287b33da26978f1d513b7880baf06a9103d2879..2b0232f8acb712569aeb5ce68f7291ab3fc7a5dc` 共 9 个提交；被审落地 commit `878cdeba5837a302004a8b3a656afee3d6a62b44`。
- **新增 P1 `EML-P1-H504-SIGNATURE-BLIND-TO-FEATURE-SOURCE`**（本轮最高危）：`run.py:94` 的 `pipeline_hash` 只哈希 `src/ml/research_h504/*.py`，而 113 个特征实际由 `src/ml/build_matrix.py` 计算。实测：改 `task_spec.py` 签名会变（对照通过），**改 `build_matrix.py` 签名逐位不变** ⇒ `registry.latest_complete` 命中旧记录，`run.py:158` 报 `REUSED_COMPLETE` 并沿用**陈旧特征**结论，破坏"真实模型增益 vs 任务定义变更"的可分离性。
- **新增 P2 `EML-P2-H504-ALL-NAN-FEATURES-SILENTLY-IMPUTED`**：`train_h504.py:13-15` 用 train 中位数静默填补且无缺失指示。实测某 session 特征全缺时，50 个候选得到**同一个**有限分数 `0.695434`，无缺失标记，仍报 `COMPLETE_H504_DEV`。
- **严重度更正（对同批报告的更正）**：`EML-…-OBSERVED-BAR-PROVENANCE-LOST` 由 **P1 降级为 P2**。实测两条路径**仅 `outcome_class` 一列不同**，`label_joint`/`label_resolved`/`training_eligible` 完全一致；`src/` 内**零处**对该列做条件分支或聚合；且该列在 `feature_spec.py:18` 的 `_FORBIDDEN_EXACT` 中，不可能进入模型。
- **我自己的中间结论已撤回**：「`unknown_missing_bar` 是死代码」**过强且错误**。实测在多股票联合日历下该分支**可达**；仅在"单股票 + 面板自生日历"下不可达。
- 决定性证据：**变异测试**。删除 `data_io.py:38` 的补行后套件仍 **50 passed 全绿**；子 agent 独立把同一性质推向相反方向（对整段日历补行、彻底删除 reindex）**同样全绿** ⇒ 现成 50 测试对**生产路径零覆盖**，唯一相关的测试绕过了 `prepare_panel`。
- 维持确认：`EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`（我实测到 **0** 个 resolved 仍报 `COMPLETE_H504_DEV`，对照组为绿，比同批报告的"1 个"更强）、`EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`、`EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`（机制确认，真实影响量未测故不升级）。
- 主动高危检查（负面结论）：**未发现前视泄漏**——切分按时间、特征前缀不变性 30/30 列零变化、`unknown`/`no_entry` 未被编码为 0；子 agent 用独立方法（扰动未来全部行情、783 行前缀 × 113 特征逐位不变）得到一致结论。
- 本轮**未**启动真实训练、未连本机、未注册或修改 Windows 任务；`real_market_fit_count = 0`，无新增实股结果。本仓**无** `docs/audits/validate_latest.py`，**不声称**通过该门禁。


## 最新源码落地后独立审计（2026-09-22 06:02 JST）：H504 链已入 main，但发现 3 个 P1 + 1 个 P2

- 完整报告：[`2026-09-22_06-02-39_JST.md`](./2026-09-22_06-02-39_JST.md)。
- 类型：`POST_INTEGRATION_SOURCE_AUDIT`；被审 HEAD `a8ae13ccf1c4a6a1baf82ad4e86087fbde83e4e4`，源码落地 commit `878cdeba5837a302004a8b3a656afee3d6a62b44`。
- 源码落地是真实工程进展：`src/ml/research_h504/`、runner/prompt、测试已在 `main`；但用户本机三小时和新实股 H504 fit 仍为 `NOT_VERIFIED / 0`。
- 新确认 `EML-P2-H504-OBSERVED-BAR-PROVENANCE-LOST`：`prepare_panel` reindex 后丢失原始 stock-session 是否真的存在 bar 的 provenance，labeler 后续会把真实 missing bar 混成 missing price。
- 新确认 `EML-P1-H504-DEV-RESOLVED-SUPPORT-MISSING`：dev 只要求候选数 `>=50`，未要求可判定 `label_joint` 数量 `>=50`，极少 resolved 样本也可能返回 `COMPLETE_H504_DEV`。
- 新确认 `EML-P1-H504-GLOBAL-FIT-BUDGET-UNENFORCED`：registry/runner 尚未代码级执行旧 48 次累计 fit 预算，失败/中断/重试的跨 session 计数仍靠 prompt 合同。
- 新登记 `EML-P2-AUX-PARTIAL-EPOCH-RESUME-WEIGHTING`：epoch 中途超时会保存部分 epoch 模型，再从该 epoch 整体重跑，改变部分样本的暴露次数；paired attribution 应优先回滚到最后完整 epoch，或实现 batch cursor/sampler 精确恢复。
- source runner 已是 `13200s`，但 tracked Windows XML 仍为 `PT2H30M`；实际注册任务值与真实三小时 receipt 本轮仍未读取，不能说三小时已经跑过。
- 下一本地优先顺序：source-bar provenance → resolved-aware fold → 48-fit budget → 实际 Windows task 核验 → 真实 candidates/labels/fold → 合法 H504 T0，若主任务阻塞则同 session 跑 `AUX_REAL_HISTORY` base-vs-plus。

## 最新源码落地：研究代码已写入 main，不再只有候选ZIP

- 用户最新明确授权研究源码、测试和本地执行入口写入GitHub。
- **源码提交：[878cdeba5837a302004a8b3a656afee3d6a62b44](https://github.com/fy-god/pro-web-60d-strategy/commit/878cdeba5837a302004a8b3a656afee3d6a62b44)**。
- 完整交付记录：[2026-09-22_03-49-55_JST.md](./2026-09-22_03-49-55_JST.md)，文档首次提交 `ca37508b15e8f0ce70b6e7fd3199ac08d1324df2`。
- [研究源码目录](https://github.com/fy-god/pro-web-60d-strategy/tree/878cdeba5837a302004a8b3a656afee3d6a62b44/src/ml/research_h504)；[本地接入说明](https://github.com/fy-god/pro-web-60d-strategy/blob/878cdeba5837a302004a8b3a656afee3d6a62b44/RESEARCH_QUICKSTART.md)。
- 源码提交共23个路径：16个研究Python模块、2个测试文件、2个runner/prompt修改、3个说明与验证文件。原始行情、权重、旧H10结果、Actions及实际Windows注册任务未改。
- 已实际支持 `--stage all --resume --offline`，包含独立日历、候选、H504标签、T0 HGB、AUX TCN、完整开发预测与收据。
- 远端 `scripts/run_fixup.py` 已改为13200秒；`fixup_prompt.txt` 已替换旧“只修P0/P1、同报告直接退出”。因此此前对这两个文件的旧状态描述必须按旧SHA阅读。
- 本轮隔离测试：**50 passed in 12.66s**，范围为新增研究代码及launcher mock，含合成拟合。研究模块tree=`60086cf074a73c6956088c81aab5aa7ab3261b95`；测试tree=`7b5d79c3f0f8872f11726514f54bf286ab990a72`，与实际测试字节一致。
- [验证记录与哈希](https://github.com/fy-god/pro-web-60d-strategy/blob/878cdeba5837a302004a8b3a656afee3d6a62b44/docs/research/h504_integration_validation.json)；[pytest原始输出](https://github.com/fy-god/pro-web-60d-strategy/blob/878cdeba5837a302004a8b3a656afee3d6a62b44/docs/research/h504_integration_pytest.txt)。

### 四种状态分别记录

| 项目 | 当前证据 |
|---|---|
| GitHub研究源码 | 已在main；可直接拉取，不再要求从聊天附件拼装 |
| 软件测试 | 本轮隔离50项通过；完整旧仓库套件未重跑 |
| 用户本机runtime/三小时 | LOCAL_APPLY_PENDING / NOT_VERIFIED；本轮未连接本机 |
| 新实股H504成绩 | real_market_fit_count=0 |

当前是T0+AUX初始研究实现，不是所有T1—T5、MLP、OOF/meta、独立校准与正式发布都已完成。registry不是全局预算控制器，checkpoint恢复不宣称batch级位一致。实际Windows任务上限仍要本地核验；提交源码不等于注册任务或启动训练。

## 最近一次独立审计（保留，不被源码集成记录替代）

- [2026-09-22_03-34-01_JST.md](./2026-09-22_03-34-01_JST.md)。
- 被审源码 `8287b33da26978f1d513b7880baf06a9103d2879`；报告首次发布提交 `05556a9a5d4d95b52605357c1c1dceedf309b0fc`，后续记录提交 `bbc82825c79c7f354179f7198514ab00b96d2c5f`。
- 其中旧生产链缺陷、旧候选测试的证据争议及工作树事故记录保留原文。当前只落实研究模块与本地入口，不宣称旧H10认证/发布链所有问题已经修复。

## 三小时执行要求与原候选来源

- [单次三小时 v5 合同](./2026-09-21_01-43-18_JST.md)：有效10800秒、正常wall12600秒、runner13200秒；实际Windows上限另验。
- [上一版候选集成报告](./2026-09-22_01-57-29_JST.md)：属于当时的ZIP候选记录，不等于当时已入库。
- [前次候选恢复链报告](./2026-09-21_14-06-49_JST.md)。

## 完整历史索引（不可变保留）

[源码落地前完整LATEST：全部历史报告、独立复核、争议和开放问题](https://github.com/fy-god/pro-web-60d-strategy/blob/bbc82825c79c7f354179f7198514ab00b96d2c5f/docs/audits/expert-ml/LATEST.md)。没有删除任何历史审计报告；旧“当前状态”按其固定SHA解释。

下一份值得更新的市场证据：本机实际数据/日历/候选指纹、合法fold、真实训练日志、checkpoint、全开发预测与execution_receipt。软件入库是实际工程交付，不是H504成功率提升。
