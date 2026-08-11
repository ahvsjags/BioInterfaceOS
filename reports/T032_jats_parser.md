# T032 JATS/XML Parser Evidence

## Result

T032 is complete on the KAUST Ibex server. The namespace-aware fixture parser emitted a stable document graph while preserving section hierarchy, paragraph order, table metadata, figure links, references, and supplementary links:

- sections: 2
- paragraphs: 5
- tables: 1
- figures: 1
- references: 1
- supplementary links: 2
- parser warnings: 0
- locator round-trip: passed for every emitted node

Each node carries source asset ID, stable XML path locator, node type, text, parent locator, ordinal, and normalized attributes. Tables retain caption, headers, and cells; figures retain graphic href; references retain identifiers in attributes and citation text; supplementary links retain href and link text.

## Safety and warnings

The parser rejects DTD, external entity, SYSTEM, and PUBLIC declarations before XML parsing. Malformed XML fails closed. Missing optional table captions produce explicit warnings without dropping the table node. The fixture contains no live or lockbox payload.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 139 tests passed; ruff, format, and mypy passed.
- pytest -q tests/extract/test_jats.py: exit 0; 3 tests passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Document node counts, warning behavior, unsafe XML rejection, and locator round-trip assertions: passed.
- Task/download/family append-only ledgers validate.

## Limitations

- The parser is validated against sanitized JATS fixtures and does not claim provider-wide XML compatibility.
- It records optional-node warnings but does not infer missing scientific content.
- No PDF fallback, live endpoint, binary download, credential, or lockbox payload was used.
- T033 owns supplementary spreadsheet and archive parsing.

## Artifacts

- src/biointerfaceos/jats_parser.py
- tests/extract/test_jats.py
- tests/fixtures/extract/article.xml
- docs/execplans/T032_jats_parser.md
- reports/T032_jats_parser.md
- TASKS.tsv and PROJECT_STATE.yaml
- T032 sequence-28 record in reports/task_ledger.jsonl

## Commits

- 55ccdd3: namespace-aware JATS parser, stable document graph, fixture, tests, warnings, and unsafe XML gate.
- The completion evidence commit follows this report, plan, ledger, and state update.
