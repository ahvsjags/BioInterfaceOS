# T014: Implement immutable release and checksum system

## Purpose

Freeze a reproducible, content-hashed fixture release whose manifest, checksums, receipt, and read-only directory can be verified without overwriting or mutating an existing release.

## Preconditions

T006, T012, and T013 are DONE, T014 is READY/current, authoritative Parquet registries and the derived catalog validate, and no locked-test payload needs to be accessed.

## Non-goals

This task does not freeze the locked test, publish external data, change scientific claims, or overwrite any existing release.

## Interfaces and invariants

ReleaseManager.freeze creates release/fixtures/<data_release_id> from fixed repository inputs, writes a canonical release_manifest.json, checksums.txt, and release_receipt.json, then makes the directory and files non-writable. The release ID includes UTC date, current Git short commit, and an 8-character manifest hash. A second freeze with the same identity is rejected. ReleaseManager.verify recomputes every input hash, checks receipt/manifest consistency, and rejects changed or writable release artifacts.

## Implementation plan

1. Implement canonical input discovery, hash receipt, atomic fixture release creation, and verification.
2. Add release freeze/verify CLI commands.
3. Add temporary-repository tests for reproducibility, immutability, overwrite denial, and tamper detection.
4. Run offline lock/sync, full/focused tests, fixture freeze/verify, state/schema/ledger checks, compileall, and diff checks.
5. Record evidence, advance T014/T015 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read T014 contract, GOAL immutable-release rules, current hashes, and release directory structure.
- [x] 2026-08-12 ? Implemented atomic fixture freeze, read-only directory, canonical checksums/receipt, CLI, and 4 tests.
- [x] 2026-08-12 ? Offline lock/sync, full check (61 passed), focused tests (4 passed), fixture freeze/verify, state, compileall, and diff gates passed.

## Discoveries

The release input set can remain small and auditable at this foundation stage: source, asset, and rejection Parquet registries, derived catalog, source policy, and source schema. State files are deliberately excluded so completion evidence can advance state without invalidating the frozen data receipt.

## Decisions

Use a fixture namespace under release/fixtures and atomically rename a prepared directory. Keep checksums over authoritative inputs only; the release manifest and receipt separately identify their own bytes. A failed or duplicate freeze never mutates an existing release.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_release.py
- biointerfaceos release freeze --fixture
- biointerfaceos release verify --fixture
- biointerfaceos state validate
- .venv/bin/python -m compileall -q src tests
- git diff --check
- receipt, checksum, tamper, and overwrite assertions

## Failure recovery

Build a new release ID after any input change. Never delete or rewrite an existing frozen directory. If a temporary build fails, only the temporary staging directory is removed; release history and ledger bytes remain intact.

## Outputs

src/biointerfaceos/release.py, tests/test_release.py, release/fixtures, release freeze/verify CLI, this ExecPlan, reports/T014_release.md, state advancement, and task-ledger evidence.

## Completion note

T014 is complete. Implementation commit 3fc5fa3570eb8781d3de37c7e70152674a8a8129, frozen release bioif-data-20260811-73c256f-b00f5ab3, and evidence report reports/T014_release.md are recorded with the sequence-9 task ledger entry. T015 is READY/current. No source or locked-test payload was accessed.
