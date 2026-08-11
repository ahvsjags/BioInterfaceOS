# T019: Implement PRIDE/ProteomeXchange adapter

## Purpose

Provide an anonymous PRIDE Archive adapter for project metadata, file manifests, accession/date/species/instrument fields, checksums, and large-file dry-run/resume behavior.

## Preconditions

T016 is DONE, T019 is READY/current, the source adapter contract, policy engine, and allowlisted network client are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not download RAW files during discovery, request credentials, scrape ordinary PRIDE web pages, or silently replace an unavailable PRIDE endpoint with an unverified mirror.

## Interfaces and invariants

Use the official PRIDE Archive REST v3 project and search endpoints, with FTP/HTTPS file links only when returned by official metadata. Preserve project accession, submission date, species, instrument, file accession, checksum, and evidence location. Enforce anonymous access and explicit license/availability gates before metadata, file listing, or fetch.

## Implementation plan

1. Define bounded, canonical REST project/search requests and parse sanitized project fixtures.
2. Implement project metadata and file-manifest mapping with checksum and resumable large-file dry-run support.
3. Add fixtures for a public project, a restricted/unavailable asset, and a checksum mismatch or resume case.
4. Run offline lock/sync, focused/full tests, compileall, state, lockbox, release, catalog, and diff checks.
5. Record append-only evidence, advance the task graph, and commit.

## Progress

- [ ] Read and pin the official PRIDE REST v3 project/file contract.
- [ ] Implement and test the PRIDE adapter.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_pride.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- mock project metadata, file manifest, license/access gate, checksum, dry-run, and resume assertions

## Failure recovery

If the official endpoint or an individual file is transient, preserve the project metadata and mark the affected asset unavailable; do not request credentials or promote bytes without a verified checksum.

## Outputs

src/biointerfaceos/sources/pride.py, tests/sources/test_pride.py, tests/fixtures/sources/pride, this ExecPlan, reports/T019_pride.md, state advancement, and task-ledger evidence.
