# R4 T195 strict-common-target execution status

Status: `T195_COMMON_TARGET_EXECUTION_COMPLETED_EXPLORATORY`

T195 is a sensitivity analysis downstream of T192. It uses the exact nine
canonical accessions that are positive and rank-eligible in all three audited
source maps:

`P04004`, `P04264`, `P05556`, `P06396`, `P07996`, `P26038`, `P60174`, `Q04695`, `Q9HDC9`.

The execution closes 809 row-traceable observations, 85 measurement batches,
three leave-one-laboratory-anchor-out folds and three model paths. Nested
selection, paired full/composition ablation, 2,000-resample batch-cluster
bootstrap and 256 within-development-batch permutations are executed from a
target set frozen before T195 model fitting.

The strict common-target result does not change the biological-unit boundary:
Dalian is pooled/unspecified plasma, Edinburgh donor IDs are not encoded in the
current map, and UCD replicate columns are technical replicates. Therefore the
result is not independent biological validation, a protected lockbox, a
no-author reproduction or scientific submission readiness.

Machine-readable inputs and outputs:

- `docs/data/R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_PROTOCOL.json`
- `docs/data/R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_REGISTRY.json`
- `src/biointerfaceos/r4_t195_three_lab_common_target_execution.py`
- `reports/review_round_4/t195_three_lab_common_target_execution/v1.0.0/`

The required flags remain:

```text
independent_validation=false
external_scientific_reproduction=false
external_user_adoption=false
scientific_submission_ready=false
```
