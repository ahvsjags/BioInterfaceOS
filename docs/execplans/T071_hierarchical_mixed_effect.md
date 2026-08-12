# T071 Fit hierarchical mixed-effect baseline

## Purpose

Fit and audit the M1 hierarchical mixed-effect baseline over the development benchmark, reporting study/protocol/material variance partitions, diagnostics, grouped cross-validation, calibration, and a toy parameter-recovery control.

## Preconditions

T063 group keys, T069 simple baselines, and T070 representation coverage are validated. The M1 config must be versioned, train-only, and deterministic. No locked test data or network access is permitted.

## Non-goals

This task will not tune a model on validation outcomes, use identity fields as predictors, alter split/group assignments, or claim causal mediation. More complex direct black-box models belong to T072.

## Interfaces and invariants

`biointerfaceos train m1 --config configs/models/m1.yaml` fits the declared hierarchical baseline from training data only. It reports convergence, diagnostics, variance partition, grouped CV/calibration, validation OOD metrics, and toy recovery. If the fixture is non-identifiable, the result must preserve an explicit simplification/regularization limitation.

## Implementation plan

1. Define the M1 config, feature audit, random-effect grouping fields, and deterministic seed.
2. Implement a bounded regularized hierarchical estimator with fixed/intercept and study/protocol/material effects.
3. Run train-only fit, grouped cross-validation, calibration and validation evaluation with T068 metrics.
4. Compute variance partition, convergence/diagnostic checks, toy parameter recovery, and deterministic artifacts.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m1 --config configs/models/m1.yaml`
- convergence/diagnostic and toy-recovery assertions
- study/protocol/material variance partition, grouped CV, calibration, and validation OOD metrics
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If random effects are not identifiable on the development fixture, retain a regularized/simplified model and record the limitation explicitly. Never resolve non-identifiability by including IDs or validation outcomes.

## Outputs

Versioned M1 config, model/result/diagnostic artifacts, variance partition, grouped-CV/calibration report, toy recovery fixture/tests, evidence report, and state/ledger advancement.
