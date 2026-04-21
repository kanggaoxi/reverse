You own the CLI surface module.

Goal:
- Reverse engineer the toycc command line surface and the minimum valid DSL.

Work only in your assigned worktree.

Required outputs:
- A set of minimal probe inputs under `results/module_cli_surface/probes/`
- Generated outputs under `results/module_cli_surface/generated/`
- Structured notes in `results/module_cli_surface/summary.md`
- Machine-readable progress in `results/module_cli_surface/status.json`

Focus on:
- command shape
- required arguments
- minimum valid DSL
- output file names
- success vs failure signatures

Do not stop after a single probe. Keep making progress until your scope is exhausted.
When complete, reply with `DONE: module_cli_surface`.
