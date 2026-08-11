# T034: Implement PDF fallback parser

## Purpose

Parse born-digital public PDF fixtures into page-aware layout blocks with stable page/bounding-box locators, preserving text, tables, captions, and explicit scanned-PDF quality flags.

## Preconditions

T031 is DONE. Structured JATS/XML and supplementary parsers remain preferred sources. Only sanitized fixture PDFs are in scope.

## Non-goals

This task will not silently OCR scanned PDFs, infer text absent from the PDF text layer, or replace structured source evidence without a quality receipt.

## Interfaces and invariants

Each layout block retains source hash, page number, block type, text, and normalized bounding box. Tables and captions are explicitly typed. Born-digital fixtures must yield non-empty text blocks. Scanned fixtures are marked SCANNED_OR_TEXTLESS with a warning and no synthetic OCR text. Evidence locator round-trip returns the page/block record.

## Implementation plan

1. Define PDF page/block/quality schemas and stable locators.
2. Implement a fixture parser for born-digital text and bounded layout metadata.
3. Detect textless/scanned fixtures explicitly and emit a quality report.
4. Add page/bbox/table/caption and locator round-trip tests.
5. Run full gates and record completion evidence.

## Progress

- [ ] Define PDF layout and quality schemas.
- [ ] Implement fixture-backed PDF parser and scanned-PDF flag.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- pytest -q tests/extract/test_pdf.py
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- born-digital text, table/caption, scanned quality flag, and locator assertions

## Failure recovery

Preserve original PDF bytes and hash. Mark textless files for manual/OCR review without inserting unverified OCR into the evidence graph.

## Outputs

page layout blocks, PDF quality report, stable locators, fixtures/tests, this ExecPlan, state advancement, and task-ledger evidence.
