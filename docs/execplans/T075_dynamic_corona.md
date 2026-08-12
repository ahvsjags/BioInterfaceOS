# T075 Fit dynamic corona world model

## Purpose

Implement a data-sufficiency-gated dynamic corona world model over time-course fixture data. The primary path will be a constrained hierarchical kinetic baseline; a neural ODE is not required when the G3 dynamic threshold is not met.

## Preconditions

T057 PRIDE-QC, T074 compositional constraints, and T056 corona modules are valid. Time-course rows must retain study identity, obey mass/simplex constraints, and separate train/validation trajectories.

## Non-goals

This task will not claim dynamic causal effects, access locked test data, or fit a neural ODE on an underpowered fixture. Any insufficient-data result remains an explicit limitation.

## Interfaces and invariants

`biointerfaceos train m5 --config configs/models/m5.yaml` checks a G3 dynamic threshold, fits a declared discrete/hierarchical kinetics fallback when needed, reports trajectory metrics, leave-study-out performance, mass/simplex constraints, and toy dynamics recovery.

## Implementation plan

1. Define M5 config, trajectory schema, sufficiency threshold, and constraint policy.
2. Build deterministic time-course trajectories with study-held-out validation.
3. Gate the high-capacity path; fit bounded exponential/discrete kinetics fallback when insufficient.
4. Evaluate trajectory RMSE, leave-study-out metrics, mass/simplex constraints, and toy recovery.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m5 --config configs/models/m5.yaml`
- sufficiency gate, trajectory constraints, leave-study-out, fallback, and toy recovery assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If the G3 dynamic threshold fails, retain the discrete/hierarchical kinetic fallback and mark the neural model waived. Do not fabricate time points or smooth away study-level missingness.

## Outputs

Versioned M5 config, sufficiency/trajectory audits, kinetic/fallback results, toy recovery fixture/tests, evidence report, and state/ledger advancement.
