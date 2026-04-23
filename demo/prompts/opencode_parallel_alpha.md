You own the `alpha` slice.

Work only inside your current git worktree.

Create and maintain:
- `results/alpha/status.json`
- `results/alpha/summary.md`
- `results/alpha/probes/`

Round behavior:
- If `results/alpha/status.json` does not exist yet:
  - Create `results/alpha/probes/round1.txt` with a short note mentioning `alpha round1`.
  - Create `results/alpha/status.json` with:
    - `"module": "alpha"`
    - `"scope_complete": false`
    - `"experiments": ["round1"]`
    - `"open_questions": ["add round2 evidence"]`
    - `"next_steps": ["create round2 probe and mark complete"]`
  - Create `results/alpha/summary.md` saying this is only the first pass and more evidence is needed.
  - Reply with `DONE: alpha first pass`

- If `results/alpha/status.json` already exists:
  - Read it and finish the remaining work.
  - Create `results/alpha/probes/round2.txt` with a short note mentioning `alpha round2`.
  - Update `results/alpha/status.json` so that:
    - `"scope_complete": true`
    - `"experiments"` contains both `round1` and `round2`
    - `"open_questions": []`
    - `"next_steps": []`
  - Update `results/alpha/summary.md` to say the scope is now complete.
  - Reply with `DONE: alpha complete`
