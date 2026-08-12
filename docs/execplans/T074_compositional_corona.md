# T074 Fit compositional corona model

## Purpose

Fit the M4 compositional corona model using simplex-constrained composition features and ILR/logistic-normal-style transformations. Compare zero handling and pseudocount alternatives, report OOD/calibration against M3, and validate toy composition recovery.

## Preconditions

T056 corona modules and T073 paired/static mediator artifacts are valid. Composition rows must sum to one after declared handling, retain zero provenance, and use train-only fitting.

## Non-goals

This task will not claim causal composition effects, access locked test data, or fit dynamic trajectories. T075 owns dynamic corona modeling.

## Interfaces and invariants

`biointerfaceos train m4 --config configs/models/m4.yaml` fits a bounded compositional baseline, checks simplex constraints, compares zero/pseudocount alternatives, and reports validation OOD/calibration, grouped metrics, and toy parameter recovery. A declared simpler fallback is acceptable when the fixture is sparse.

## Implementation plan

1. Define M4 config, composition schema, zero policy, and ILR balance basis.
2. Build deterministic composition vectors from T056 module fixture with explicit zero/missing masks.
3. Fit log-ratio regularized model under raw-zero and pseudocount alternatives.
4. Evaluate OOD/calibration versus M3, audit simplex constraints, and recover toy compositions.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m4 --config configs/models/m4.yaml`
- simplex, zero/pseudocount, OOD/calibration, grouped metrics, and toy recovery assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If composition sparsity makes ILR unstable, preserve a pseudocount/simpler declared fallback and report the sensitivity. Never renormalize away missingness without recording the original zero/missing mask.

## Outputs

Versioned M4 config, composition/zero audits, model/alternative results, OOD/calibration report, toy recovery fixture/tests, evidence report, and state/ledger advancement.
