# T033 Supplementary Spreadsheet and Archive Parser Evidence

## Result

T033 is complete on the KAUST Ibex server. The parser normalized CSV, TSV, XLSX, and safe ZIP fixture inputs while preserving source hashes and original coordinates:

- XLSX sheets: 1
- XLSX merged ranges: A1:A2 and C1:C2
- multirow header rows: 2
- formula cells retained: B3*2 and B4*2 with cached values
- units retained: mg/mL and a.u.
- CSV and TSV coordinate tables: passed
- safe ZIP member: nested/table.csv
- zip-slip archive: blocked before member read

XLSX parsing is implemented directly against OOXML ZIP parts because the server environment has no spreadsheet Python package requirement. The parser does not execute formulas or archive contents.

## Provenance and safety

Every normalized cell retains source SHA-256, source path, table/sheet/member path, A1 coordinate, row/column indexes, raw value, formula text, unit, and header level. ZIP inventory rejects absolute paths, drive-like paths, traversal components, symlink-like members, encrypted members, and archives exceeding the uncompressed-size limit. Unsupported archive members are preserved as warnings.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 142 tests passed; ruff, format, and mypy passed.
- pytest -q tests/extract/test_supplements.py: exit 0; 3 tests passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- XLSX merged-cell/formula/unit/coordinate, CSV/TSV unit, safe ZIP, and zip-slip assertions: passed.
- Task/download/family append-only ledgers validate.

## Limitations

- XLSX behavior is validated on a sanitized OOXML fixture and does not calculate formulas.
- Unsupported/encrypted archive members are rejected or warned; original bytes remain the provenance source.
- No live endpoints, binary downloads, credentials, repository code, or locked-test payloads were accessed.
- T034 owns born-digital PDF fallback parsing and explicit scanned-PDF handling.

## Artifacts

- src/biointerfaceos/supplements.py
- tests/extract/test_supplements.py
- tests/fixtures/extract/table.xlsx
- tests/fixtures/extract/table.csv
- tests/fixtures/extract/table.tsv
- tests/fixtures/extract/safe.zip
- tests/fixtures/extract/zip_slip.zip
- docs/execplans/T033_supplements.md
- reports/T033_supplements.md
- TASKS.tsv and PROJECT_STATE.yaml
- T033 sequence-29 record in reports/task_ledger.jsonl

## Commits

- 407ad89: safe CSV/TSV/XLSX/ZIP parser, OOXML fixture, security fixtures, and tests.
- The completion evidence commit follows this report, plan, ledger, and state update.
