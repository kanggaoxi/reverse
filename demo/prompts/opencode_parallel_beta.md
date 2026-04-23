You own the `beta` slice.

Work only inside your current git worktree.

Create and maintain:
- `results/beta/status.json`
- `results/beta/summary.md`
- `results/beta/probes/`

Round behavior:
- If `results/beta/status.json` does not exist yet:
  - Create `results/beta/probes/round1.txt` with a short note mentioning `beta round1`.
  - Create `results/beta/status.json` with:
    - `"module": "beta"`
    - `"scope_complete": false`
    - `"experiments": ["round1"]`
    - `"open_questions": ["add round2 evidence"]`
    - `"next_steps": ["create round2 probe and mark complete"]`
  - Create `results/beta/summary.md` saying this is only the first pass and more evidence is needed.
  - Reply with `DONE: beta first pass`

- If `results/beta/status.json` already exists:
  - Read it and finish the remaining work.
  - Create `results/beta/probes/round2.txt` with a short note mentioning `beta round2`.
  - Update `results/beta/status.json` so that:
    - `"scope_complete": true`
    - `"experiments"` contains both `round1` and `round2`
    - `"open_questions": []`
    - `"next_steps": []`
  - Update `results/beta/summary.md` to say the scope is now complete.
  - Reply with `DONE: beta complete`
