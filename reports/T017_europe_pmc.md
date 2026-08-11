# T017 Europe PMC Adapter Evidence

## Result

T017 is complete on the KAUST Ibex server. The repository now contains an anonymous Europe PMC adapter with bounded cursor pagination, policy-gated metadata and asset operations, official full-text and supplementary links, and checksum-gated atomic fetches. T018 is now current; T019 through T025 remain dependency-ready.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 73 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_europe_pmc.py: exit 0; 4 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- biointerfaceos catalog check: CATALOG_VALID.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- Search uses the official Europe PMC REST search endpoint with canonical query parameters, bounded page size/page count, cursor pagination, de-duplication, and terminal/repeated-cursor handling.
- Candidate records preserve accession, source URL, publication date when valid, license signal, and evidence location.
- Metadata and asset listing pass SourcePolicyEngine before transport and expose official JATS and supplementary-file links.
- Fetch requires an explicit SHA-256 in the asset descriptor and delegates to the atomic, host-allowlisted network client.
- Sanitized JSON fixtures cover two cursor pages, CC-BY and CC0 license signals, metadata links, policy rejection, and checksum-gated fetch.
- No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/europe_pmc.py
- tests/sources/test_europe_pmc.py
- tests/fixtures/sources/europe_pmc
- docs/execplans/T017_europe_pmc.md
- reports/T017_europe_pmc.md
- TASKS.tsv and PROJECT_STATE.yaml
- T017 sequence-12 record in reports/task_ledger.jsonl

## Commits

- a8564b8ef06f9de06f45705aeaf4619fbf9033f4 ? T017 adapter, fixtures, tests, and execution plan.
- The completion evidence commit follows this report and ledger update.
