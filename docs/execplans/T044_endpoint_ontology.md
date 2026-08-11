# T044: Implement endpoint and measurement ontology

## Purpose

Normalize biological endpoints and measurements into assay-, basis-, and time-aware entities, covering uptake, viability, complement, inflammation, coagulation, biodistribution, and delivery while keeping incompatible endpoint strata separate.

## Preconditions

T023, T039, and T040 are DONE. Ontology adapters, evidence locators, units, and protocol context are available.

## Non-goals

This task will not harmonize incompatible assay bases, collapse endpoint timepoints, or treat qualitative and quantitative measures as interchangeable.

## Interfaces and invariants

Every endpoint retains raw label, endpoint family, assay, measurement basis, timepoint, unit, normalized value/effect where compatible, source locator, and confidence. Compatible effects may be harmonized only within a declared stratum. Incompatible strata remain separate.

## Implementation plan

1. Define endpoint family, measurement, assay/basis, timepoint, effect-size, and stratum schemas.
2. Build fixtures for uptake, viability, complement, inflammation, coagulation, biodistribution, and delivery.
3. Implement family/assay/basis/time normalization using the unit registry.
4. Harmonize compatible effects within strata and preserve incompatible records separately.
5. Route unknown basis, incompatible units, and missing timepoints to review.
6. Add biointerfaceos resolve endpoints --fixture, focused tests, and full acceptance gates.

## Progress

- [ ] Define endpoint and measurement ontology schemas.
- [ ] Implement family/assay/basis/time normalization.
- [ ] Harmonize compatible effects and retain incompatible strata.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos resolve endpoints --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- endpoint family, assay, basis, time, compatible-effect, incompatible-strata, and missingness assertions

## Failure recovery

Keep raw endpoint labels, assay/basis/time, and values. Create separate strata or review records for incompatible endpoints; never force a cross-basis effect.

## Outputs

endpoint entities, measurement mappings, effect-size strata, review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
