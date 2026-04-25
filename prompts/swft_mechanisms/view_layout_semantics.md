You own the `view_layout_semantics` module.

Scope:
- `change_view`, `reshape`, `transpose`, `nd_to_nz`, `nz_to_nd`
- shape reinterpretation vs real layout transform
- ND/NZ transitions
- 4D -> 2D flattening and follow-up slicing behavior

Primary references:
- `akg/swft/python/swft/api/transdata.py`
- `akg/swft/docs/tensor.md`
- `akg/swft/op_test/fusion/premla.py`
- `akg/swft/op_test/fusion/paged_attention_tp8_do_internal.py`

Method:
- Begin with the smallest possible tensors that still expose ordering issues.
- When a layout surprise appears, expand to baseline, one-variable delta, boundary case, and counterexample.
- Separate "logical view only" claims from "generated code inserted extra movement" claims.
- Record whether the observed behavior matches docs, code comments, or only experiment.

Required outputs under `swft-lab/results/view_layout_semantics/`:
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
- op: change_view, reshape, transpose, nd_to_nz, nz_to_nd
- rank: 1D, 2D, 3D, 4D
- shape collapse: 4D -> 2D, 3D -> 2D, 2D -> 3D where valid
- format: ND, NZ
- dtype changes through `change_view`
- follow-up ops after view change: slice, move, insert

Completion criteria:
- At least 10 distinct probes.
- At least 3 anomaly families where generated artifacts are inspected.
- At least 2 probes proving a rule and 2 probes disproving an over-generalized rule.
- `confirmed_rules`, `refuted_rules`, `anomalies`, `minimal_repros`, and `artifact_correlations` are all non-empty.
- `open_questions` is empty.
- `next_steps` is empty.
- `scope_complete` is true.

Do not reply with `DONE:` until every completion criterion is satisfied.
