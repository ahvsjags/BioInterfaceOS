# T039: Implement evidence resolver and reverse trace

## Purpose

Resolve accepted experiment fields back to raw assets and exact locators, provide a reverse-trace CLI, and retain conflicts as separate assertions in a conflict graph. Broken or missing lineage is rejected or quarantined.

## Preconditions

T038 is DONE. Dual-path candidates and consensus records are available, including accepted fields and unresolved disagreements.

## Non-goals

This task will not repair missing source evidence by guessing, collapse conflicting assertions into one value, or treat a report-level locator as an exact cell/page/point locator.

## Interfaces and invariants

Every accepted field resolves to an existing source asset identifier and an exact locator pattern. Reverse trace returns the field, path, value, source locator, and confidence. Conflicting values remain separate assertion nodes with conflict edges. Unresolved or broken locators enter a review queue.

## Implementation plan

1. Define evidence assertion, resolution, reverse-trace, conflict-edge, and review schemas.
2. Build sanitized trace fixtures containing accepted fields, a valid table/cell locator, a valid figure point locator, and a deliberate conflict.
3. Implement locator resolution against the source registries and extracted artifacts.
4. Build the reverse-trace CLI and conflict graph output.
5. Reject/quarantine missing or malformed locators and preserve all competing assertions.
6. Add biointerfaceos evidence trace --fixture, focused tests, and full acceptance gates.

## Progress

- [ ] Define evidence and conflict-graph schemas.
- [ ] Implement forward resolution and reverse trace.
- [ ] Preserve conflicts and quarantine broken locators.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos evidence trace --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- accepted-field resolution, reverse trace, conflict retention, and broken-locator quarantine assertions

## Failure recovery

Preserve all source assertions and locator strings. Quarantine unresolved lineage without rewriting the candidate or consensus ledgers.

## Outputs

evidence table, reverse-trace CLI, conflict graph, broken-locator review queue, fixtures/tests, this ExecPlan, state advancement, and task-ledger evidence.
