# T027 Initial Search and Seed Registry Evidence

## Result

T027 is complete on the KAUST Ibex server. The frozen matrix was executed in fixture-backed development mode and produced append-only run receipts plus a deduplicated candidate registry:

- scope: development, mapped to the train query blocks
- matrix SHA-256: 70c767c0d38cf3a87a196bfa8dc107d8110630264d034ae4a745a5820491800d
- query blocks: 13
- pages/cursors: 15
- raw fixture hits: 17
- unique candidates: 14
- policy-admitted candidates: 13
- quarantined candidates: 1
- persisted search run rows: 13
- persisted candidate rows: 14, all unique by candidate_id
- final run_id: db6ead9f40f83326

The run is explicitly fixture-backed. It is not a claim about real-world literature hit counts and did not contact source endpoints.

## Provenance and firewall

Each run row retains query ID, source, axis, scope, date range, cursor strategy, request URI, page count, response SHA-256 list, timestamp, matrix hash, fixture flag, and locked-test flag. Each candidate row retains source/accession key, title, license signal, policy decision, query IDs, scope, URL, response hashes, run ID, and locked-test flag.

Training candidates end at 2023-12-31. The runner validates the matrix before execution and never reads, stores, or searches the 2025-01-01 through 2026-08-11 lockbox interval. Re-running the same fixture appends a new run receipt but does not duplicate candidate rows.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 124 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_search_runner.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos search validate-queries: matrix valid with 22 queries and the frozen SHA-256 above.
- .venv/bin/biointerfaceos search run --scope development: SEARCH_RUN_VALID query_blocks=13 pages=15 raw_hits=17 unique_candidates=14 admitted=13 quarantined=1 fixture=true.
- .venv/bin/biointerfaceos source policy self-test: SOURCE_POLICY_VALID fixtures=10 rejected_or_quarantined=7 registry_rows=7.
- .venv/bin/biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- .venv/bin/biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- .venv/bin/biointerfaceos catalog check: CATALOG_VALID.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- Six append-only ledgers validate: four project ledgers plus search-runs and candidate ledgers.
- Candidate uniqueness assertion: 14 rows and 14 unique candidate IDs.

## Implemented behavior

- Matrix scope filtering maps development to frozen train queries and validation to the separate 2024 scope.
- Fixture pages use explicit cursors; repeated or mismatched cursors fail.
- Response bytes receive stable SHA-256 hashes; candidate IDs are source plus accession and deduplicate across pages/query blocks/reruns.
- Policy is evaluated for each hit before a candidate is admitted; missing licenses are retained as quarantined candidates.
- Search receipts are append-only and sealed; candidate registry rows are append-only and sealed.
- No binary assets were downloaded and no code was executed.

## Limitations

- This is a sanitized fixture-backed seed run; real public-source retrieval remains a separate bounded operation and is not represented as completed here.
- Candidate titles and accessions in the fixture are synthetic; they are wiring/evidence tests, not scientific evidence.
- T028 owns citation expansion, dataset/code links and paper-family deduplication over real public metadata.
- No lockbox semantic payload or associated data was accessed.

## Artifacts

- reports/search_runs.jsonl
- registry/search_candidates.jsonl
- tests/fixtures/search/search_results.json
- src/biointerfaceos/search_runner.py
- tests/test_search_runner.py
- src/biointerfaceos/cli.py
- docs/execplans/T027_initial_search.md
- reports/T027_initial_search.md
- TASKS.tsv and PROJECT_STATE.yaml
- T027 sequence-22 record in reports/task_ledger.jsonl

## Commits

- 280a5904f47c59654bab807d4736a831af1a5eb9: fixture-backed runner, sealed receipts, deduplicated candidate registry, fixtures and tests.
- The completion evidence commit follows this report and ledger update.
