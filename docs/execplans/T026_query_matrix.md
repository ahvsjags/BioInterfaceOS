# T026: Build versioned query matrix

## Purpose

Create and validate the versioned discovery query matrix for material, corona, endpoint, data, and assay axes without touching lockbox payloads.

## Preconditions

T017, T018, T019, T020, and T025 are DONE. Source adapters, public repository mirrors, and the nanodatabase admission decisions are available.

## Non-goals

This task will not run the systematic search, inspect locked-test records, tune queries against hidden outcomes, or claim exhaustive literature coverage.

## Interfaces and invariants

configs/search_queries.yaml must record schema version, query-set version, source/axis/language/scope, query text, date bounds, cursor strategy, and rationale. Duplicate queries, unsupported syntax, missing axes, and post-lockbox date leakage are validation errors. The query matrix is an input artifact for T027 and must be hashable and reproducible.

## Implementation plan

1. Define a compact query schema covering material identity, corona/protein, endpoint, assay, protocol, species, and data/code axes.
2. Add source-specific query syntax and bounded date/cursor fields for Europe PMC, PMC OA, PRIDE, GEO/SRA, repository mirrors, and admitted substitutes.
3. Add duplicate/impossible-syntax/date-firewall validation and a deterministic matrix hash.
4. Write reports/QUERY_MATRIX_VALIDATION.md and offline fixtures for valid, duplicate, malformed, and out-of-range cases.
5. Run full gates and record the immutable query-set version before any discovery run.

## Progress

- [ ] Define and validate the query matrix schema.
- [ ] Add deterministic query validation and fixtures.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos search validate-queries
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check

## Failure recovery

Revise syntax or source-specific query blocks without inspecting locked outcomes; retain rejected query rows and their validation reasons.

## Outputs

configs/search_queries.yaml, query validator, tests/fixtures/search_queries, tests, reports/QUERY_MATRIX_VALIDATION.md, this ExecPlan, state advancement, and task-ledger evidence.
