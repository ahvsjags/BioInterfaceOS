# T019 PRIDE/ProteomeXchange Adapter Evidence

## Result

T019 is complete on the KAUST Ibex server. The repository now contains an anonymous PRIDE Archive adapter using the official REST v3 project/search and file-path interfaces, with project metadata, accession/date/species/instrument fields, file manifests, checksum projection, restricted-asset filtering, large-file dry-run, and resumable checksum-verified fetch. T020 is now current; T021 through T025 remain dependency-ready.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 84 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_pride.py: exit 0; 5 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- biointerfaceos catalog check: CATALOG_VALID.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- Project accession queries use the official PRIDE Archive v3 project endpoint; keyword queries use the official paginated search endpoint.
- Project metadata preserves accession, title, submission/publication dates, organisms, instruments, DOI, license, request URL, and response SHA-256.
- The file-path manifest parser accepts official project file records, normalizes official FTP links to HTTPS, captures sizes/checksums/categories, and skips restricted/private/unavailable entries.
- Only explicit public/analysis licenses admitted by SourcePolicyEngine reach metadata, asset listing, dry-run, or fetch.
- Dry-run reports large-file status without downloading; fetch delegates resumable range handling and atomic SHA-256 promotion to AnonymousHttpClient.
- Sanitized fixtures cover project search, metadata, file manifests, SHA-256, a restricted file, a 2 GB dry-run, and a 206 resume response.
- No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/pride.py
- tests/sources/test_pride.py
- tests/fixtures/sources/pride
- docs/execplans/T019_pride.md
- reports/T019_pride.md
- TASKS.tsv and PROJECT_STATE.yaml
- T019 sequence-14 record in reports/task_ledger.jsonl

## Commits

- b8111b46332e370e05c41e5259f950c605ec1ac6 ? T019 adapter, fixtures, and tests.
- The completion evidence commit follows this report and ledger update.
