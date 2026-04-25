你负责 `slice_concat_semantics` 模块。

目标：
- 逆向 `slice_to_ub`、`slice_to_l1`、`slice_to_l0A`、`slice_to_l0B`、`split_to_*`、`concat*`、`insert_to_gm` 的切片、拼接和写回语义。
- 重点观察 begin/slicesize 如何解释，切片是否保持元素顺序，写回 GM 是否出现隐藏重排或补齐。

主要参考：
- `swft_op_example/lib/swft/api/slicedata.py`
- `swft_op_example/docs/slicedata.md`
- `swft_op_example/op_test/fusion/premla.py`
- `swft_op_example/op_test/fusion/moe_token_unpermute.py`

环境准备：
- 运行任何 SWFT 命令前，必须先执行：`source /usr1/project/k00909889/swft_reverse/.venv/bin/activate`
- SWFT 包通过虚拟环境中的 pip install 安装，import 路径为 `import swft`。你可以通过 `python3 -c "import swft; print(swft.__file__)"` 找到实际安装路径来阅读源码。如果 `swft_op_example/lib/` 下的目录结构与上面列出的路径不完全匹配，请以实际 import 路径为准，同时参考 `swft_op_example/docs/` 和 `swft_op_example/op_test/` 中的内容。

开始实验前必须先做环境自检：
- 记录当前工作目录、Python 版本、关键环境变量、SWFT/Ascend 环境初始化命令的输出。
- 执行一个最小 SWFT 编译或运行样例，确认确实能生成编译产物。
- 如果环境自检失败，必须把状态标为未完成，并记录失败命令和错误信息。

实验方法：
- 每次只隔离一个变换。
- 把“数据顺序错乱”当成一等异常，必须做基线、单变量扰动、边界值、反例。
- 分开验证 forward slice 路径和 insert/write-back 路径。
- 区分普通 UB/L1 切片和 L0A/L0B 搬运语义。
- 如果没有生成 `generated/<case>/` 或 `logs/<case>.txt`，这个 case 不能算通过。

产物目录：
- `swft-lab/results/slice_concat_semantics/probes/<case>.py`
- `swft-lab/results/slice_concat_semantics/generated/<case>/`
- `swft-lab/results/slice_concat_semantics/logs/<case>.txt`
- `swft-lab/results/slice_concat_semantics/status.json`
- `swft-lab/results/slice_concat_semantics/summary.md`

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
- op family: slice, split, concat, insert
- destination mem_type: UB, L1, L0A, L0B, GM
- rank: 1D, 2D, 3D, 4D
- 连续切片与尾部切片
- 反证假设，例如“slice 一定不会重排”

完成标准：
- 至少 10 个不同 probe。
- 至少 3 个失败或异常 probe，并保存证据。
- 至少 2 个 round-trip 实验：slice 后 insert，split 后 concat。
- `confirmed_rules`、`refuted_rules`、`anomalies`、`minimal_repros`、`artifact_correlations` 都非空。
- `open_questions` 为空。
- `next_steps` 为空。
- `scope_complete` 为 true。

回复要求：
- 全程使用中文回复。
- 不满足全部完成标准时，不允许回复 `DONE:`。
