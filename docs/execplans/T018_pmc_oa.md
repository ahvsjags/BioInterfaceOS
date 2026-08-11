# T018: Implement PMC Open Access adapter

## Purpose

Provide an anonymous, official-endpoint PMC Open Access adapter for OA file lists, license filtering, JATS/XML assets, figures, and supplementary files.

## Preconditions

T016 is DONE, T018 was READY and is now DONE, the source adapter contract, policy engine, and allowlisted network client are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not scrape ordinary PMC article pages, infer a full-text license from an abstract, download non-OA content, or bypass authentication, cookies, CAPTCHAs, or paywalls.

## Interfaces and invariants

Use only official PMC OA Web Service, OAI-PMH, FTP, E-Utilities, BioC, or Cloud endpoints. The adapter must distinguish OA-subset membership from ordinary PMC metadata, preserve per-asset license/provenance fields, pass metadata/list/fetch through SourcePolicyEngine, and require an explicit SHA-256 before fetch promotion.

## Implementation plan

1. Select a deterministic official PMC OA file-list endpoint and define bounded request behavior.
2. Implement OA-subset membership and explicit-license filtering without treating abstract licenses as full-text licenses.
3. Add sanitized fixtures for admitted OA content, non-OA metadata pointers, JATS/XML, figures, and supplementary files.
4. Run offline lock/sync, focused/full tests, compileall, state, lockbox, release, catalog, and diff checks.
5. Record append-only evidence, advance the task graph, and commit.

## Progress

- [x] Read and pin the official PMC OA endpoint contract.
- [x] Implement and test the PMC OA adapter.
- [x] Run acceptance gates and record completion evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_pmc_oa.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- mock OA membership, license filtering, JATS, figure, supplementary, and non-OA pointer assertions

## Failure recovery

If the OA file service is transient or unavailable, preserve the sanitized metadata fixture and mark the asset unavailable; do not broaden access to ordinary PMC pages.

## Outputs

src/biointerfaceos/sources/pmc_oa.py, tests/sources/test_pmc_oa.py, tests/fixtures/sources/pmc_oa, this ExecPlan, reports/T018_pmc_oa.md, state advancement, and task-ledger evidence.


## Completion note

T018 completed with implementation commit da4c22fcf9b1b81a79de939368ea1f515f8a5434 and final acceptance evidence in reports/T018_pmc_oa.md.
