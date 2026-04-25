你负责 `l0_load_mmad_contract` 模块。

目标：
- 逆向 `move_to_l0A`、`move_to_l0B`、`move_to_l0C`、`slice_to_l0A`、`slice_to_l0B`、`mmad` 的契约。
- 重点观察 transpose、load3d、L0C broadcast-like 行为、16 对齐约束、L1 -> L0A/L0B -> MMAD -> L0C -> UB/GM 的完整路径。

主要参考：
- `akg/swft/python/swft/api/move.py`
- `akg/swft/python/swft/api/slicedata.py`
- `akg/swft/python/swft/api/compute.py`
- `akg/swft/docs/move.md`
- `akg/swft/docs/compute.md`
- `akg/swft/op_test/fusion/premla.py`
- `akg/swft/op_test/fusion/paged_attention_tp8_do_internal.py`

开始实验前必须先做环境自检：
- 记录当前工作目录、Python 版本、关键环境变量、SWFT/Ascend 环境初始化命令的输出。
- 执行一个最小 SWFT 编译或运行样例，确认确实能生成编译产物。
- 如果环境自检失败，必须把状态标为未完成，并记录失败命令和错误信息。

实验方法：
- 先构造最小 matmul 形状 probe，再对比复杂 op_test。
- transpose 和非 transpose 分开测。
- `load3d` 单独作为子面测试。
- 每个异常必须扩展成基线、单变量扰动、边界值、反例。
- 如果没有生成 `generated/<case>/` 或 `logs/<case>.txt`，这个 case 不能算通过。

产物目录：
- `swft-lab/results/l0_load_mmad_contract/probes/<case>.py`
- `swft-lab/results/l0_load_mmad_contract/generated/<case>/`
- `swft-lab/results/l0_load_mmad_contract/logs/<case>.txt`
- `swft-lab/results/l0_load_mmad_contract/status.json`
- `swft-lab/results/l0_load_mmad_contract/summary.md`

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
- move vs slice into L0A/L0B
- transpose false vs true
- load3d false vs true
- L0C 输出 shape 和 format
- 16x16 边界
- `mmad` 接受的 dtype 族

完成标准：
- 至少 10 个不同 probe。
- 至少 3 个失败或被拒绝的契约 case。
- 至少 2 个非 16 对齐尾维 probe。
- 至少 2 个 transpose 或 load3d probe。
- `confirmed_rules`、`refuted_rules`、`anomalies`、`minimal_repros`、`artifact_correlations` 都非空。
- `open_questions` 为空。
- `next_steps` 为空。
- `scope_complete` 为 true。

回复要求：
- 全程使用中文回复。
- 不满足全部完成标准时，不允许回复 `DONE:`。
