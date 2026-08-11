# T008: Implement storage accounting and quota guard

## Purpose

Provide deterministic storage accounting and safe quota/deletion controls before scientific data acquisition begins.

## Preconditions

T000 through T007 are DONE, T008 is current, and the repository contains no scientific data or model artifacts.

## Non-goals

This task does not download data, delete raw data, implement networking, or modify T009 or later tasks.

## Interfaces and invariants

Storage configuration is repository-contained in config/storage.yaml with a 1.5 TB budget and declared roots. Audits count regular files only, exclude .git, .venv, __pycache__, temporary files, and the generated storage report, and emit stable content hashes and duplicate groups. StorageGuard rejects outside-root writes, over-budget writes, and all deletion requests under data/raw. Cleanup discovery is read-only.

## Implementation plan

1. Add the storage configuration and typed storage audit/guard module.
2. Add the storage audit CLI and deterministic JSON report.
3. Add offline tests for accounting, duplicate hashes, quota, containment, raw deletion, exclusions, and dry-run cleanup.
4. Run the full quality and storage acceptance gates.
5. Record evidence, advance T008/T009 state, append one T008 task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Implemented config loading, accounting, duplicate detection, quota guard, raw deletion denial, dry-run cleanup, CLI, report, and tests.
- [x] 2026-08-12 ? Ran lock check, offline frozen sync, make check, storage audit, schema/state regressions, compileall, and containment checks.
- [x] 2026-08-12 ? Recorded the evidence report and task-ledger entry, advanced T008/T009 state, and committed the result.

## Discoveries

The project currently contains only foundation artifacts. The measured audit is therefore small relative to the hard budget. The generated storage report must be excluded from its own input manifest to avoid self-referential size drift.

## Decisions

Use SHA-256 file content hashes for duplicate groups and manifest identity. Keep all guard methods read-only except for the explicit report writer; no cleanup method performs deletion.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos storage audit --strict
- biointerfaceos schema validate-all
- biointerfaceos state validate && biointerfaceos state next
- python -m compileall -q src tests
- git diff --check and containment assertions

## Failure recovery

If the audit fails, preserve the report and diagnostic output, correct only configuration or storage-module issues, and rerun. Never remove raw data or historical ledgers.

## Outputs

config/storage.yaml, src/biointerfaceos/storage.py, storage CLI, reports/storage_usage.json, reports/T008_storage.md, tests/test_storage.py, this ExecPlan, task/state advancement, one T008 ledger record, and focused commits.

## Completion note

T008 is complete. Storage accounting, duplicate hashes, quota denial, raw deletion denial, containment, exclusion, and read-only cleanup tests passed. T009 is READY/current; no data, model, or locked-test payload was accessed.
