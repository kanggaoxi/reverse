You are assigned to module `codegen_patterns`.

Target:
- Reverse engineer the black-box wheel at `/tmp/reverse_target/toycc_demo-0.1.0-py3-none-any.whl`.
- Treat it as a black-box target. Do not inspect any builder source outside the wheel.

Work only inside your current git worktree.

Required artifact layout:
- `results/codegen_patterns/probes/`
- `results/codegen_patterns/generated/`
- `results/codegen_patterns/status.json`
- `results/codegen_patterns/summary.md`

Required scope:
- Compare `compile.json`, `kernel.cce`, and `host.cpp`.
- Determine where inferred lowering decisions show up.
- Include at least 2 contrasting probes.
- Record stable mapping rules in structured markdown.

Turn discipline:
- In your first turn, do not mark the task complete.
- In your first turn, perform at least 2 concrete experiments and update `status.json` and `summary.md`.
- Stop after recording evidence. The supervisor may resume you.
- On later turns, continue until scope is complete, then reply with `DONE: codegen_patterns`.
