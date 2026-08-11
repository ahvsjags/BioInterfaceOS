# T026: Build versioned query matrix

## Purpose

Create and validate the versioned discovery query matrix for material, corona, endpoint, data, and assay axes without touching lockbox payloads.

## Preconditions

T017, T018, T019, T020, and T025 are DONE. Source adapters, public repository mirrors, and the nanodatabase admission decisions are available.

## Non-goals

This task will not run the systematic search, inspect locked-test records, tune queries against hidden outcomes, or claim exhaustive literature coverage.

## Interfaces and invariants

configs/search_queries.yaml records schema version, query-set version, source/axis/scope, query text, date bounds, cursor strategy, and rationale. Duplicate queries, unsupported syntax, missing axes, and post-lockbox date leakage are validation errors. The query matrix is an input artifact for T027 and has a deterministic SHA-256 receipt.

## Implementation plan

1. Define a compact query schema covering material identity, corona/protein, endpoint, assay, protocol, species, and data/code axes.
2. Add source-specific query syntax and bounded date/cursor fields for Europe PMC, PMC OA, PRIDE, GEO/SRA, repository mirrors, and admitted substitutes.
3. Add duplicate/impossible-syntax/date-firewall validation and a deterministic matrix hash.
4. Write reports/QUERY_MATRIX_VALIDATION.md and offline fixtures for valid, duplicate, malformed, and out-of-range cases.
5. Run full gates and record the immutable query-set version before any discovery run.

## Progress

- [x] Define and validate the query matrix schema.
- [x] Add deterministic query validation and fixtures.
- [x] Run acceptance gates and record completion evidence.

## Discoveries

- The current GEO adapter resolves explicit public GSE/GSM/SRA accessions rather than broad concept searches; the matrix therefore records GEO accession seeds as a separate cursor strategy.
- The lockbox date boundary must be enforced before any source adapter is called; the validator rejects a query that intersects 2025-01-01 onward.
- A valid current frontier can have no READY task while the in-progress task is the last dependency-satisfied task; the state test now represents that case.

## Decisions

- Training queries end at 2023-12-31 and validation queries use exactly 2024-01-01 through 2024-12-31.
- The matrix contains seven required scientific axes, nine source types, and both train/validation scopes.
- Matrix bytes are hashed after YAML serialization; any semantic or formatting change requires a new matrix version and receipt.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos search validate-queries
- biointerfaceos source policy self-test
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- git diff --check
- valid matrix, duplicate definition, lockbox date, scope mismatch, and trailing-newline fixtures

## Failure recovery

Revise syntax or source-specific query blocks without inspecting locked outcomes; retain rejected query rows and their validation reasons. Never overwrite a released matrix; bump matrix_version and write a new hash receipt.

## Outputs

configs/search_queries.yaml, src/biointerfaceos/search_matrix.py, tests/fixtures/search_queries, tests/test_search_matrix.py, reports/QUERY_MATRIX_VALIDATION.md, this ExecPlan, state advancement, and task-ledger evidence.

## Completion note

T026 completed with implementation commit 2fadbfe3e669c6abd83813e155b653ac1ecf202a. Final acceptance evidence is recorded in reports/T026_query_matrix.md.
