You own the `l0_load_mmad_contract` module.

Scope:
- `move_to_l0A`, `move_to_l0B`, `move_to_l0C`
- `slice_to_l0A`, `slice_to_l0B`
- `mmad`
- transpose, load3d, L0C broadcast-like behavior, and 16-alignment expectations

Primary references:
- `akg/swft/python/swft/api/move.py`
- `akg/swft/python/swft/api/slicedata.py`
- `akg/swft/python/swft/api/compute.py`
- `akg/swft/docs/move.md`
- `akg/swft/docs/compute.md`
- `akg/swft/op_test/fusion/premla.py`
- `akg/swft/op_test/fusion/paged_attention_tp8_do_internal.py`

Method:
- Build minimal matmul-shaped probes before touching fused kernels.
- Test transpose and non-transpose separately.
- Treat `load3d` as its own sub-surface.
- Check the contract across L1 -> L0A/L0B -> MMAD -> L0C -> UB/GM.

Required outputs under `swft-lab/results/l0_load_mmad_contract/`:
- `probes/<case>.py`
- `generated/<case>/`
- `logs/<case>.txt`
- `status.json`
- `summary.md`

Required `status.json` keys:
- `module`
- `scope_complete`
- `hypotheses`
- `coverage_matrix`
- `confirmed_rules`
- `refuted_rules`
- `anomalies`
- `minimal_repros`
- `artifact_correlations`
- `open_questions`
- `next_steps`

Coverage axes:
- move vs slice into L0A/L0B
- transpose false vs true
- load3d false vs true
- L0C output shape and format
- 16x16 boundary cases
- dtype families accepted by `mmad`

Completion criteria:
- At least 10 distinct probes.
- At least 3 failing or rejected contract cases.
- At least 2 probes around non-16-aligned last dimensions.
- At least 2 probes around transpose or load3d.
- `confirmed_rules`, `refuted_rules`, `anomalies`, `minimal_repros`, and `artifact_correlations` are all non-empty.
- `open_questions` is empty.
- `next_steps` is empty.
- `scope_complete` is true.

Do not reply with `DONE:` until every completion criterion is satisfied.
