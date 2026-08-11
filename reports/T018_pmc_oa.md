# T018 PMC Open Access Adapter Evidence

## Result

T018 is complete on the KAUST Ibex server. The repository now contains an anonymous PMC Open Access Web Service adapter that preserves OA membership and non-OA metadata pointers, admits only explicit configured licenses, lists OA package/JATS/PDF/figure/supplementary links, records response hashes, and requires a manifest checksum for fetch promotion. T019 is now current; T020 through T025 remain dependency-ready.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 79 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_pmc_oa.py: exit 0; 6 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- biointerfaceos catalog check: CATALOG_VALID.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- The adapter uses only the official PMC OA Web Service file-list endpoint and official NCBI/FTP links; it does not scrape ordinary article pages.
- Explicit PMC accessions resolve to OA records or retained non-OA metadata pointers.
- OA candidates carry the provider license signal and pass SourcePolicyEngine before metadata, asset listing, or fetch.
- Supported file formats map to OA package, JATS, PDF, figure, and supplementary asset descriptors.
- FTP links are normalized to official HTTPS endpoints, and fetches require an explicit SHA-256 through the atomic network client.
- Sanitized XML fixtures cover admitted OA content and an idIsNotOpenAccess response; tests verify response hashing, policy rejection, asset typing, and atomic checksum-gated fetch.
- No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/pmc_oa.py
- tests/sources/test_pmc_oa.py
- tests/fixtures/sources/pmc_oa
- docs/execplans/T018_pmc_oa.md
- reports/T018_pmc_oa.md
- TASKS.tsv and PROJECT_STATE.yaml
- T018 sequence-13 record in reports/task_ledger.jsonl

## Commits

- da4c22fcf9b1b81a79de939368ea1f515f8a5434 ? T018 adapter, OA fixtures, and tests.
- The completion evidence commit follows this report and ledger update.
