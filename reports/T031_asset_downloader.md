# T031 Policy-Gated Asset Downloader Evidence

## Result

T031 is complete on the KAUST Ibex server. The fixture queue was processed through source policy, lockbox, content-type, size, SHA-256, manifest, and CAS gates:

- first fixture run: 2 assets promoted, 2 quarantined, 2 policy-skipped;
- promoted bytes: 61;
- CAS references/blobs: 2/2;
- source manifest rows: 4 (2 admitted, 2 quarantined);
- download receipts: 6;
- second run: 6 resumable outcomes, no duplicate receipts or blobs;
- release: bioif-data-20260811-42783ef-e32d9290.

The two admitted assets were atomically promoted to the content-addressed store. One admitted candidate failed SHA-256 verification and one failed content-type verification; both payloads were preserved under data/quarantine and their manifest records were changed to quarantined. The unknown-license and login-required candidates were policy-skipped before their fixture paths were read.

## Provenance and safety

Each queue item carries a candidate identity, URL, expected digest, expected size, expected content type, maximum size, fixture flag, and locked-test flag. Each receipt records policy decision, rejection code, expected/actual digest and type, size, asset ID, quarantine path, reason, and locked-test flag. Receipts are append-only and sealed.

The downloader never performs a live network request in fixture mode. The LockboxFirewall rejects protected paths, and policy decisions happen before payload reads. The manifest and CAS index are verified before release freeze.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 136 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_asset_downloader.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos data fetch --fixture: first run promoted=2 quarantined=2 policy_skipped=2 resumed=0 receipts=6 bytes=61.
- .venv/bin/biointerfaceos data fetch --fixture: second run promoted=0 quarantined=0 policy_skipped=0 resumed=6 receipts=6.
- .venv/bin/biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- .venv/bin/biointerfaceos source policy self-test: passed.
- .venv/bin/biointerfaceos lockbox self-test: passed.
- .venv/bin/biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- .venv/bin/biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- .venv/bin/biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Ten append-only ledgers validate, including download receipts.
- Receipt status, manifest counts, CAS references, quarantine count, and resume assertions: passed.

## Limitations

- The queue and payloads are sanitized local fixtures; no live public asset was fetched.
- The downloader does not execute downloaded code or parse scientific contents.
- The existing default release selector can choose an older same-day release by name; the new release was verified explicitly by release ID.
- No credentials, lockbox payloads, or model assets were accessed.
- T032 owns JATS/XML full-text parsing.

## Artifacts

- src/biointerfaceos/asset_downloader.py
- src/biointerfaceos/cli.py
- tests/test_asset_downloader.py
- tests/fixtures/downloads/download_queue.json and payload fixtures
- reports/download_receipts.jsonl and sealed snapshot
- registry/SOURCE_MANIFEST.parquet
- registry/ASSET_INDEX.parquet
- registry/rejected_sources.parquet
- data/cas/sha256/*
- data/quarantine/*
- registry/catalog.duckdb
- release/fixtures/bioif-data-20260811-42783ef-e32d9290
- docs/execplans/T031_asset_downloader.md
- reports/T031_asset_downloader.md
- TASKS.tsv and PROJECT_STATE.yaml
- T031 sequence-27 record in reports/task_ledger.jsonl

## Commits

- 42783ef: policy-gated fixture downloader, queue, receipts, CAS/quarantine fixtures, manifests, catalog, tests, and CLI.
- a24d448: immutable fixture release for the updated manifest and CAS.
- The completion evidence commit follows this report, plan, ledger, and state update.
