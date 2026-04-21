You own the shapes and alignment module.

Goal:
- Reverse engineer how toycc lowers shapes, especially when the last dimension is not aligned.

Required focus:
- fp16 and fp32
- 32B alignment
- 16x16 alignment behavior
- whether shape is silently padded
- whether generated `.cce` reveals lowering differences

Required outputs:
- probes covering aligned and unaligned cases
- generated artifacts
- structured notes in `results/module_shapes_alignment/summary.md`
- machine-readable progress in `results/module_shapes_alignment/status.json`

Do not stop after writing notes. Keep running new probes until coverage is convincing.
When complete, reply with `DONE: module_shapes_alignment`.
