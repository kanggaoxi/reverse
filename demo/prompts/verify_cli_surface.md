You are assigned to module `cli_surface`.

Target:
- Reverse engineer the black-box wheel at `/tmp/reverse_target/toycc_demo-0.1.0-py3-none-any.whl`.
- Treat it as a black-box target. Do not inspect any builder source outside the wheel.

Work only inside your current git worktree.

Required artifact layout:
- `results/cli_surface/probes/`
- `results/cli_surface/generated/`
- `results/cli_surface/status.json`
- `results/cli_surface/summary.md`

Required scope:
- Identify the entry point or invocation path from the wheel itself.
- Find the minimum valid invocation that succeeds.
- Capture at least one failing invocation.
- Record output file names and success/failure signatures.

Turn discipline:
- In your first turn, do not mark the task complete.
- In your first turn, perform at least 2 concrete experiments and update `status.json` and `summary.md`.
- Stop after recording evidence. The supervisor may resume you.
- On later turns, continue until scope is complete, then reply with `DONE: cli_surface`.
