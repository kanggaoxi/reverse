You are assigned to module `api_behavior`.

Target:
- Reverse engineer the black-box wheel at `/tmp/reverse_target/toycc_demo-0.1.0-py3-none-any.whl`.
- Treat it as a black-box target. Do not inspect any builder source outside the wheel.

Work only inside your current git worktree.

Required artifact layout:
- `results/api_behavior/probes/`
- `results/api_behavior/generated/`
- `results/api_behavior/status.json`
- `results/api_behavior/summary.md`

Required scope:
- Determine which `api:` names appear to be accepted.
- Compare at least 3 candidate APIs using otherwise similar inputs.
- Include at least 1 failing or suspicious case.
- Record whether generated outputs differ by API.

Turn discipline:
- In your first turn, do not mark the task complete.
- In your first turn, perform at least 2 concrete experiments and update `status.json` and `summary.md`.
- Stop after recording evidence. The supervisor may resume you.
- On later turns, continue until scope is complete, then reply with `DONE: api_behavior`.
