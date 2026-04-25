You own the `slice_concat_semantics` module.

Scope:
- `slice_to_ub`, `slice_to_l1`, `slice_to_l0A`, `slice_to_l0B`
- `split_to_*`, `concat`, `concat_to_l1`, `concat_to_gm`, `insert_to_gm`
- begin and size semantics
- order preservation vs hidden reorder

Primary references:
- `akg/swft/python/swft/api/slicedata.py`
- `akg/swft/docs/slicedata.md`
- `akg/swft/op_test/fusion/premla.py`
- `akg/swft/op_test/fusion/moe_token_unpermute.py`

Method:
- Keep probes minimal and isolate one transformation at a time.
- Treat unexpected reorder as a first-class anomaly and grow it into a family of repros.
- Compare forward path and write-back path separately.
- Distinguish generic slice behavior from L0A/L0B-specific movement behavior.

Required outputs under `swft-lab/results/slice_concat_semantics/`:
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
- op family: slice, split, concat, insert
- destination mem_type: UB, L1, L0A, L0B, GM
- rank: 1D, 2D, 3D, 4D
- contiguous vs tail slices
- negative evidence for assumptions such as "slice never reorders"

Completion criteria:
- At least 10 distinct probes.
- At least 3 failing or anomalous probes with preserved evidence.
- At least 2 round-trip experiments: slice then insert, split then concat.
- `confirmed_rules`, `refuted_rules`, `anomalies`, `minimal_repros`, and `artifact_correlations` are all non-empty.
- `open_questions` is empty.
- `next_steps` is empty.
- `scope_complete` is true.

Do not reply with `DONE:` until every completion criterion is satisfied.
