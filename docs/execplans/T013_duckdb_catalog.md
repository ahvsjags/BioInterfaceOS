# T013: Implement DuckDB analytical catalog

## Purpose

Build a reproducible local analytical catalog whose views are backed by the authoritative Parquet registries, with explicit schema version and idempotent migrations.

## Preconditions

T007 and T010 are DONE, T013 is READY/current, PyArrow and DuckDB are available from pinned project dependencies, and no scientific or locked-test payload needs to be accessed.

## Non-goals

This task does not create a second source of truth, mutate raw data, infer scientific values, or read data/locked_test. The database is a rebuildable query layer over Parquet.

## Interfaces and invariants

Catalog.build creates registry/catalog.duckdb, catalog_meta with schema_version 1, and views source_manifest, asset_index, rejected_sources, and asset_provenance. Each view reads its corresponding repository Parquet file through DuckDB read_parquet. Catalog.check verifies input containment, file existence, schema version, view columns, and idempotent row counts. Migrations are versioned and fail closed on a future schema.

## Implementation plan

1. Add pinned DuckDB runtime and lock update.
2. Implement catalog build/check/query helpers and Parquet-backed views.
3. Add catalog CLI build/check commands.
4. Add temporary-repository tests for idempotence, schema metadata, core joins, and missing-input failure.
5. Run offline lock/sync, full/focused tests, CLI/state/schema checks, compileall, and diff checks.
6. Record evidence, advance T013/T014 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read T013 contract, GOAL DuckDB/Parquet requirement, current registries, and selected DuckDB 1.5.5 cached runtime.
- [ ] Implement and test the catalog.
- [ ] Run acceptance gates and record completion evidence.

## Discoveries

DuckDB was not initially installed, but a CPython 3.11 Linux 1.5.5 wheel is available in the KAUST uv cache. The existing empty Parquet registries are suitable smoke-test inputs.

## Decisions

Use read_parquet views over registry Parquet files and keep the DuckDB file derived. Store only schema/build metadata in DuckDB; never copy authoritative rows into a mutable table.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_catalog.py
- biointerfaceos catalog build
- biointerfaceos catalog check
- biointerfaceos state validate
- .venv/bin/python -m compileall -q src tests
- git diff --check
- idempotent build and authoritative-input assertions

## Failure recovery

If a view or migration fails, close the database and rebuild it from the Parquet files. Never repair the database by editing copied analytical rows. Preserve prior database bytes until a new build succeeds.

## Outputs

src/biointerfaceos/catalog.py, tests/test_catalog.py, registry/catalog.duckdb, catalog CLI, this ExecPlan, reports/T013_catalog.md, state advancement, and task-ledger evidence.

## Completion note

Pending implementation and acceptance validation.
