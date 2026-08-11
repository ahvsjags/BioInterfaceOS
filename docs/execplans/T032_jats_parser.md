# T032: Implement JATS/XML full-text parser

## Purpose

Parse public JATS/XML fixtures into a stable document graph that preserves sections, paragraphs, tables, captions, references, supplementary links, and evidence locators.

## Preconditions

T031 is DONE. The policy-gated asset store and provenance receipts are available. Only fixture-backed XML is in scope.

## Non-goals

This task will not parse lockbox payloads, silently drop malformed XML, infer missing scientific claims, or use PDF fallback when required XML fields are absent.

## Interfaces and invariants

Every parsed node has a stable locator composed of source asset ID, XML path, node type, and ordinal. Section hierarchy and paragraph order are preserved. Tables retain captions, headers, cells, and footnotes; figures retain captions and links; references retain identifiers and citation text; supplementary links retain href and link text. Parser warnings are explicit and round-trip locator lookup returns the original node.

## Implementation plan

1. Define document graph and warning schemas.
2. Implement namespace-aware JATS parsing with stable locators and hierarchy.
3. Preserve tables, figures, references, supplementary links, and parser warnings.
4. Add fixture-backed round-trip locator tests and malformed XML handling.
5. Run full gates and record completion evidence.

## Progress

- [x] Define document graph and locator schemas.
- [x] Implement fixture-backed JATS/XML parser.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- pytest -q tests/extract/test_jats.py
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- document node counts and locator round-trip assertions

## Completion note

T032 completed with implementation commit 55ccdd3. The parser preserved all required fixture nodes and passed round-trip locator, warning, malformed XML, and unsafe declaration tests. Completion evidence is recorded in reports/T032_jats_parser.md.

## Failure recovery

Preserve raw XML bytes and provenance hash. Store parser warnings for malformed optional nodes; fail closed for missing required identifiers or unsafe paths.

## Outputs

document graph, stable locator index, parser warnings, fixtures/tests, this ExecPlan, state advancement, and task-ledger evidence.
