# T040: Implement units normalization and uncertainty propagation

## Purpose

Normalize accepted numeric assertions into a versioned unit registry while preserving raw values, dimensional bases, conversion provenance, and uncertainty. Unknown or ambiguous bases remain unconverted and enter clarification review.

## Preconditions

T039 is DONE. Accepted evidence rows and exact locators are available. Figure-derived uncertainty records and table-reported units are available.

## Non-goals

This task will not guess concentration/dose bases, convert values across incompatible dimensions, or discard raw values after normalization. Unknown basis and unsupported units remain explicit.

## Interfaces and invariants

Every normalized value retains raw value/unit, normalized value/unit, conversion factor, formula/version, source locator, and uncertainty status. Dimensional checks reject incompatible conversions. Uncertainty is transformed with the same valid conversion factor and remains linked to the raw assertion.

## Implementation plan

1. Define unit, quantity, conversion, normalized assertion, and clarification-review schemas.
2. Build fixtures for size, time, concentration, dose, zeta potential, PDI, and uncertainty-bearing values.
3. Implement a deterministic unit registry with dimension checks and explicit basis requirements.
4. Normalize valid values and propagate absolute/relative uncertainty while preserving raw evidence.
5. Quarantine unknown basis, incompatible dimensions, and unsupported units.
6. Add biointerfaceos normalize units --fixture, focused tests, and full acceptance gates.

## Progress

- [ ] Define unit registry and normalized assertion schemas.
- [ ] Implement dimensional conversion and uncertainty propagation.
- [ ] Preserve raw values and queue unknown bases/incompatible units.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos normalize units --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- dimensional conversion, basis firewall, raw-value retention, and uncertainty assertions

## Failure recovery

Keep raw assertions and evidence locators unchanged. Set normalized values to null and create clarification records for unknown bases or incompatible dimensions.

## Outputs

unit registry, normalized assertions, uncertainty propagation records, clarification queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
