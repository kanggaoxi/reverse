你负责 `dtype_conversion_mixed_precision` 模块。

目标：
- 逆向 `move_to_ub(dtype=...)`、`vconv` 和混合精度路径。
- 先验证文档明确支持的 dtype，再把疑似但未文档化的 dtype 作为假设测试。
- 特别注意：不要因为文件名里有 `tp8` 就直接断言 FP8 被 SWFT API 支持。

主要参考：
- `swft_op_example/lib/swft/api/compute.py`
- `swft_op_example/lib/swft/api/move.py`
- `swft_op_example/docs/compute.md`
- `swft_op_example/docs/tensor.md`
- `swft_op_example/op_test/fusion/paged_attention_tp8_do_internal.py`
- `swft_op_example/op_test/bmm/t_bmm_t_tp8_th.py`

环境准备：
- 运行任何 SWFT 命令前，必须先执行：`source /usr1/project/k00909889/swft_reverse/.venv/bin/activate`
- SWFT 包通过虚拟环境中的 pip install 安装，import 路径为 `import swft`。你可以通过 `python3 -c "import swft; print(swft.__file__)"` 找到实际安装路径来阅读源码。如果 `swft_op_example/lib/` 下的目录结构与上面列出的路径不完全匹配，请以实际 import 路径为准，同时参考 `swft_op_example/docs/` 和 `swft_op_example/op_test/` 中的内容。

开始实验前必须先做环境自检：
- 记录当前工作目录、Python 版本、关键环境变量、SWFT/Ascend 环境初始化命令的输出。
- 执行一个最小 SWFT 编译或运行样例，确认确实能生成编译产物。
- 如果环境自检失败，必须把状态标为未完成，并记录失败命令和错误信息。

实验方法：
- 把结论分成两张表：文档支持、实验观察支持。
- 每条 conversion path 都要记录失败发生在哪一层：API 校验、编译、生成产物、运行。
- 每个异常必须扩展成基线、单变量扰动、边界值、反例。
- 如果没有生成 `generated/<case>/` 或 `logs/<case>.txt`，这个 case 不能算通过。

产物目录：
- `swft-lab/results/dtype_conversion_mixed_precision/probes/<case>.py`
- `swft-lab/results/dtype_conversion_mixed_precision/generated/<case>/`
- `swft-lab/results/dtype_conversion_mixed_precision/logs/<case>.txt`
- `swft-lab/results/dtype_conversion_mixed_precision/status.json`
- `swft-lab/results/dtype_conversion_mixed_precision/summary.md`

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
- source dtype 和 destination dtype
- move-time conversion vs 显式 `vconv`
- ND vs NZ tensor 上的 conversion
- `change_view` 前后的 conversion
- 文档 dtype 与疑似额外 dtype，例如 FP8

完成标准：
- 至少 10 个不同 probe。
- 至少 4 个失败 probe，并精确记录失败阶段。
- 至少一张表明确区分文档支持和实验观察支持。
- `confirmed_rules`、`refuted_rules`、`anomalies`、`minimal_repros`、`artifact_correlations` 都非空。
- `open_questions` 为空。
- `next_steps` 为空。
- `scope_complete` 为 true。

回复要求：
- 全程使用中文回复。
- 不满足全部完成标准时，不允许回复 `DONE:`。
