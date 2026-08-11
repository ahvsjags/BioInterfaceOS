# T020 GEO/SRA Adapter Evidence

## Result

T020 is complete on the KAUST Ibex server. The repository now contains an anonymous GEO/SRA adapter using NCBI GEO SOFT metadata and SRA RunInfo, mapping GSE/GSM/SRP/SRR relationships, linking processed matrices/SOFT/supplementary files and SRA raw runs, recording response hashes, and rejecting controlled-access records before asset operations. T021 is now current; T022 through T025 remain dependency-ready.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 89 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_geo.py: exit 0; 5 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- biointerfaceos catalog check: CATALOG_VALID.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- GSE/GSM metadata uses the official NCBI GEO accession endpoint and parses SOFT key/value records.
- Series metadata preserves sample GSM IDs, BioProject IDs, SRA study/run relations, organisms, explicit fixture license fields, request URL, and response SHA-256.
- Official GEO FTP paths are generated for series matrix, family SOFT, supplementary files, and SRA RunInfo-provided raw links.
- SRA RunInfo CSV is parsed for study, BioProject, BioSample, organism, platform, visibility, raw URL, and checksum.
- Controlled-access/dbGaP-like metadata sets policy access flags and is rejected before metadata/list/fetch transport.
- Sanitized fixtures cover GSE/GSM/SRP/SRR mapping, processed and raw links, SRA response hashing, checksum-gated fetch, and restricted records.
- No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/geo.py
- tests/sources/test_geo.py
- tests/fixtures/sources/geo
- docs/execplans/T020_geo.md
- reports/T020_geo.md
- TASKS.tsv and PROJECT_STATE.yaml
- T020 sequence-15 record in reports/task_ledger.jsonl

## Commits

- eaeaef9a49e7e9c562202b5689acb0bd59d9def6 ? T020 adapter, fixtures, and tests.
- The completion evidence commit follows this report and ledger update.
