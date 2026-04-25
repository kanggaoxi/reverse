You own the `memmove_autopad_alignment` module.

Scope:
- `move_to_gm`, `move_to_ub`, `move_to_l1` in `akg/swft/python/swft/api/move.py`
- `slice_to_ub`, `pad_to_ub`, `insert_to_gm` in `akg/swft/python/swft/api/slicedata.py`
- tail alignment, implicit padding, `no_autopad`, 32B boundary behavior, 16x16 boundary behavior

Primary references:
- `akg/swft/python/swft/api/move.py`
- `akg/swft/python/swft/api/slicedata.py`
- `akg/swft/docs/move.md`
- `akg/swft/docs/slicedata.md`
- `akg/swft/op_test/fusion/premla.py`

Method:
- Start from minimal probes, not large fusion kernels.
- Every anomaly must be expanded into an experiment family:
  baseline, one-variable delta, boundary case, counterexample.
- Distinguish documented behavior from experimentally observed behavior.
- Record exact commands in per-case logs.
- For each successful probe, compare source DSL or Python probe, generated artifacts, and runtime output.

Required outputs under `swft-lab/results/memmove_autopad_alignment/`:
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
- source mem_type: GM, UB, L1
- api: move vs slice vs insert vs pad
- dtype: FP16, FP32, INT8, INT16, INT32 where accepted
- rank: 1D, 2D, 3D, 4D
- boundary dims: 1, 15, 16, 17, 31, 32, 33 and realistic larger tails
- `no_autopad=False` vs `True`

Completion criteria:
- At least 12 distinct probes.
- At least 3 failing probes with recorded error messages or unexpected generated-artifact evidence.
- At least 4 explicit boundary families around 16 and 32B thresholds.
- `confirmed_rules`, `refuted_rules`, `anomalies`, `minimal_repros`, and `artifact_correlations` are all non-empty.
- `open_questions` is empty.
- `next_steps` is empty.
- `scope_complete` is true.

Do not reply with `DONE:` until every completion criterion is satisfied.
