# T038 Dual-Path Structured Extraction Evidence

## Result

T038 is complete on the KAUST Ibex server. One sanitized experiment record is emitted through two offline paths using the same versioned field schema:

- records: 1
- deterministic-rule fields: 5
- offline-mock fields: 5
- agreements: 4
- disagreements: 1
- accepted consensus fields: 4
- consensus review rows: 1

Every field in both paths carries one or more exact asset locators. The disagreement retains both path values and evidence, has no accepted value, and is routed to the append-only consensus review queue. The mock path records offline backend metadata and network_accessed=false.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 159 tests passed; ruff, format, and mypy passed.
- biointerfaceos extract experiment --fixture --dual: exit 0; records=1 rule_fields=5 mock_fields=5 agreements=4 disagreements=1 accepted_fields=4 review_items=1.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Thirteen append-only ledgers validate, including task, search, expansion, family-review, download, figure, digitization, and consensus-review ledgers.
- Path schema equality, locator completeness, accepted-field count, disagreement retention, no-accepted-value, offline-mock, and review-queue idempotency assertions passed.

## Limitations

- The second extraction path is an offline deterministic mock, not a private or hosted model.
- Fixture values are intentionally bounded; no field is inferred without evidence.
- Disagreements remain unresolved until a later consensus/adjudication task.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/experiment_extraction.py
- tests/extract/test_experiment.py
- tests/fixtures/extract/dual_experiment.json
- registry/experiment_candidates.json
- registry/experiment_consensus.json
- registry/consensus_review_queue.jsonl and its seal/snapshot
- reports/dual_extraction.md
- docs/execplans/T038_dual_path_extraction.md
- TASKS.tsv and PROJECT_STATE.yaml
- T038 sequence-34 record in reports/task_ledger.jsonl

## Commit

- 919f076: compare dual-path experiment extraction.
