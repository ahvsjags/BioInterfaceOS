# T038: Implement dual-path structured extraction

## Purpose

Produce a common experiment-record schema from JATS text, supplementary/PDF table semantics, and figure-derived measurements using two auditable paths: deterministic rules and a local/mock extraction path. Preserve evidence locators, compare paths, and route disagreements to consensus review.

## Preconditions

T032, T033, T035, and T037 are DONE. Structured document records, table semantics, calibrated figure points, and review queues are available.

## Non-goals

This task will not accept a field without a source locator, call private APIs, or lower evidence requirements when a local/mock path is unavailable. Disagreements are not silently averaged or discarded.

## Interfaces and invariants

Both paths emit the same versioned experiment schema. Every numeric or categorical field carries one or more raw-asset locators and a confidence/status. Consensus records retain both path values, agreement/disagreement status, and the adjudication state. Local/mock execution is deterministic and offline.

## Implementation plan

1. Define versioned experiment candidate, field-evidence, path-output, and consensus schemas.
2. Build combined sanitized fixtures from JATS, table semantics, and digitized figure outputs.
3. Implement deterministic rule extraction with stable field locators and provenance.
4. Implement a local/mock extraction path with identical schema and explicit model/backend metadata.
5. Compare both paths, record field-level disagreements, and route unresolved conflicts to the consensus queue.
6. Add biointerfaceos extract experiment --fixture --dual, focused tests, and full acceptance gates.

## Progress

- [x] Define dual-path experiment and consensus schemas.
- [x] Implement deterministic and local/mock extraction paths.
- [x] Record field-level agreement/disagreement with evidence locators.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos extract experiment --fixture --dual
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- schema equality, locator completeness, path agreement/disagreement, consensus queue, and offline-backend assertions

## Failure recovery

Preserve each path output and its source locators. Quarantine unresolved disagreements in the consensus queue; never overwrite one path with the other.

## Outputs

dual-path experiment candidates, field-level consensus records, disagreement queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.

## Completion note

T038 completed with implementation commit 919f076. Deterministic and offline-mock paths share a versioned field schema; locator-complete agreements are accepted, while disagreements retain both assertions and enter consensus review.
