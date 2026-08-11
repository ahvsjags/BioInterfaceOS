# T039 Evidence Resolver and Reverse Trace Evidence

## Result

T039 is complete on the KAUST Ibex server. The resolver checks exact locator membership against extracted table and digitized-figure artifacts, writes a reverse-trace table, and retains conflicts as separate assertion nodes:

- assertions: 6
- resolved: 5
- quarantined broken locators: 1
- conflict nodes: 2
- conflict edges: 1
- review-queue rows: 1
- reverse trace for table cell C3: 2 matching assertions

The two outcome-mean assertions remain separate and are connected by a VALUE_CONFLICT edge. The deliberately missing locator is quarantined rather than repaired. Resolved rows retain source asset ID, path, value, confidence, and exact locator.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 162 tests passed; ruff, format, and mypy passed.
- biointerfaceos evidence trace --fixture --locator asset:asset-table-001/table:table-main/cell:C3: exit 0; assertions=6 resolved=5 quarantined=1 conflict_nodes=2 conflict_edges=1 review_items=1 trace_matches=2.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Fourteen append-only ledgers validate, including task, search, expansion, family-review, download, table, figure, digitization, consensus, and evidence-review ledgers.
- Accepted-field resolution, exact reverse trace, conflict retention, broken-locator quarantine, and review-queue idempotency assertions passed.

## Limitations

- Locator membership is bounded to the committed table-semantics and digitized-figure artifacts.
- Missing locators are quarantined; no source repair or value inference is attempted.
- Conflicts are represented, not adjudicated.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/evidence_resolver.py
- tests/extract/test_evidence.py
- tests/fixtures/evidence/trace_cases.json
- registry/evidence_table.json
- registry/evidence_conflict_graph.json
- registry/evidence_review_queue.jsonl and its seal/snapshot
- reports/evidence_trace.md
- docs/execplans/T039_evidence_resolver.md
- TASKS.tsv and PROJECT_STATE.yaml
- T039 sequence-35 record in reports/task_ledger.jsonl

## Commit

- 43fe09a: resolve evidence locators and conflicts.
