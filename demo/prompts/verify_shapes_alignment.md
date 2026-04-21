You are assigned to module `shapes_alignment`.

Target:
- Reverse engineer the black-box wheel at `/tmp/reverse_target/toycc_demo-0.1.0-py3-none-any.whl`.
- Treat it as a black-box target. Do not inspect any builder source outside the wheel.

Work only inside your current git worktree.

Required artifact layout:
- `results/shapes_alignment/probes/`
- `results/shapes_alignment/generated/`
- `results/shapes_alignment/status.json`
- `results/shapes_alignment/summary.md`

Required scope:
- Determine shape lowering behavior for aligned and unaligned cases.
- Cover fp16 and fp32.
- Explicitly test cases relevant to 32B alignment and 16x16 alignment.
- Record whether output artifacts reveal silent padding or lowering changes.

Turn discipline:
- In your first turn, do not mark the task complete.
- In your first turn, perform at least 3 concrete experiments and update `status.json` and `summary.md`.
- Stop after recording evidence. The supervisor may resume you.
- On later turns, continue until scope is complete, then reply with `DONE: shapes_alignment`.
