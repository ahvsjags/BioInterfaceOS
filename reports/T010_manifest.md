# T010 Source Manifest Evidence

## Result

T010 is complete on the KAUST Ibex server. BioInterfaceOS now has a strict typed source/asset registry backed by a real fixed-schema Parquet file. Admitted, rejected, and quarantined records are represented; required URL, accession, retrieval time, SHA-256, size, license, redistribution, and download fields are validated; identical non-null content hashes are deduplicated. T011 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- uv lock --check: exit 0; lock includes pyarrow 17.0.0 and numpy 2.4.6.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 14 packages checked.
- UV_OFFLINE=1 make check: exit 0; 40 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_manifest.py: exit 0; 7 tests passed.
- .venv/bin/biointerfaceos source manifest validate: SOURCE_MANIFEST_VALID rows=0 unique_content_hashes=0 admitted=0 rejected=0 quarantined=0.
- .venv/bin/biointerfaceos schema validate-all: exit 0; 9 schemas and fixtures valid.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- SourceRecord validates anonymous HTTP(S) URLs without credentials, ISO-8601 timezone-aware retrieval times, publication dates, lowercase SHA-256 values, non-negative sizes, status/access coherence, explicit license and redistribution for admission, and rejection/quarantine reasons.
- Asset IDs are deterministic SHA-256 values of source ID, URL, and content hash.
- ManifestRegistry reads and writes a fixed 16-column Parquet schema atomically through a same-directory temporary file.
- Registration rejects conflicting source identities and returns an existing row for duplicate content hashes without adding a second copy.
- The CLI command source manifest validate performs a full Parquet round trip and deterministic status/hash counts.
- No scientific source, model, credential, or locked-test payload was accessed or downloaded.

## Artifacts

- src/biointerfaceos/manifest.py
- tests/test_manifest.py
- registry/SOURCE_MANIFEST.parquet
- src/biointerfaceos/cli.py
- pyproject.toml and uv.lock
- docs/execplans/T010_source_manifest.md
- reports/T010_manifest.md
- TASKS.tsv and PROJECT_STATE.yaml
- T010 sequence-5 record in reports/task_ledger.jsonl

## Commits

- 593ca7bf98cda1f534629e4787748465a7eb69ca ? T010 implementation, Parquet manifest, CLI, tests, and pinned runtime.
- The completion evidence commit follows this report and ledger update.
