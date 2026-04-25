你负责 `view_layout_semantics` 模块。

目标：
- 逆向 `change_view`、`reshape`、`transpose`、`nd_to_nz`、`nz_to_nd` 的视图、shape 和 layout 语义。
- 重点观察逻辑 shape 改变是否会引入真实数据重排，ND/NZ 转换是否触发隐式补齐，4D 压成 2D 后再 slice 是否保持顺序。

主要参考：
- `swft_op_example/lib/swft/api/transdata.py`
- `swft_op_example/docs/tensor.md`
- `swft_op_example/op_test/fusion/premla.py`
- `swft_op_example/op_test/fusion/paged_attention_tp8_do_internal.py`

环境准备：
- 运行任何 SWFT 命令前，必须先执行：`source /usr1/project/k00909889/swft_reverse/.venv/bin/activate`
- SWFT 包通过虚拟环境中的 pip install 安装，import 路径为 `import swft`。你可以通过 `python3 -c "import swft; print(swft.__file__)"` 找到实际安装路径来阅读源码。如果 `swft_op_example/lib/` 下的目录结构与上面列出的路径不完全匹配，请以实际 import 路径为准，同时参考 `swft_op_example/docs/` 和 `swft_op_example/op_test/` 中的内容。

开始实验前必须先做环境自检：
- 记录当前工作目录、Python 版本、关键环境变量、SWFT/Ascend 环境初始化命令的输出。
- 执行一个最小 SWFT 编译或运行样例，确认确实能生成编译产物。
- 如果环境自检失败，必须把状态标为未完成，并记录失败命令和错误信息。

实验方法：
- 用最小 tensor 暴露数据顺序问题。
- 出现 layout 异常时，必须扩展成基线、单变量扰动、边界值、反例。
- 区分“只是逻辑 view”与“生成代码插入了额外搬运或重排”。
- 每条结论必须标明依据来自文档、源码还是实验。
- 如果没有生成 `generated/<case>/` 或 `logs/<case>.txt`，这个 case 不能算通过。

产物目录：
- `swft-lab/results/view_layout_semantics/probes/<case>.py`
- `swft-lab/results/view_layout_semantics/generated/<case>/`
- `swft-lab/results/view_layout_semantics/logs/<case>.txt`
- `swft-lab/results/view_layout_semantics/status.json`
- `swft-lab/results/view_layout_semantics/summary.md`

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
- op: change_view, reshape, transpose, nd_to_nz, nz_to_nd
- rank: 1D, 2D, 3D, 4D
- shape collapse: 4D -> 2D, 3D -> 2D, 2D -> 3D，按实际可行性记录
- format: ND, NZ
- `change_view` 中的 dtype/format/shape 组合变化
- view 后接 slice、move、insert 的行为

完成标准：
- 至少 10 个不同 probe。
- 至少 3 组检查生成产物的异常实验族。
- 至少 2 个证明规则的 probe，至少 2 个反驳过度泛化规则的 probe。
- `confirmed_rules`、`refuted_rules`、`anomalies`、`minimal_repros`、`artifact_correlations` 都非空。
- `open_questions` 为空。
- `next_steps` 为空。
- `scope_complete` 为 true。

回复要求：
- 全程使用中文回复。
- 不满足全部完成标准时，不允许回复 `DONE:`。
