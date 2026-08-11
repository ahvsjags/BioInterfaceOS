# T034 PDF Fallback Parser Evidence

## Result

T034 is complete on the KAUST Ibex server. The bounded fixture parser handled a born-digital PDF text layer and explicitly flagged a textless/scanned fixture:

- born-digital pages: 1
- born-digital blocks: 4
- text blocks: 2
- captions: 1
- tables: 1
- scanned/textless status: SCANNED_OR_TEXTLESS
- OCR attempts: 0
- locator round-trip: passed for every born-digital block

Each block retains source asset ID, page, typed block kind, text, and normalized bounding box. Stable locators use asset ID, page number, and block ordinal.

## Quality gate

The parser requires a PDF header, reads only bounded content streams, and does not execute embedded content or invoke OCR. Textless fixtures retain their source hash and receive an explicit quality warning rather than synthetic text.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 145 tests passed; ruff, format, and mypy passed.
- pytest -q tests/extract/test_pdf.py: exit 0; 3 tests passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Born-digital block typing, page/bbox, textless quality flag, no-OCR, and locator round-trip assertions: passed.
- Task/download/family append-only ledgers validate.

## Limitations

- PDF parsing is fixture-backed and intentionally limited to controlled text streams.
- Textless/scanned inputs are marked for review; no OCR is inserted into the evidence graph.
- No live endpoints, binaries, credentials, repository code, or locked-test payloads were accessed.
- T035 owns semantic table-to-experiment mapping.

## Artifacts

- src/biointerfaceos/pdf_parser.py
- tests/extract/test_pdf.py
- tests/fixtures/extract/born_digital.pdf
- tests/fixtures/extract/scanned.pdf
- docs/execplans/T034_pdf_parser.md
- reports/T034_pdf_parser.md
- TASKS.tsv and PROJECT_STATE.yaml
- T034 sequence-30 record in reports/task_ledger.jsonl

## Commits

- 9556773: bounded PDF text/layout parser, born-digital and scanned fixtures, quality flags, and tests.
- The completion evidence commit follows this report, plan, ledger, and state update.
