You own the `multicore_partition_sync` module.

Scope:
- `get_block_idx`
- `sync_cores`
- per-core slicing, per-core tails, shared GM write-back, and multi-core movement rules

Primary references:
- `akg/swft/python/swft/api/context.py`
- `akg/swft/python/swft/api/sync.py`
- `akg/swft/docs/core.md`
- `akg/swft/op_test/fusion/moe_token_unpermute.py`
- `akg/swft/op_test/fusion/premla.py`

Method:
- Treat single-core and multi-core as separate baselines.
- Vary only one partitioning variable at a time.
- For each anomaly, build baseline, one-variable delta, boundary, counterexample.
- Record whether the issue is in partition math, synchronization, or hidden padding on per-core tails.

Required outputs under `swft-lab/results/multicore_partition_sync/`:
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
- single-core vs multi-core
- core count and per-core chunk size
- even partition vs tail partition
- sync absent vs sync present where meaningful
- GM read and write-back patterns

Completion criteria:
- At least 8 distinct probes.
- At least 2 tail-partition anomaly families.
- At least 2 probes that inspect synchronization behavior.
- `confirmed_rules`, `refuted_rules`, `anomalies`, `minimal_repros`, and `artifact_correlations` are all non-empty.
- `open_questions` is empty.
- `next_steps` is empty.
- `scope_complete` is true.

Do not reply with `DONE:` until every completion criterion is satisfied.
