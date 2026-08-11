# T020: Implement GEO/SRA adapter

## Purpose

Provide an anonymous GEO/SRA adapter for GSE/GSM/SRP/SRR relationships, processed matrices, metadata, SOFT records, and official raw-data links.

## Preconditions

T016 is DONE, T020 is READY/current, the source adapter contract, policy engine, and allowlisted network client are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not request dbGaP credentials, scrape ordinary GEO pages, download FASTQ during discovery, or treat restricted SRA records as public.

## Interfaces and invariants

Use official NCBI GEO/SRA metadata and FTP/HTTPS endpoints. Preserve GSE/GSM/SRP/SRR identifiers, sample relationships, publication dates, organism/tissue fields, processed-file links, raw-file links, checksum when present, and evidence locations. Prefer author count matrices and metadata before raw FASTQ.

## Implementation plan

1. Define deterministic GEO series/sample and SRA run metadata requests with bounded payload parsing.
2. Implement GSE/GSM/SRP/SRR relationship mapping and processed/raw asset descriptors.
3. Add sanitized SOFT/JSON fixtures for a public series, sample relations, processed matrix, raw SRA link, and a restricted record.
4. Run offline lock/sync, focused/full tests, compileall, state, lockbox, release, catalog, and diff checks.
5. Record append-only evidence, advance the task graph, and commit.

## Progress

- [ ] Read and pin the official GEO/SRA metadata contract.
- [ ] Implement and test the GEO/SRA adapter.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_geo.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- mock GSE/GSM/SRP/SRR mapping, processed/raw links, public policy, restricted rejection, and fixture parsing assertions

## Failure recovery

If an official metadata endpoint is transient, preserve the sanitized metadata fixture and mark the affected asset unavailable; prefer public processed files and keep lower evidence grade for links without checksums.

## Outputs

src/biointerfaceos/sources/geo.py, tests/sources/test_geo.py, tests/fixtures/sources/geo, this ExecPlan, reports/T020_geo.md, state advancement, and task-ledger evidence.
