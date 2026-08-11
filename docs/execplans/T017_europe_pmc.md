# T017: Implement Europe PMC adapter

## Purpose

Provide a reproducible anonymous Europe PMC adapter for candidate search, cursor pagination, metadata/full-text links, supplementary asset listing, and checksum-gated fetches.

## Preconditions

T016 is DONE, T017 is READY/current, the anonymous client and source policy engine are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not bulk-download papers, inspect post-2024 locked-test content, infer licenses, or treat an abstract license as a full-text license.

## Interfaces and invariants

EuropePmcAdapter uses official endpoints under www.ebi.ac.uk only, a fixed anonymous User-Agent, bounded rate/retry policy, and the SourcePolicyEngine before metadata/list/fetch. Search uses cursorMark pagination and returns candidate metadata with accession, publication date, license, and evidence location. Metadata returns official full-text and supplementary links. Fetch requires an explicit expected SHA-256 in AssetDescriptor and uses AnonymousHttpClient.download; missing checksums are rejected.

## Implementation plan

1. Implement the Europe PMC adapter with typed query/config helpers and cursor pagination.
2. Add sanitized JSON query fixtures and fully mocked adapter tests.
3. Run offline lock/sync, full/focused tests, compileall, state, lockbox, release, and diff checks.
4. Record evidence, advance T017/T018 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 UTC Read T017 contract, Europe PMC official endpoint templates in GOAL, adapter contract, policy, and network client.
- [x] Implement and test the Europe PMC adapter.
- [x] Run acceptance gates and record completion evidence.

## Discoveries

Europe PMC cursor pagination exposes nextCursorMark rather than a URL; the adapter will canonicalize each request with sorted query parameters and stop on a repeated cursor.

## Decisions

Treat provider license metadata as a candidate signal only; all metadata/list/fetch operations still pass SourcePolicyEngine. Do not download an asset without an explicit checksum in its manifest descriptor.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_europe_pmc.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check
- mock pagination, policy, link, and checksum-gated fetch assertions

## Failure recovery

Cursor or transport errors remain bounded by AnonymousHttpClient. A missing or mismatched checksum prevents fetch before promotion. Preserve sanitized response fixtures and do not retry against real endpoints during tests.

## Outputs

src/biointerfaceos/sources/europe_pmc.py, tests/sources/test_europe_pmc.py, tests/fixtures/sources/europe_pmc, this ExecPlan, reports/T017_europe_pmc.md, state advancement, and task-ledger evidence.

## Completion note

T017 completed with implementation commit a8564b8ef06f9de06f45705aeaf4619fbf9033f4 and final acceptance evidence recorded in reports/T017_europe_pmc.md.
