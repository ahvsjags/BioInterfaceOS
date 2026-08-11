# T014 Immutable Release Evidence

## Result

T014 is complete on the KAUST Ibex server. BioInterfaceOS can create and verify an immutable fixture release with canonical input manifest, checksums, data/config hashes, Git receipt, and read-only release contents. Existing release names cannot be overwritten. T015 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- uv lock --check: exit 0; lock includes duckdb 1.5.5, pyarrow 17.0.0, and pyyaml 6.0.2.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 61 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_release.py: exit 0; 4 tests passed.
- biointerfaceos release freeze --fixture: exit 0; release ID bioif-data-20260811-73c256f-b00f5ab3.
- biointerfaceos release verify --fixture: exit 0; 6 input files and manifest hash b00f5ab33bd84711d99fb5eb88fffab328287f9fa022d0ff4d478cb54a186b06 verified.
- biointerfaceos catalog check: exit 0.
- biointerfaceos source manifest validate: exit 0.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- Release inputs are the source, asset, and rejection Parquet registries, derived catalog, source policy, and source schema.
- release_manifest.json stores sorted path/size/SHA-256 entries plus manifest/data/config hashes.
- checksums.txt is generated from the same canonical entries.
- release_receipt.json records fixture/frozen status, release ID, Git commit, hashes, timestamp, and file count.
- The release directory and its files are non-writable. Re-freezing the same identity is rejected; changed input or receipt/checksum bytes fail verification.
- The receipt records the clean parent commit 73c256f used when the fixture was frozen; the implementation and evidence commits preserve that immutable release without rewriting it.
- No scientific source, model, credential, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/release.py
- release/fixtures/bioif-data-20260811-73c256f-b00f5ab3
- src/biointerfaceos/cli.py
- tests/test_release.py
- docs/execplans/T014_release_checksums.md
- reports/T014_release.md
- TASKS.tsv and PROJECT_STATE.yaml
- T014 sequence-9 record in reports/task_ledger.jsonl

## Commits

- 3fc5fa3570eb8781d3de37c7e70152674a8a8129 ? T014 release freezer, verifier, CLI, tests, and frozen fixture.
- The completion evidence commit follows this report and ledger update.
