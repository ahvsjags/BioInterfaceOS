# T035 Table-to-Experiment Semantics Evidence

## Result

T035 is complete on the KAUST Ibex server. The fixture-backed parser converts two heterogeneous tables into an evidence-preserving experiment representation:

- tables: 2
- experiment arms: 3
- measurements: 4
- review items: 2
- review-queue rows: 2

The parser retains multi-level header hierarchy, arm identity, sample size, mean/error values, units when reported, footnotes, and exact source cell locators. The ambiguous table remains explicitly unresolved and is routed to the append-only review queue. Re-running the fixture command deduplicates the review records.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 148 tests passed; ruff, format, and mypy passed.
- biointerfaceos extract tables --fixture: exit 0; tables=2 arms=3 measurements=4 review_items=2.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Eleven append-only ledgers validate, including the task, search, expansion, family-review, download, and table-review ledgers.
- Exact cell locator, header hierarchy, unit/error/footnote preservation, ambiguity retention, and review-queue deduplication assertions passed.

## Limitations

- Table semantics are currently fixture-backed and do not infer missing units, sample sizes, or incompatible subtable relationships.
- Formula values are treated as reported values; no formula execution or recomputation is performed.
- Low-confidence or ambiguous mappings remain in the review queue and are not silently promoted.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/table_semantics.py
- tests/extract/test_table_semantics.py
- tests/fixtures/semantics/table_semantics.json
- registry/experiment_table_semantics.json
- registry/table_review_queue.jsonl and its seal/snapshot
- reports/table_semantics.md
- docs/execplans/T035_table_semantics.md
- TASKS.tsv and PROJECT_STATE.yaml
- T035 sequence-31 record in reports/task_ledger.jsonl

## Commit

- bc17172: map fixture tables to experiment semantics.
