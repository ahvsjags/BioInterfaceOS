# T073 Fit static corona mediator model

## Purpose

Fit the M3 static corona mediator model on paired material/intervention, corona mediator, and response outcome fixture units. Compare direct and mediated decompositions, run an alternative/random mediator control, propagate uncertainty, and downgrade the interpretation to associational if identification is insufficient.

## Preconditions

T056 corona modules, T071 M1, and T072 M2 are valid. Pairing must be explicit, duplicate-free, split-safe, and limited to fixture-backed direct/indirect links. No causal claim is made without an identification audit.

## Non-goals

This task will not infer causal effects from unpaired observational rows, alter split assignments, access hidden test targets, or fit dynamic/compositional models. T074 owns compositional corona modeling.

## Interfaces and invariants

`biointerfaceos train m3 --config configs/models/m3.yaml` validates paired units, fits direct and mediator-assisted associational decompositions, runs a random-mediator control, and reports uncertainty propagation, grouped metrics, and identification status. If pairing or identification is insufficient, the result must explicitly downgrade to associational decomposition.

## Implementation plan

1. Define M3 config, paired-unit schema, module/response feature policy, and identification checklist.
2. Build direct, mediator, and random-mediator design matrices from T056/T062-aligned fixture units.
3. Fit bounded regularized decompositions on train-only paired units and evaluate validation OOD.
4. Compare direct vs mediated prediction, run random-mediator negative control, propagate mediator uncertainty, and audit pairing/leakage.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m3 --config configs/models/m3.yaml`
- paired-unit construction, direct/mediated/random-control, uncertainty, and associational downgrade assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If pairings are incomplete or causal identification fails, preserve the pairing ledger and report associational decomposition with an explicit downgrade. Do not fill missing mediator values or reuse response labels across splits.

## Outputs

Versioned M3 config, paired-unit/audit artifacts, direct/mediated/random-control results, uncertainty/calibration report, focused tests, evidence report, and state/ledger advancement.
