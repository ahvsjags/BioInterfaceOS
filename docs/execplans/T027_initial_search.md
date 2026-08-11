# T027: Run initial systematic search and seed registry

## Purpose

Execute the validated development/validation query matrix through anonymous public adapters, persist cursors/hit IDs/timestamps, and seed a deduplicated candidate registry without accessing lockbox content.

## Preconditions

T026 is DONE and its matrix hash is frozen. T017-T020, T024, and the source policy engine are available. The locked date interval remains 2025-01-01 through 2026-08-11.

## Non-goals

This task will not inspect locked studies, tune queries against hidden outcomes, download scientific assets, claim saturation, or force paper-family merges.

## Interfaces and invariants

Every search run records matrix version/hash, query ID, source, scope, date bounds, UTC timestamp, request URL, cursor/page token, response hash, hit IDs through the candidate registry, response count, policy decision, and failure status. Development results are metadata-only until later asset gates. A rerun with the same frozen fixtures is candidate-id deterministic and does not duplicate persisted candidate rows.

## Implementation plan

1. Build search-run receipts and a candidate registry schema keyed by source plus stable accession.
2. Add fixture-backed runners for Europe PMC, PRIDE, GEO/SRA accession seeds, and public repository metadata.
3. Enforce date firewall and policy checks before accepting each hit; quarantine ambiguous licenses.
4. Persist cursor progress and bounded retries without reading or storing lockbox payloads.
5. Run fixture discovery for all matrix blocks, deduplicate candidate IDs, and emit a reproducibility receipt.
6. Validate the seed registry, run full gates, and record evidence before advancing.

## Progress

- [x] Define search-run and candidate-registry receipts.
- [x] Implement fixture-backed initial search runner.
- [x] Run bounded development/validation seed search and acceptance gates.

## Discoveries

- A fixture-backed run is the safe CI baseline because the matrix spans providers with different query/cursor contracts; live retrieval is a separate operational action.
- Candidate persistence needs deduplication across repeated runs even though append-only run receipts continue to accumulate.
- The current development scope contains 13 query blocks; validation remains available as a separate scope and does not enter the lockbox interval.

## Decisions

- The default CLI run is fixture-backed and explicitly reports fixture=true; no source endpoint is contacted.
- Run receipts are append-only, while candidate records are keyed by source plus stable accession and are not re-appended on rerun.
- License-ambiguous hits remain QUARANTINE and are preserved in the registry rather than silently dropped.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos search validate-queries
- biointerfaceos search run --scope development
- biointerfaceos source policy self-test
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check
- six ledger validation and 14-row unique candidate registry check

## Failure recovery

Save partial run receipts and cursor state; resume only the affected query block. Do not rewrite prior responses or delete rejected candidates. Use the cached fixture receipt for deterministic CI reruns.

## Outputs

reports/search_runs.jsonl, registry/search_candidates.jsonl, tests/fixtures/search/search_results.json, src/biointerfaceos/search_runner.py, tests/test_search_runner.py, reports/T027_initial_search.md, this ExecPlan, state advancement, and task-ledger evidence.

## Completion note

T027 completed with implementation commit 280a5904f47c59654bab807d4736a831af1a5eb9. Final acceptance evidence is recorded in reports/T027_initial_search.md.
