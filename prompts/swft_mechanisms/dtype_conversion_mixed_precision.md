You own the `dtype_conversion_mixed_precision` module.

Scope:
- `move_to_ub(dtype=...)`
- `vconv`
- mixed-precision flows around move, view, and compute
- explicitly test documented dtypes first, then test suspected but undocumented dtypes as hypotheses

Primary references:
- `akg/swft/python/swft/api/compute.py`
- `akg/swft/python/swft/api/move.py`
- `akg/swft/docs/compute.md`
- `akg/swft/docs/tensor.md`
- `akg/swft/op_test/fusion/paged_attention_tp8_do_internal.py`
- `akg/swft/op_test/bmm/t_bmm_t_tp8_th.py`

Method:
- Split the work into two tables:
  documented support vs experimentally observed support.
- Never assume FP8 is supported just because a related test name contains `tp8`.
- For each conversion path, record where failure happens:
  API validation, compilation, generated artifact, or runtime.
- Expand every surprising accept/reject into baseline, one-variable delta, boundary, counterexample.

Required outputs under `swft-lab/results/dtype_conversion_mixed_precision/`:
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
- source dtype and destination dtype
- move-time conversion vs explicit `vconv`
- conversion with ND vs NZ tensors
- conversion before and after `change_view`
- documented dtypes vs suspected extra dtypes such as FP8

Completion criteria:
- At least 10 distinct probes.
- At least 4 failing probes with precise failure stage recorded.
- At least one table that separates documented support from observed support.
- `confirmed_rules`, `refuted_rules`, `anomalies`, `minimal_repros`, and `artifact_correlations` are all non-empty.
- `open_questions` is empty.
- `next_steps` is empty.
- `scope_complete` is true.

Do not reply with `DONE:` until every completion criterion is satisfied.
