# T027: Run initial systematic search and seed registry

## Purpose

Execute the validated development/validation query matrix through anonymous public adapters, persist cursors/hit IDs/timestamps, and seed a deduplicated candidate registry without accessing lockbox content.

## Preconditions

T026 is DONE and its matrix hash is frozen. T017-T020, T024, and the source policy engine are available. The locked date interval remains 2025-01-01 through 2026-08-11.

## Non-goals

This task will not inspect locked studies, tune queries against hidden outcomes, download scientific assets, claim saturation, or force paper-family merges.

## Interfaces and invariants

Every search run records matrix version/hash, query ID, source, scope, date bounds, UTC timestamp, request URL, cursor/page token, response hash, hit IDs, response count, policy decision, and failure status. Development results are metadata-only until later asset gates. A rerun with the same frozen fixtures must be deterministic.

## Implementation plan

1. Build search-run receipts and a candidate registry schema keyed by source plus stable accession.
2. Add fixture-backed runners for Europe PMC, PRIDE, GEO/SRA accession seeds, and public repository metadata.
3. Enforce date firewall and policy checks before accepting each hit; quarantine ambiguous licenses.
4. Persist cursor progress and bounded retries without reading or storing lockbox payloads.
5. Run fixture discovery for all matrix blocks, deduplicate candidate IDs, and emit a reproducibility receipt.
6. Validate the seed registry, run full gates, and record evidence before advancing.

## Progress

- [ ] Define search-run and candidate-registry receipts.
- [ ] Implement fixture-backed initial search runner.
- [ ] Run bounded development/validation seed search and acceptance gates.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos search run --scope development
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check

## Failure recovery

Save partial run receipts and cursor state; resume only the affected query block. Do not rewrite prior responses or delete rejected candidates.

## Outputs

search_runs, candidate registry, receipts, tests, reports/T027_initial_search.md, this ExecPlan, state advancement, and task-ledger evidence.
