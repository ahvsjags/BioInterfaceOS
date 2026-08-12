# T090 Stable protein-corona functional axes

## Purpose

Discover candidate stable protein-corona functional axes from development matrices while comparing NMF, sparse, and log-ratio alternatives, measuring bootstrap and leave-study stability, and preserving random-module controls and uncertainty.

## Preconditions

T056 harmonized corona matrices, T074 calibrated uncertainty, and T089 frozen hypothesis tournament/preregistration rules are valid.

## Non-goals

This task will not use locked or validation targets for axis discovery, select an axis after inspecting held-out outcomes, report pathway enrichment without evidence, or collapse uncertainty into a single unqualified axis claim.

## Interfaces and invariants

`biointerfaceos discover functional-axes` will emit typed axis models, loadings, pathway-enrichment evidence links, bootstrap/leave-study stability, random-module controls, uncertainty intervals, and a comparison receipt. Candidate axes remain exploratory and are not automatically accepted.

## Implementation plan

1. Define schemas for matrix provenance, axis models, loadings, enrichment links, stability metrics, random controls, and uncertainty.
2. Load only T056 development corona matrices and T089 frozen preregistration config.
3. Fit deterministic NMF, sparse, and log-ratio alternatives under equal component/tuning budgets.
4. Run bootstrap and leave-study stability checks plus random-module negative controls; retain candidates only with uncertainty and evidence links.
5. Add CLI, focused tests, evidence artifacts, report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos discover functional-axes`
- alternatives compared, stability measured, random controls evaluated, and candidate uncertainty emitted
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Retain predefined functional modules and label the axis discovery exploratory if stability or negative-control gates fail. Preserve every failed alternative and its uncertainty rather than selecting by held-out outcome.

## Outputs

Versioned functional-axis schema/config, development matrix fixture, alternative model comparison, loadings, enrichment evidence, stability report, random controls, uncertainty, focused tests, evidence report, and state/ledger advancement.
