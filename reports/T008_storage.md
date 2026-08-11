# T008 Storage Evidence

## Result

T008 is complete on the KAUST Ibex server. Storage accounting, duplicate-content detection, a 1.5 TB quota guard, repository containment, raw-data deletion denial, and read-only cleanup discovery are implemented. T009 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- uv lock --check: exit 0; no dependency change.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 25 tests passed across CLI, schema, state, and storage suites.
- .venv/bin/biointerfaceos storage audit --strict: STORAGE_VALID bytes=44925 files=71 budget_bytes=1500000000000 duplicates=4.
- .venv/bin/biointerfaceos schema validate-all: SCHEMA_VALID schemas=9 fixtures=9.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/biointerfaceos state next: T008 before completion; T009 after completion state transition.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.

## Implemented artifacts

- config/storage.yaml: 1500000000000-byte budget and declared roots.
- src/biointerfaceos/storage.py: typed config, audit, SHA-256 manifest, duplicates, quota guard, raw deletion denial, exclusions, dry-run cleanup, and report writer.
- src/biointerfaceos/cli.py: storage audit --strict command.
- reports/storage_usage.json: deterministic audit report.
- tests/test_storage.py: five focused tests.
- reports/T008_storage.md: this evidence report.

## Safety properties

The audit does not mutate counted files. Temporary files, excluded directories, symlinks, and the generated report are not counted. StorageGuard rejects paths outside declared roots, writes over the soft budget, and all data/raw deletion requests. Cleanup returns candidates without deleting anything.

## Commits

- 98b06471a0081e3277cfe0259d2911644ba72bc6 ? T008 implementation.
- The final state, report, task-ledger, and evidence commit follows after final verification.

## Limitations

No public scientific data or models were accessed. Locked-test payloads were not accessed. T009 network-client work remains pending.
