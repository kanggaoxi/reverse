你负责 `multicore_partition_sync` 模块。

目标：
- 逆向 `get_block_idx`、`sync_cores`、多核切分、每核尾块、共享 GM 写回和多核搬运规则。
- 重点观察单核与多核差异、尾块是否触发隐藏补齐、sync 前后 GM 可见性和覆盖问题。

主要参考：
- `swft_op_example/lib/swft/api/context.py`
- `swft_op_example/lib/swft/api/sync.py`
- `swft_op_example/docs/core.md`
- `swft_op_example/op_test/fusion/moe_token_unpermute.py`
- `swft_op_example/op_test/fusion/premla.py`

环境准备：
- 运行任何 SWFT 命令前，必须先执行：`source /usr1/project/k00909889/swft_reverse/.venv/bin/activate`
- SWFT 包通过虚拟环境中的 pip install 安装，import 路径为 `import swft`。你可以通过 `python3 -c "import swft; print(swft.__file__)"` 找到实际安装路径来阅读源码。如果 `swft_op_example/lib/` 下的目录结构与上面列出的路径不完全匹配，请以实际 import 路径为准，同时参考 `swft_op_example/docs/` 和 `swft_op_example/op_test/` 中的内容。

开始实验前必须先做环境自检：
- 记录当前工作目录、Python 版本、关键环境变量、SWFT/Ascend 环境初始化命令的输出。
- 执行一个最小 SWFT 编译或运行样例，确认确实能生成编译产物。
- 如果环境自检失败，必须把状态标为未完成，并记录失败命令和错误信息。

实验方法：
- 单核和多核分别建立 baseline。
- 每次只改变一个切分变量。
- 每个异常必须扩展成基线、单变量扰动、边界值、反例。
- 记录问题属于 partition math、同步、还是每核尾块隐藏补齐。
- 如果没有生成 `generated/<case>/` 或 `logs/<case>.txt`，这个 case 不能算通过。

产物目录：
- `swft-lab/results/multicore_partition_sync/probes/<case>.py`
- `swft-lab/results/multicore_partition_sync/generated/<case>/`
- `swft-lab/results/multicore_partition_sync/logs/<case>.txt`
- `swft-lab/results/multicore_partition_sync/status.json`
- `swft-lab/results/multicore_partition_sync/summary.md`

`status.json` 必须包含这些字段：
- `module`
- `scope_complete`
- `hypotheses`
- `coverage_matrix`
- `confirmed_rules`
- `refuted_rules`
- `anomalies`
- `minimal_repros`
- `artifact_correlations`
- `known_failures`
- `open_questions`
- `next_steps`

覆盖维度：
- single-core vs multi-core
- core count 与 per-core chunk size
- 均匀切分 vs 尾块切分
- 有 sync vs 无 sync，按实际语义可行性记录
- GM read 和 write-back pattern

完成标准：
- 至少 8 个不同 probe。
- 至少 2 组尾块切分异常实验族。
- 至少 2 个检查同步行为的 probe。
- `confirmed_rules`、`refuted_rules`、`anomalies`、`minimal_repros`、`artifact_correlations` 都非空。
- `open_questions` 为空。
- `next_steps` 为空。
- `scope_complete` 为 true。

回复要求：
- 全程使用中文回复。
- 不满足全部完成标准时，不允许回复 `DONE:`。
