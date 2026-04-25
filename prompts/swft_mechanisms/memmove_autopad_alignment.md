你负责 `memmove_autopad_alignment` 模块。

目标：
- 逆向 `move_to_gm`、`move_to_ub`、`move_to_l1`、`slice_to_ub`、`pad_to_ub`、`insert_to_gm` 的搬运、自动补齐和对齐规则。
- 重点观察 32B 对齐、16x16 边界、尾块补齐、`no_autopad=True/False` 的差异。
- 不要只看最终结论，必须保存 probe、编译产物、日志和异常证据。

主要参考：
- `akg/swft/python/swft/api/move.py`
- `akg/swft/python/swft/api/slicedata.py`
- `akg/swft/docs/move.md`
- `akg/swft/docs/slicedata.md`
- `akg/swft/op_test/fusion/premla.py`

开始实验前必须先做环境自检：
- 记录当前工作目录、Python 版本、关键环境变量、SWFT/Ascend 环境初始化命令的输出。
- 执行一个最小 SWFT 编译或运行样例，确认确实能生成编译产物。
- 如果环境自检失败，必须把状态标为未完成，并在 `known_failures` 或 `anomalies` 中记录失败命令和错误信息。不能把环境失败写成测试通过。

实验方法：
- 从最小 probe 开始，不要一上来改大融合算子。
- 每个异常必须扩展成一组实验：基线、单变量扰动、边界值、反例。
- 每条结论必须区分“文档写明”“源码推断”“实验观察”。
- 每个成功 probe 都要对比源代码、生成产物、日志和运行结果。
- 如果没有生成 `generated/<case>/` 或 `logs/<case>.txt`，这个 case 不能算通过。

产物目录：
- `swft-lab/results/memmove_autopad_alignment/probes/<case>.py`
- `swft-lab/results/memmove_autopad_alignment/generated/<case>/`
- `swft-lab/results/memmove_autopad_alignment/logs/<case>.txt`
- `swft-lab/results/memmove_autopad_alignment/status.json`
- `swft-lab/results/memmove_autopad_alignment/summary.md`

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
- source mem_type: GM, UB, L1
- api: move, slice, insert, pad
- dtype: FP16, FP32, INT8, INT16, INT32，按实际支持情况记录
- rank: 1D, 2D, 3D, 4D
- 边界维度: 1, 15, 16, 17, 31, 32, 33，以及真实大尺寸尾块
- `no_autopad=False` 与 `no_autopad=True`

完成标准：
- 至少 12 个不同 probe。
- 至少 3 个失败或异常 probe，并记录错误信息或异常生成产物。
- 至少 4 组围绕 16 和 32B 边界的实验族。
- `confirmed_rules`、`refuted_rules`、`anomalies`、`minimal_repros`、`artifact_correlations` 都非空。
- `open_questions` 为空。
- `next_steps` 为空。
- `scope_complete` 为 true。

回复要求：
- 全程使用中文回复。
- 不满足全部完成标准时，不允许回复 `DONE:`。
