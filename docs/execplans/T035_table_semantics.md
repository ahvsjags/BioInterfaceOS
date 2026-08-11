# T035: Implement table-to-experiment parser

## Purpose

Convert structured JATS, supplementary, and PDF table fixtures into experiment arms and measurements while preserving header hierarchy, sample sizes, mean/error/unit fields, footnotes, exact cell locators, and ambiguity.

## Preconditions

T032, T033, and T034 are DONE. JATS, spreadsheet, and PDF table representations plus the experiment schema are available.

## Non-goals

This task will not flatten incompatible subtables, invent missing units or sample sizes, or promote low-confidence semantic mappings without a review record.

## Interfaces and invariants

Every arm and measurement maps to one or more exact source cell locators. Header levels and footnotes remain attached. Mean/error pairs retain error type and unit. Missing or conflicting semantics are represented as null/ambiguous fields and queued for review. Formula values are treated as reported values, never recomputed.

## Implementation plan

1. Define table semantics, arm, measurement, and ambiguity schemas.
2. Implement header hierarchy and arm/measurement mapping for fixture tables.
3. Preserve sample size, mean, error, unit, footnote, and cell locator evidence.
4. Add low-confidence and incompatible-subtable review queue behavior.
5. Add CLI command biointerfaceos extract tables --fixture and focused tests.
6. Run full gates and record completion evidence.

## Progress

- [x] Define semantic table and experiment schemas.
- [x] Implement fixture-backed table-to-experiment mapping and review queue.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos extract tables --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- header/arm/measurement, unit/error, footnote, locator, ambiguity, and review-queue assertions

## Failure recovery

Preserve source cell locators and raw table values. Quarantine incompatible tables or low-confidence mappings for review; never silently coerce units or merge conflicting arms.

## Outputs

experiment table semantics, normalized measurements, review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.

## Completion note

T035 completed with implementation commit bc17172. The fixture parser preserves header hierarchy, experiment arms, measurements, reported units/errors, footnotes, exact cell locators, and explicit ambiguity records. Full gates passed with 148 tests.
