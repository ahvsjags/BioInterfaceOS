# T028 Citation and Linked-Resource Expansion Evidence

## Result

T028 is complete on the KAUST Ibex server. The T027 seed registry was expanded through a bounded, fixture-backed citation/dataset/code graph with append-only provenance receipts:

- scope: development
- maximum depth: 2
- seed candidates: 14
- raw expansion edges: 44
- unique normalized targets: 17
- policy-admitted targets: 16
- quarantined targets: 1
- persisted expansion run rows: 29
- persisted expansion edge rows: 17
- final run ID: 49c6f2df4656d93f

The fixture contains citation, dataset, supplement/code, DOI, accession, and URL aliases. Shared DOI and URL targets collapse by stable normalized keys, while parent IDs and edge types remain preserved. This is a deterministic wiring and policy test; it is not a claim about live literature coverage or scientific validity.

## Provenance and policy

Each run receipt records the parent candidate, depth, scope, fixture status, response SHA-256, timestamp, and locked-test flag. Each edge records parent IDs, edge types, normalized target key, source, DOI/accession/URL, title, response hash, license signal, decision, rejection code, and depth.

The expansion runner validates the frozen query matrix before loading seed candidates, enforces development scope and a maximum depth of two, and applies the existing source/license policy before admission. The one license-ambiguous code target remains QUARANTINE. No binary asset, repository code, credential, or lockbox payload was downloaded or executed.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 127 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_expansion.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos search validate-queries: matrix valid.
- .venv/bin/biointerfaceos search expand --depth 2 --scope development: SEARCH_EXPANSION_VALID scope=development depth=2 seed_candidates=14 raw_edges=44 unique_targets=17 admitted=16 quarantined=1 fixture=true.
- .venv/bin/biointerfaceos source policy self-test: passed.
- .venv/bin/biointerfaceos lockbox self-test: passed.
- .venv/bin/biointerfaceos release verify --fixture: passed.
- .venv/bin/biointerfaceos catalog check: passed.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- Eight append-only ledgers validate: project ledgers, search run/candidate ledgers, and expansion run/edge ledgers.
- Expansion edge uniqueness assertion: 17 rows and 17 unique target_key values.

## Implemented behavior

- Citation, dataset, supplement, and code/repository links are represented as typed provenance edges.
- DOI, source accession, and normalized URL aliases deduplicate deterministically without merging incompatible records.
- Expansion is bounded to depth two and does not inspect locked-test content.
- Every target is policy-evaluated before admission; unsupported or ambiguous licensing is preserved as quarantine.
- Run receipts and edge records are append-only, sealed, and resumable without rewriting seed records.
- The CLI exposes biointerfaceos search expand --depth {1,2} --scope {development,validation}.

## Limitations

- The current run is fixture-backed; it does not represent live public-source counts.
- Fixture titles, accessions, and URLs are synthetic and only test graph wiring, deduplication, and policy behavior.
- No binaries, lockbox payloads, or repository code were accessed.
- T029 owns saturation analysis and coverage-gap proposals.

## Artifacts

- reports/expansion_runs.jsonl
- registry/expansion_edges.jsonl
- tests/fixtures/expansion/expansion_results.json
- src/biointerfaceos/expansion.py
- tests/test_expansion.py
- src/biointerfaceos/cli.py
- docs/execplans/T028_expand_links.md
- reports/T028_expand_links.md
- TASKS.tsv and PROJECT_STATE.yaml
- T028 sequence-23 record in reports/task_ledger.jsonl

## Commits

- 5cfec88: fixture-backed bounded citation/dataset/code expansion, sealed receipts, deduplicated edge registry, fixtures, and tests.
- The completion evidence commit follows this report, plan, ledger, and state update.
