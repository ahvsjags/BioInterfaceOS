# T013 DuckDB Catalog Evidence

## Result

T013 is complete on the KAUST Ibex server. BioInterfaceOS now has a pinned DuckDB 1.5.5 catalog that is derived from authoritative Parquet registries, records schema version and input hashes, exposes reproducible views and a core asset-provenance join, and fails closed when inputs change. T014 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- uv lock --check: exit 0; lock includes duckdb 1.5.5, pyarrow 17.0.0, and pyyaml 6.0.2.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 57 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_catalog.py: exit 0; 4 tests passed.
- biointerfaceos catalog build: CATALOG_VALID schema_version=1 source_rows=0 asset_rows=0 rejection_rows=7 join_rows=0.
- biointerfaceos catalog check: same deterministic counts and exit 0.
- biointerfaceos source manifest validate: exit 0.
- biointerfaceos assets verify: exit 0.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- Catalog.build creates registry/catalog.duckdb and read_parquet views source_manifest, asset_index, rejected_sources, and asset_provenance.
- catalog_meta stores schema_version 1 and SHA-256 hashes of every authoritative Parquet input.
- Catalog.check validates view availability, input hashes, row counts, and the core asset-manifest join; changed or missing inputs fail closed.
- Rebuilding twice is idempotent and the database remains a derived query layer, not the source of truth.
- Read-only query guard rejects mutating SQL. No scientific source, model, credential, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/catalog.py
- registry/catalog.duckdb
- src/biointerfaceos/cli.py
- tests/test_catalog.py
- pyproject.toml and uv.lock
- docs/execplans/T013_duckdb_catalog.md
- reports/T013_catalog.md
- TASKS.tsv and PROJECT_STATE.yaml
- T013 sequence-8 record in reports/task_ledger.jsonl

## Commits

- 9a55980da59b8652ab222c516c014f9991bf8cbe ? T013 DuckDB catalog, CLI, tests, dependency lock, and derived database.
- The completion evidence commit follows this report and ledger update.
