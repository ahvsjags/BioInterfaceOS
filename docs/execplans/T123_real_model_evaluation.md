# T123: Real paired model runs, ablations and OOD evaluation

## Purpose

Use real, compatible, study-grouped benchmark data to determine whether any declared model or module effect survives paired ablations and out-of-distribution evaluation.

## Preconditions

T122 is complete, but its three study-held-out items are heterogeneous raw-cell locator tasks. They are not yet a compatible biological prediction target, and this limitation is a precondition rather than a result.

## Non-goals

Do not convert deterministic locator resolution into a causal or biological model, manufacture labels, reuse fixture runs, infer unavailable cohorts, or describe protocol completion as robustness or generalisation.

## Interfaces and invariants

- Required command: `python -m biointerfaceos model evaluate-real --strict`.
- Inputs must be a frozen compatible target, raw source-level predictions, paired full/ablated configurations, declared seeds, study-level OOD groups, negative controls and overlap/effective-n records.
- Any model output must retain `DEVELOPMENT_OBSERVATION` / `EXPLORATORY` status until an independent evaluator executes T124.
- No module effect is accepted without paired runs on identical source groups/seeds and explicit uncertainty.

## Implementation plan

1. Audit whether a common target with adequate effective n exists across the T122 sources.
2. If not, register the incompatibility and enlarge the raw-data registry before any model training.
3. Freeze compatible target, configurations, seeds, ablation matrix, external cohort definition and negative controls.
4. Run paired models only after the above freeze; retain raw predictions and group-level uncertainty.
5. Implement strict evaluator and failure tests, preserving unavailable states instead of backfilling fixture values.

## Progress

- [ ] Compatibility and effective-n audit.
- [ ] Source expansion or target freeze.
- [ ] Paired model/ablation/OOD execution.
- [ ] Strict receipt and negative-control audit.

## Discoveries

- The T122 source-locator benchmark must not be reused as a scientific model target.

## Decisions

- Pending compatibility audit.

## Validation

- Strict evaluation must reject heterogeneous targets, fixture payloads, mismatched seeds/groups, absent raw predictions, undeclared OOD cohorts and missing negative controls.

## Failure recovery

If a compatible real target cannot be assembled, record a blocked data-coverage state and return to source admission. Keep all effect/robustness/generalisation claims disabled.

## Outputs

- Compatibility report; frozen target/configuration/split manifests; paired predictions; ablations; OOD and negative-control audit; receipt.

## Completion note

Pending.
