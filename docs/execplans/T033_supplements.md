# T033: Implement supplementary spreadsheet and archive parser

## Purpose

Inventory and normalize public supplementary CSV/TSV/XLSX/ZIP fixtures while preserving original sheet, row, column, cell-coordinate, unit, formula, and archive-member provenance.

## Preconditions

T031 and T007 are DONE. The policy-gated asset store, safe path utilities, and fixture provenance contracts are available.

## Non-goals

This task will not execute spreadsheet formulas or archive contents, extract encrypted archives, follow unsafe symlinks, or trust archive member paths without zip-slip checks.

## Interfaces and invariants

Every normalized cell retains original workbook/sheet/member path, A1 coordinate, row/column indexes, raw value, formula text when present, unit metadata, and source hash. Merged cells and multirow headers are represented explicitly. ZIP extraction is confined to a repository-contained temporary namespace; absolute paths, traversal, and symlink-like members are blocked and quarantined.

## Implementation plan

1. Define supplement inventory, table, cell, and archive-warning schemas.
2. Implement CSV/TSV parsing with original coordinates and unit/header detection.
3. Implement XLSX sheet, merged-cell, formula, and multirow-header preservation.
4. Implement safe ZIP inventory/extraction with zip-slip and unsupported/encrypted gates.
5. Add fixture-backed normalized table outputs and focused security tests.
6. Run full gates and record completion evidence.

## Progress

- [x] Define supplement inventory and normalized cell schemas.
- [x] Implement spreadsheet parsing and safe archive handling.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- pytest -q tests/extract/test_supplements.py
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- merged-cell, multirow-header, units, formulas, coordinate, and zip-slip assertions

## Completion note

T033 completed with implementation commit 407ad89. CSV/TSV/XLSX/ZIP fixtures pass coordinate, unit, formula, merged-cell, and archive traversal gates. Completion evidence is recorded in reports/T033_supplements.md.

## Failure recovery

Preserve original source bytes and hashes. Quarantine unsupported/encrypted archives and malformed tables with warnings; never overwrite normalized outputs or delete original coordinates.

## Outputs

supplement inventory, normalized tables/cells, archive safety receipts, fixtures/tests, this ExecPlan, state advancement, and task-ledger evidence.
