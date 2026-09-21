# 专家／ML研究入口：源码已经入库

本目录入口用于 `fy-god/pro-web-60d-strategy`，不需要从聊天ZIP拼装源码。H10旧标签、模型和归档不覆盖；H504研究单独运行。

## 已实现的范围

`src/ml/research_h504/` 提供独立市场日H504标签、因果候选清单、显式FeatureSpec、候选支持检查、快照/KDJ路径/量压/VIR、家族ECDF/MEB模块、T0 HGB、AUX因果TCN base/plus、检查点和执行收据。

这是初始可运行研究链，不是所有方案都已实现：T1—T5、完整MLP对照、OOF/meta、独立校准和最终发布账本仍须按真实依赖补齐。AUX结果不代表H504四倍事件结果；现有软件测试不证明市场效果。

## 1. 环境与自检

使用本项目既有隔离Python环境。依赖包含numpy、pandas、scikit-learn；TCN需要torch；测试需要pytest；Parquet输入需要pyarrow或等价读取引擎。不要自动修改全局环境。

```text
python -m src.ml.research_h504.run --help
python -m pytest -q tests/research_h504
python scripts/run_fixup.py --dry-run
```

本次隔离部署测试记录在 `docs/research/h504_integration_validation.json`：50项通过，包括合成HGB/TCN及launcher mock。未重跑完整既有仓库测试，未在用户Windows或真实市场数据上执行。

## 2. 准备明确输入

- panel：CSV/CSV.GZ/Parquet，列为 `code,date,open,high,low,close,volume`。股票代码统一为与候选完全一致的字符串。OHLC必须同一价格基准；读文件不自动认证PIT、复权或成交可执行性。
- calendar：独立、有版本的市场日历，CSV的 `date` 列；真实运行必填。未来排期不充当已观察到的随访数据。
- layers：从因果低位机制产生，列 `code,date,recall_tier`。不使用未来结果选候选。
- candidates：已有候选清单可直接提供；保留 `candidate_id`，不得因未来标签未知/无法入场删除。

若真实日历或价格口径不明，先修数据合同，不通过换成 `SYNTHETIC` 绕过校验。

## 3. 同一个研究目录顺序执行

以下路径是需替换的示例，不代表本机一定存在这些文件。Windows中可直接使用单行命令。

```text
python -m src.ml.research_h504.run --stage candidates --layers <真实layers.csv> --out outputs/ml/research_runs/batch001/candidates.csv
python -m src.ml.research_h504.run --stage all --panel <真实panel.parquet> --calendar <独立calendar.csv> --candidates outputs/ml/research_runs/batch001/candidates.csv --out outputs/ml/research_runs/batch001 --resume --offline --evidence-type REAL_MARKET --source-sha <实际源码SHA>
```

也可在 `all` 中提供 `--layers` 代替 `--candidates`。代码会生成因子与诊断、检查H504候选支持、尝试T0，再执行AUX base/plus（默认三个种子）。缺torch只阻塞神经分支；`--skip-neural` 可显式跳过神经。H504无合法完整随访时间外折时保留阻塞状态，不缩短504，也不随机切分凑结果。

`--stage inspect` 的fold输出只作日历结构参考；`--stage all` 的 `fold_support.json` 使用实际候选。默认HGB每叶300，训练支持至少600，并另外检查类别支持。

## 4. 三小时本地执行

`run_fixup.py` 已改为13200秒（220分钟）硬上限，使用文件锁，sync失败或工作区dirty时停止；不再自动autostash/rebase。`--dry-run` 不执行Git同步或创建日志。`fixup_prompt.txt` 已替换为研究队列合同，不再“只修P0/P1”或“同报告立即退出”。

但本次提交没有连接用户电脑、没有更改实际Windows注册任务。磁盘中的旧任务模板仍可能是PT2H30M，低于三小时。启动前，本地执行者必须只读查询实际注册值：

```powershell
Get-ScheduledTask -TaskName ProWeb60d-Fixup | Select-Object TaskName,State,@{Name='ExecutionTimeLimit';Expression={$_.Settings.ExecutionTimeLimit}}
```

任务不存在则报告 `LOCAL_APPLY_PENDING`，不要冒称已启动。若任务存在但上限不足，在用户已有一次性授权下备份并只调整运行时上限到PT3H50M，回读确认Triggers/Actions/Principals不变；不要运行删除重建任务的旧完整注册脚本。本次没有更改任何触发时刻。

有效研究目标10800秒，正常总wall12600秒；48次累计fit预算及已耗量仍须本地执行者核对。当前registry是研究记录，不是完整的跨进程预算控制器。完成当前任务后继续有依据的READY工作；没有合法工作或预算不足须如实结束，不空转、同hash重跑或关闭合理早停凑时间。

## 5. 产物与恢复

检查 `data_inventory.json`、`candidate_manifest.csv`、`fold_support.json`、`feature_schema.json`、诊断、`experiment_registry.jsonl`、T0模型、AUX best/last检查点、全部开发预测，以及 `local_start_receipt.json` / `execution_receipt.json`。

未知结果候选仍在H504开发预测里。`target_met=false`就是未达到时长，退出码0不代表市场研究成功。源码/数据/日历变更会改变signature；不要把不兼容旧run目录当作可复用完成结果。中断时检查 `last.pt`；当前支持训练状态恢复，但不宣称中途batch级位一致恢复。只加载自己生成或已核验的pickle/PT文件。

本阶段的开发预测参与早停/选择，不是未经查看的最终测试。家族映射、PIT股票池、复权、交易可执行性、相关性区间和正式发布政策必须另验。不要从COMPLETE_AUX或软件测试绿灯得出H504精确率提升。

## 6. 发布边界

本次只将研究源码、测试、本地runner/prompt和接入说明写入GitHub；原始行情、模型权重、旧报告数字、Actions和本机任务注册均未改。先取得真实本地训练与预测证据，再更新项目成功率。
