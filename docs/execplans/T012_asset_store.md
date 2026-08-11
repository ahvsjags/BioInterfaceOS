# T012: Implement content-addressed asset store

## Purpose

Store admitted public assets once by content hash, preserve failed bytes for diagnosis, and link every stored blob back to a validated source-manifest record.

## Preconditions

T010 is DONE, T012 is READY/current, the source manifest and Parquet runtime validate, and no source or locked-test payload needs to be accessed.

## Non-goals

This task does not discover sources, apply license policy, access locked-test data, or delete raw artifacts. It only provides the local store and mocked/file-based verification paths.

## Interfaces and invariants

AssetStore uses data/cas/sha256/<prefix>/<sha256> as the physical content address and registry/ASSET_INDEX.parquet as a fixed provenance index. Ingestion requires an admitted SourceRecord with a matching non-null SHA-256. Bytes are staged, hashed, fsynced, and atomically promoted only after verification. Identical bytes reuse one blob while preserving multiple provenance references. Hash mismatches never reach CAS and are preserved under data/quarantine. Verification rejects missing, escaping, tampered, or unlinked blobs and never reads data/locked_test.

## Implementation plan

1. Implement typed CAS references, atomic staging, hash verification, provenance checks, and Parquet index operations.
2. Add assets verify CLI and initialize an empty index.
3. Add file-based tests for deduplication, partial/mismatch behavior, provenance linkage, containment, tamper detection, and no locked-test access.
4. Run offline lock/sync, full and focused tests, CLI/state/schema checks, compileall, and diff checks.
5. Record evidence, advance T012/T013/T014 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read T012, GOAL storage/manifest constraints, T010 API, and repository raw-data protections.
- [ ] Implement and test the asset store.
- [ ] Run acceptance gates and record completion evidence.

## Discoveries

The existing storage guard excludes data/raw and transient files but permits a committed, repository-contained data/cas namespace. PyArrow 17.0.0 supports the same fixed-schema atomic Parquet pattern used by the source manifest.

## Decisions

Use a two-level SHA-256 path fanout and an index row per provenance reference. Deduplicate physical blobs while retaining source/asset identity in the index. Keep mismatched staged bytes in quarantine rather than deleting evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/assets
- biointerfaceos assets verify
- biointerfaceos source manifest validate
- biointerfaceos state validate
- .venv/bin/python -m compileall -q src tests
- git diff --check
- CAS hash and provenance assertions

## Failure recovery

Atomic writes leave the prior blob and index untouched if staging, hashing, or index replacement fails. Mismatched staged bytes are moved to data/quarantine with a content-derived name. Verification failures are reported without deletion. Never use data/locked_test as a store or test fixture.

## Outputs

src/biointerfaceos/assets.py, tests/assets, registry/ASSET_INDEX.parquet, data/cas, data/quarantine, assets verify CLI, this ExecPlan, reports/T012_assets.md, state advancement, and task-ledger evidence.

## Completion note

Pending implementation and acceptance validation.
