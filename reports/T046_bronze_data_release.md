# T046 Immutable Bronze Data Release Evidence

## Result

T046 is complete on the KAUST Ibex server. The Bronze builder creates a deterministic, immutable release from admitted CAS assets and bounded parsed fixtures.

- release ID: bioif-bronze-54639b3ded1a4d4d
- manifest hash: 54639b3ded1a4d4d279d953a2c7f37d9736d198335db08c5312d861541a8000f
- raw admitted assets represented as CAS pointers: 2
- parsed assets embedded: 3
- restricted pointer-only assets: 1
- total manifest assets: 6
- separated license tiers: 3

The builder never rewrites Bronze/raw values. Admitted raw assets point to the content-addressed store, parsed outputs are deterministic JSON artifacts, and the restricted fixture is represented only by metadata/pointer with no payload read.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 184 tests passed; ruff, format, and mypy passed.
- biointerfaceos data build-bronze --fixture: exit 0; raw_assets=2 parsed_assets=3 pointer_assets=1 license_tiers=3.
- biointerfaceos release verify bronze: exit 0; immutable release, exact rebuild, checksum, and CAS-pointer checks passed.
- Rebuilding the same fixture returned the same release ID and manifest hash without overwriting the existing release.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos state validate: passed; tasks=115.
- compileall and git diff --check: passed.
- 23 append-only JSONL ledgers validate.

## Artifacts

- src/biointerfaceos/bronze_release.py
- src/biointerfaceos/cli.py
- tests/fixtures/bronze/bronze_inputs.json
- tests/bronze/test_bronze.py
- data/bronze/bronze_manifest.json
- release/bronze/bioif-bronze-54639b3ded1a4d4d/bronze_manifest.json (SHA-256: c299c44973ca314be0a10be88dfb4c1028914f9bf91be3975985bb110d5454f7)
- release/bronze/bioif-bronze-54639b3ded1a4d4d/license_tiers.json
- release/bronze/bioif-bronze-54639b3ded1a4d4d/checksums.txt (SHA-256: 76b46f9747951502a3ca99615720cb4a47ef82b6fb0611e0750ba02c251caf59)
- release/bronze/bioif-bronze-54639b3ded1a4d4d/rebuild_receipt.json (SHA-256: 371aa56fb8f2a9d073c61ab3684621a1673c3a383bd87464a250e59412fe9183)
- docs/execplans/T046_bronze_data_release.md
- sequence-42 record in reports/task_ledger.jsonl

## Limitations

- Bronze assembly is fixture-backed and does not contact live sources.
- Parsed content is bounded to the existing deterministic fixture parsers.
- Restricted assets are pointers only; no restricted payload is stored or accessed.
