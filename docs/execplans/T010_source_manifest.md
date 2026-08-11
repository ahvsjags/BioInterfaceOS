# T010: Implement source manifest registry

## Purpose

Create a strict, provenance-preserving source and asset registry that represents admitted, rejected, and quarantined candidates in a real Parquet manifest before acquisition and policy tasks begin.

## Preconditions

T007 and T009 are DONE, T010 is READY/current, the repository state validates, and no locked-test payload or scientific source needs to be accessed.

## Non-goals

This task does not discover or download public sources, decide license policy beyond enforcing explicit record status, parse full text, or inspect locked-test content.

## Interfaces and invariants

SourceRecord requires stable source identity, canonical anonymous URL, access/status, retrieval time, accession, SHA-256 when content is available, size, license, redistribution, and download status fields. A record with an unclear license cannot be admitted. Asset IDs are deterministic SHA-256 values derived from source ID, URL, and content hash. ManifestRegistry writes a fixed-schema Parquet file atomically, validates every row, deduplicates identical non-null content hashes, and rejects paths outside the repository.

## Implementation plan

1. Add the pinned PyArrow runtime needed for a true Parquet manifest.
2. Implement typed record validation and atomic manifest read/write/register operations.
3. Add biointerfaceos source manifest validate.
4. Add temporary-directory tests for schema enforcement, admission/quarantine invariants, deduplication, containment, and CLI validation.
5. Run offline lock/sync, full checks, focused tests, compileall, state/ledger validation, and diff checks.
6. Record evidence, advance T010/T011 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read AGENTS, GOAL, PLANS, state, T010, source schema, and storage constraints; selected PyArrow from the server cache for a real Parquet artifact.
- [x] 2026-08-12 ? Implemented typed record validation, atomic Parquet registry, CLI validation, and 7 focused tests.
- [x] 2026-08-12 ? Offline lock/sync, full check (40 passed), focused tests (7 passed), CLI, state, ledger, compileall, and diff gates passed.

## Discoveries

The foundation environment did not contain PyArrow initially, but the KAUST uv cache contains a CPython 3.11 Linux wheel for PyArrow 17.0.0. Offline installation also supplies NumPy 2.4.6.

## Decisions

Use PyArrow 17.0.0 pinned in pyproject.toml and uv.lock rather than silently emitting JSON with a Parquet suffix. Keep the manifest contract local and explicit because the earlier minimal source schema does not encode nullable asset metadata.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_manifest.py
- .venv/bin/biointerfaceos source manifest validate
- .venv/bin/python -m compileall -q src tests
- git diff --check
- repository containment and Parquet round-trip assertions

## Failure recovery

Parquet writes go through a same-directory temporary file and atomic replace. Invalid records are rejected before any write. No source download is attempted. A failed or malformed fixture is recreated in a temporary directory; existing manifest and ledger bytes are preserved.

## Outputs

src/biointerfaceos/manifest.py, tests/test_manifest.py, CLI source-manifest validation, registry/SOURCE_MANIFEST.parquet, this ExecPlan, reports/T010_manifest.md, state advancement, a task-ledger record, and focused commits.

## Completion note

T010 is complete. The implementation commit is 593ca7bf98cda1f534629e4787748465a7eb69ca; evidence is in reports/T010_manifest.md and the sequence-5 task ledger record. T011 is READY/current. No source acquisition or locked-test access occurred.
