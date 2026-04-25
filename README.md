# Multi-Agent Reverse-Engineering Orchestrator

这个目录里的主监督程序用于把一个黑盒逆向任务拆给多个 CLI agent 并行推进。它最初用 `codex exec` 验证，但机制本身不绑定 Codex；只要你的 agent CLI 能被命令行启动，最好能支持 resume，并能把最终回复写到文件或输出 JSONL 事件，就可以接入。`opencode`、内部 agent CLI、或者一个包装脚本都可以作为后端。

核心脚本：

```bash
python3 scripts/orchestrate_agents.py --config <config.json>
```

## 适用场景

适合以下类型的逆向或黑盒探索任务：

- 逆向一个不开源 wheel、SDK、编译器、DSL 编译器或 CLI 工具。
- 多个 API 模块可以并行探索，例如语法、类型、算子、shape/alignment、codegen 产物。
- 每个 agent 需要反复写小样例、运行编译/执行命令、比较输出、记录规律。
- agent 容易“没做完就停”，需要主程序定时恢复和督促。
- 需要 judge agent 对 worker 的完成声明做二次验收。

典型 swft/Ascend C 场景可以这样拆：

- `syntax`: 探索 DSL 顶层语法、函数/核函数声明、输入输出声明。
- `types_shapes`: 探索 dtype、shape、rank、padding、32B/16x16 对齐行为。
- `ops_basic`: 探索 elementwise、broadcast、cast、reshape、transpose。
- `ops_cube`: 探索 matmul/cube/load/store 相关 API 到 `.cce` 的生成规律。

## 工作方式

主程序为每个 worker 做这些事：

1. 创建或复用一个 git worktree。
2. 用不同 prompt 启动一个 agent CLI 进程。
3. 持续读取 agent 输出，保存 JSONL 事件日志。
4. 记录 `session_id`、最后回复、退出码、轮次、是否提出完成。
5. 进程退出后决定是否 resume、retry、stall recovery 或进入 judge。
6. 如果 worker 回复 `DONE:`，只视为“提议完成”，不会直接结束。
7. 如果开启 judge，主程序启动 judge agent 读取 worker 的最后回复、`status.json` 和 `summary.md`。
8. 只有 judge 返回 `JUDGE_JSON: {"decision":"done", ...}`，任务才真正结束。

状态转移的关键点：

```text
worker running
worker exits without DONE -> judge/continue or nudge resume
worker exits with DONE -> proposed_done
judge says continue -> resume worker with judge next_instruction
judge says retry -> resume worker with recovery prompt
judge says blocked -> resume worker with stall prompt
judge says done -> done(judge)
```

## 目录和产物

建议每个 worker 在自己的 worktree 里维护固定结构：

```text
results/<module>/
  status.json
  summary.md
  probes/
  generated/
  diffs/
  logs/
```

推荐 `status.json` 结构：

```json
{
  "module": "ops_cube",
  "scope_complete": false,
  "apis_covered": [],
  "experiments": [],
  "alignment_cases": [],
  "cce_comparisons": [],
  "known_failures": [],
  "open_questions": [],
  "next_steps": []
}
```

judge 的可靠性主要来自这些结构化字段，而不是模型主观判断。不要只让 worker 写一段自然语言总结。

## 配置文件总览

最小配置示意：

```json
{
  "repo_root": "/path/to/repo",
  "base_branch": "main",
  "state_dir": ".orchestrator",
  "agent_cli": "codex",
  "model": "gpt-5.4",
  "enable_judge": true,
  "require_judge_approval": true,
  "judge_model": "gpt-5.4",
  "status_interval": 30,
  "stall_seconds": 900,
  "max_rounds": 5,
  "max_retries": 2,
  "extra_agent_args": [
    "--add-dir",
    "/path/to/readonly/target"
  ],
  "common_prompt": "You are one worker in a coordinated reverse-engineering effort...",
  "judge_common_prompt": "You are a strict supervisor judge...",
  "nudge_prompt": "Continue `{agent_name}` in `{worktree}`...",
  "recovery_prompt": "The previous run ended unexpectedly...",
  "stall_prompt": "The previous run appears stalled...",
  "agents": [
    {
      "name": "ops-cube",
      "branch": "explore/ops-cube",
      "worktree": "/tmp/myproj-ops-cube",
      "prompt_file": "prompts/ops_cube.md",
      "status_file": "results/ops_cube/status.json",
      "max_rounds": 6
    }
  ]
}
```

重要字段：

- `repo_root`: 主 git repo 路径。主程序会在这里创建 worktree。
- `base_branch`: 新 worktree 分支从哪个分支切出。
- `state_dir`: 主程序自己的状态和日志目录。
- `agent_cli`: 后端 agent 命令，默认是 `codex`。
- `model`: worker 使用的模型名。是否生效取决于你的 CLI 模板。
- `enable_judge`: 是否启用 judge。
- `require_judge_approval`: 是否要求 judge 批准后才能真正结束。建议逆向任务设为 `true`。
- `judge_only_on_proposed_done`: 是否只在 worker 明确回复 `DONE:` 后才运行 judge。严格模式建议设为 `true`。
- `judge_model`: judge 使用的模型。
- `status_interval`: 主程序打印状态的间隔秒数。
- `stall_seconds`: 多久没有输出就视为可能停滞。
- `max_rounds`: 一个 worker 最多被恢复多少轮。
- `max_retries`: 非 0 退出码最多重试次数。
- `extra_agent_args`: 给所有 agent CLI 追加的参数，例如额外只读目录、权限选项。
- `common_prompt`: 每个 worker 都会收到的共同规则。
- `agents[].prompt_file`: 每个模块自己的任务说明。
- `agents[].status_file`: judge 会读取的结构化状态文件。
- `completion_checks`: 主程序的确定性完成门禁。可要求必须存在哪些目录、`status.json` 必须有哪些 key、最少多少 probe、每个 probe 是否都要有 `generated/` 和 `logs/` 对应产物。

兼容旧字段：

- `codex_bin` 仍可用，但新配置建议用 `agent_cli`。
- `extra_codex_args` 仍可用，但新配置建议用 `extra_agent_args`。

## 接入 Codex

如果使用 Codex CLI，并且你的环境已经通过 `cc-switch` 或其他方式配置好了 provider，通常直接这样写即可：

```json
{
  "agent_cli": "codex",
  "model": "gpt-5.4",
  "full_auto": true,
  "json_output": true,
  "extra_agent_args": [
    "--add-dir",
    "/path/to/target"
  ]
}
```

默认启动命令等价于：

```bash
codex exec --full-auto --json -m <model> -o <last_message_path> -C <worktree> <prompt>
```

默认恢复命令等价于：

```bash
codex exec --full-auto --json -m <model> -o <last_message_path> resume <session_id> <prompt>
```

如果 `agent_cli` 的 basename 是 `opencode`，当前脚本会原生切换到 opencode 协议，不再走上面的 Codex 风格命令。默认等价命令为：

```bash
opencode run --dangerously-skip-permissions --format json --model <model> --dir <worktree> <prompt>
opencode run --dangerously-skip-permissions --format json --model <model> --dir <worktree> --session <session_id> <prompt>
```

脚本会自动从 opencode JSONL 事件里提取：

- 顶层 `sessionID` 作为会话 id
- `{"type":"text","part":{"text":"..."}}` 里的文本作为最后回复

judge 在 opencode 后端下也会直接从 JSONL 事件重建文本，不再依赖 `-o` 输出文件。

## 接入 opencode 或内部 CLI

不同 agent CLI 的参数不一样，所以最稳妥的做法是写一个 wrapper，让它暴露一套稳定接口，然后在配置里通过 command template 调用。

现在对 `opencode` 已经有一层内建适配，所以如果你直接使用官方 CLI，通常不需要再写 wrapper。更推荐在配置里把 `agent_cli` 写成绝对路径，例如：

```json
{
  "agent_cli": "/home/your-user/.opencode/bin/opencode"
}
```

这是因为很多机器的非交互 shell 不会加载 `.bashrc` 里追加的 PATH。

推荐 wrapper 支持三个动作：

```bash
agent-wrapper start  --worktree <path> --model <model> --out <last.txt> --prompt <prompt>
agent-wrapper resume --session <id> --model <model> --out <last.txt> --prompt <prompt>
agent-wrapper judge  --worktree <repo> --model <model> --out <judge.txt> --prompt <prompt>
```

如果 opencode 没有稳定 session resume，可以让 wrapper 自己保存会话信息，或者把 `resume_requires_session` 设为 `false`，并让 `resume_command_template` 通过历史文件重新构造上下文。

模板配置示意：

```json
{
  "agent_cli": "/path/to/agent-wrapper",
  "model": "your-model-name",
  "resume_requires_session": false,
  "initial_command_template": [
    "{agent_cli}",
    "start",
    "--worktree",
    "{worktree}",
    "--model",
    "{model}",
    "--out",
    "{last_message_path}",
    "--prompt",
    "{prompt}",
    "{global_extra_args}",
    "{agent_extra_args}"
  ],
  "resume_command_template": [
    "{agent_cli}",
    "resume",
    "--worktree",
    "{worktree}",
    "--session",
    "{session_id}",
    "--model",
    "{model}",
    "--out",
    "{last_message_path}",
    "--prompt",
    "{prompt}",
    "{global_extra_args}",
    "{agent_extra_args}"
  ],
  "judge_command_template": [
    "{agent_cli}",
    "judge",
    "--worktree",
    "{repo_root}",
    "--model",
    "{model}",
    "--out",
    "{last_message_path}",
    "--prompt",
    "{prompt}",
    "{global_extra_args}"
  ]
}
```

可用模板变量：

- `{agent_cli}`
- `{model}`
- `{prompt}`
- `{session_id}`
- `{worktree}`
- `{repo_root}`
- `{last_message_path}`
- `{agent_name}`
- `{branch}`
- `{state_dir}`
- `{global_extra_args}`
- `{agent_extra_args}`

CLI 输出兼容要求：

- 最好输出 JSONL。
- 如果输出 `{"type":"thread.started","thread_id":"..."}`，主程序会记录 session id。
- 如果输出 `{"type":"item.completed","item":{"type":"agent_message","text":"..."}}`，主程序会把 `text` 写入 `last_message_path`。
- 如果 CLI 不输出 JSONL，也可以由 wrapper 直接把最终回复写到 `--out` 指定路径。

## 在逆向场景里该填什么

把环境信息放在 `common_prompt` 或模块 prompt 里。不要只口头告诉 agent，必须写成明确命令。

建议包括：

```text
Target:
- swft compiler path: /opt/internal/swft/bin/swft
- DSL docs path: /data/swft/docs
- Example path: /data/swft/examples
- Ascend C env setup: source /usr/local/Ascend/ascend-toolkit/set_env.sh

Compile command:
- swftc <input.dsl> --emit-cce --out <out_dir>

Run command:
- bash tools/run_case.sh <out_dir>

Compare command:
- python3 tools/compare_outputs.py --golden <golden.npy> --actual <actual.npy>

Required outputs:
- Save every DSL probe under results/<module>/probes/
- Save generated .cce under results/<module>/generated/
- Save compiler stdout/stderr under results/<module>/logs/
- Update results/<module>/status.json after every turn
- Update results/<module>/summary.md after every turn
```

把原始输入有哪些也写清楚，例如：

```text
Input materials:
- DSL grammar notes: docs/swft_syntax.md
- Existing kernels: examples/
- ONNX model: models/model.onnx
- Operator split list: ops/operator_slices.json
- Golden tensors: testdata/golden/
```

把完成标准写成 checklist，例如：

```text
Completion criteria:
- At least 8 successful probes.
- At least 3 failing probes with error messages recorded.
- At least 2 non-32B-aligned shape cases.
- At least 2 16x16 boundary cases.
- For each successful probe, compare DSL, generated .cce, host code, and runtime output.
- status.json must set scope_complete=true only after all criteria are satisfied.
- Final reply must begin with DONE: <module>.
```

## Prompt 文件建议

每个模块 prompt 应该包含：

- 模块边界：这个 worker 负责什么，不负责什么。
- 可用资料：docs/examples/model/testdata 的路径。
- 必须使用的命令：环境初始化、编译、运行、比较。
- 实验产物路径：probes/generated/logs/diffs。
- 结构化状态字段：`status.json` 必须有哪些 key。
- 完成标准：什么情况下可以回复 `DONE:`。
- 禁止事项：不要改其他 worker 的目录，不要删除已有证据，不要凭猜测下结论。
- 异常扩展规则：一旦发现异常，必须继续做 `baseline + 单变量扰动 + 边界值 + 反例` 四联实验，而不是只记录一个现象。

示例片段：

```text
You own the `types_shapes` slice.

Use:
- source /usr/local/Ascend/ascend-toolkit/set_env.sh
- /opt/internal/swft/bin/swftc <probe.dsl> --emit-cce --out <out_dir>
- python3 tools/check_case.py <out_dir>

Explore:
- dtype spellings
- shape syntax
- fp16/fp32 32B alignment
- 16x16 cube boundary
- what happens when input shape is not aligned

Write:
- results/types_shapes/probes/*.dsl
- results/types_shapes/generated/<case>/
- results/types_shapes/logs/<case>.txt
- results/types_shapes/status.json
- results/types_shapes/summary.md

Do not reply DONE until status.json has scope_complete=true and all checklist items are satisfied.
```

如果你的目标是让 agent 反推出编译器规律，而不是只补几个 case，建议直接按机制拆模块。仓库里已经提供一套更适合 SWFT 的示例：

- 配置文件：[scripts/swft_agents.mechanisms.example.json](/home/kgx/code/kernel/reverse/scripts/swft_agents.mechanisms.example.json)
- prompt 目录：[prompts/swft_mechanisms](/home/kgx/code/kernel/reverse/prompts/swft_mechanisms)

这些 prompt 默认按下面的机制切片：

- `memmove_autopad_alignment`
- `view_layout_semantics`
- `slice_concat_semantics`
- `l0_load_mmad_contract`
- `dtype_conversion_mixed_precision`
- `multicore_partition_sync`

## Judge 设计

建议开启：

```json
{
  "enable_judge": true,
  "require_judge_approval": true
}
```

这样 worker 的 `DONE:` 只是提议完成。judge 会读取：

- worker 最后回复
- `status.json`
- 同目录 `summary.md`

当前脚本还会先跑一层 deterministic pre-check，再决定是否允许进入 judge。默认严格模式下，它会拦截这些情况：

- `status.json` 缺失或不是合法 JSON
- `summary.md` 缺失或为空
- `scope_complete != true`
- `open_questions` 非空
- `next_steps` 非空
- 缺少必需目录，例如 `probes/`、`generated/`、`logs/`
- probe 数量、generated 数量、log 数量低于配置阈值
- 某些 probe 没有对应的 generated 或 log 产物

也就是说，worker 先说 `DONE:` 并不会直接触发宽松验收。主程序会先做确定性门禁；门禁不过，worker 会被强制恢复继续补证据。

judge 需要输出一行：

```text
JUDGE_JSON: {"decision":"done","reason":"...","next_instruction":"..."}
```

可选 decision：

- `done`: 验收通过，真正结束。
- `continue`: 证据不足，继续实验。
- `retry`: 上一轮失败或状态不一致，恢复重试。
- `blocked`: 需要换策略或处理阻塞。

分歧处理原则：

- worker 说 `DONE`，judge 说 `continue`：继续，以 judge 的 `next_instruction` 督促 worker 补证据。
- worker 没说 `DONE`，judge 说 `done`：可以结束，但不建议这样设计；最好要求 worker 和 status 都明确完成。
- judge 不可用：不会直接结束，会进入 `judge-unavailable` 并尝试 stall recovery。

当前严格模式下还做了两件事：

- judge 默认只在 worker 明确回复 `DONE:` 后才运行，不会在普通成功退出后就提前放行。
- 如果一个回合结束后没有任何证据变化，例如 probe 列表、generated 列表、logs 列表、`status.json` 或 `summary.md` 都没变，主程序会把它当成 `no-progress`，转入更强的 stall recovery 提示，而不是当成有效推进。

## 运行和监控

启动：

```bash
python3 scripts/orchestrate_agents.py --config path/to/config.json
```

查看状态：

```bash
ls .orchestrator
cat .orchestrator/<agent>.state.json
tail -f .orchestrator/<agent>.events.log
cat .orchestrator/<agent>.last.txt
cat .orchestrator/<agent>.judge.last.txt
```

状态字段含义：

- `done`: 是否真正结束。
- `proposed_done`: worker 是否已经回复 `DONE:`。
- `last_status`: 当前状态，例如 `running`、`waiting-resume`、`proposed-done`、`done(judge)`。
- `round_index`: 已完成轮次。
- `judge_runs`: judge 执行次数。
- `session_id`: agent CLI 暴露的会话 id。
- `last_exit_code`: 最近一次 agent 进程退出码。
- `pending_prompt`: 下一次恢复时使用哪类提示，例如 `nudge`、`recovery`、`stall`。
- `raw_event_count`: 已读取的原始输出行数。一直不增长通常说明 agent 进程没有输出。
- `json_event_count`: 已成功解析的 JSONL 事件数。如果 raw 增长但 json 不增长，说明后端输出格式和脚本预期不匹配。
- `last_event_ts`: 最近一次收到输出的时间戳。
- `last_spawn_ts`: 最近一次启动 agent 进程的时间戳。
- `stall_warnings`: 被判定为长时间无输出的次数。
- `spawn_artifact_snapshot`: 本轮启动前的产物快照。
- `last_artifact_snapshot`: 本轮退出后的产物快照。
- `last_run_had_artifact_delta`: 本轮是否产生了文件层面的证据变化。

监督进程重启后，会从 state 文件恢复 `pending_prompt`，继续那些已经明确进入 `continue`、`retry`、`stall` 路径的 worker。对于 `proposed-done` 和 `awaiting-judge` 这类等待 judge 的状态，主程序不会跳过 judge 直接恢复 worker。

每个 agent 会在 `state_dir` 下生成这些监督文件：

- `<agent>.state.json`: 主程序状态文件。用于恢复进度，也是定位卡住问题的第一入口。
- `<agent>.events.log`: agent 的原始 stdout 日志，包括 opencode JSONL 事件和主程序追加的 spawn/stall/judge 记录。
- `<agent>.last.txt`: 主程序提取出的 worker 最后一段自然语言回复。下一轮恢复 prompt 会引用它。
- `<agent>.judge.last.txt`: judge 最后一轮回复。只有开启 judge 后才会出现。

每个 worker 自己应该在 worktree 里生成这些探索产物：

- `swft-lab/results/<module>/status.json`: 结构化进度和结论。
- `swft-lab/results/<module>/summary.md`: 人类可读总结。
- `swft-lab/results/<module>/probes/`: 每个最小实验的源文件。
- `swft-lab/results/<module>/generated/`: 每个 probe 对应的编译产物目录。
- `swft-lab/results/<module>/logs/`: 每个 probe 对应的命令输出日志。

## 办公机排障

如果某个 worktree 卡在第一轮，先看主程序状态：

```bash
cat .orchestrator/<agent>.state.json
tail -n 80 .orchestrator/<agent>.events.log
ps -fp <pid>
```

判断方法：

- `last_status=running` 且 `raw_event_count=0`: opencode 进程启动了但没有输出。优先检查 opencode 是否在等待交互、模型是否可用、权限是否卡住。
- `raw_event_count` 增长但 `json_event_count=0`: opencode 输出不是脚本预期的 JSONL，检查是否缺了 `--format json` 或版本行为不同。
- `last_status=stalled>...` 且 pid 仍存在: agent 长时间无输出。建议配置 `interrupt_stalled=true`，脚本会中断并用 `stall_prompt` 恢复。
- `session_id` 为空: 第一轮还没拿到 opencode session。当前脚本会在无 session 时用新会话继续恢复，不再强依赖 `--session`。
- `last_exit_code` 非 0 且 `retry_count` 连续增长: 后端命令或环境命令失败。看 `<agent>.events.log` 的最后错误，而不是只看 `status.json`。

如果 `status.json` 写了很多 pass，但 `generated/` 和 `logs/` 是空的，按下面顺序排查：

```bash
find <worktree>/swft-lab/results/<module> -maxdepth 3 -type f | sort
cat <worktree>/swft-lab/results/<module>/status.json
cat .orchestrator/<agent>.last.txt
tail -n 120 .orchestrator/<agent>.events.log
```

判断方法：

- `probes/` 为空: worker 没有真正开始做实验，属于 agent 执行质量或 prompt 约束不足。
- `probes/` 有文件但 `generated/` 为空: 编译命令没有跑成功，或 prompt 没写清楚产物路径。
- `logs/` 为空: worker 没有保存命令输出，结论不可验收。
- `status.json` 说 pass 但没有对应 generated/log: 这是 worker 幻觉或偷懒，不应认为任务完成。严格配置里的 `completion_checks` 会拦住这种 DONE。
- `known_failures` 记录 NPU 环境缺失，但你确认机器有 NPU: 看 prompt 里是否写了真实环境初始化命令，例如 `source .../set_env.sh`，以及 agent 是否真的执行了自检命令。

为了让另一台机器不改代码直接跑，配置里需要把机器差异全部写清楚：

- `agent_cli`: opencode 绝对路径。
- `model` 和 `judge_model`: opencode 中真实可用的模型名。
- `repo_root`: 仓库根目录。
- `worktree`: 每个模块的 worktree 目标路径。
- SWFT 环境初始化命令。
- 最小 SWFT 编译命令和预期产物路径。
- NPU/Ascend 自检命令。
- 只读资料路径，例如文档、模型、测试数据。
- 是否允许中断卡住进程，通常办公机建议 `interrupt_stalled=true`。

## 权限和安全

不要默认给 agent 无限权限。更稳妥的做法：

- 每个 worker 只写自己的 worktree。
- 目标 wheel、SDK、模型、文档用只读路径传入。
- 编译输出写到 `results/<module>/generated/`。
- 不允许 worker 删除其他 worker 的结果。
- 需要联网、安装依赖、写系统目录时，由 wrapper 或外层审批控制。

如果你确实要给内部 agent 全权限，建议只在隔离机器或容器里做，并把所有实验输入输出路径固定下来，避免误删真实工程。

## 已验证能力

当前 demo 已验证：

- 多 worker 并行启动。
- 每个 worker 独立 worktree。
- worker 停下后通过 session resume 继续推进。
- judge 能读取 worker 产物并返回 `continue`。
- worker 回复 `DONE:` 后不会直接结束。
- 只有 judge 返回 `done` 后，状态才变成 `done(judge)`。

## 当前限制

- 默认命令格式仍以 Codex CLI 兼容为基线。
- 非 Codex/opencode CLI 建议通过 wrapper 接入。
- 监督器只能判断进程和文件状态，不能保证实验语义完全正确。
- judge 不是天然正确，必须依赖结构化 `status.json` 和明确 checklist。
- 如果后端 CLI 不支持 resume，恢复效果取决于 wrapper 如何重建上下文。
