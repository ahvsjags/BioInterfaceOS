# T047 Normalized Silver Data Release Evidence

## Result

T047 is complete on the KAUST Ibex server. Silver tables were assembled from the immutable Bronze release and completed normalization registries with stable primary keys and evidence locators.

- release ID: bioif-silver-b05bdbc371d43cae
- manifest hash: b05bdbc371d43cae6c906f8a61261d0eeb75a57776ba21d8b9b456be304c2c16
- schema hash: 072116d15775130a1fe24df8f11137bed8d72dc45af5701381dc777b5f6c6c1f
- tables: 8
- total rows: 36
- quarantined rows: 2
- evidence coverage: 1.000
- duplicate primary keys: 0
- referential integrity errors: 0
- critical QC flags: 4; critical QC unquarantined: 0

Silver rows retain source/evidence locators and original payload JSON. Invalid formulations and broken-evidence rows remain explicit quarantine statuses; no row is silently dropped and Bronze bytes are untouched.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 187 tests passed; ruff, format, and mypy passed.
- biointerfaceos data build-silver --fixture: exit 0; tables=8 rows=36 quarantined_rows=2.
- biointerfaceos data validate silver --fixture: exit 0; schema, checksum, primary-key, evidence, referential-integrity, and critical-QC gates passed.
- biointerfaceos release verify bronze: passed.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed; tasks=115.
- compileall and git diff --check: passed.
- 23 append-only JSONL ledgers validate.

## Artifacts

- src/biointerfaceos/silver_release.py
- src/biointerfaceos/cli.py
- tests/fixtures/silver/silver_expectations.json
- tests/silver/test_silver.py
- data/silver/silver_manifest.json
- release/silver/bioif-silver-b05bdbc371d43cae/silver_manifest.json (SHA-256: d55cabf07a3a44f877e76d00aed76a3a8f52d5eedef46790727f4c91fa440b12)
- release/silver/bioif-silver-b05bdbc371d43cae/silver_qc_report.json (SHA-256: 6dd52ee6122532fc69bf62a5bed47b757e1d503c5816a1170bb7d782d91225a5)
- release/silver/bioif-silver-b05bdbc371d43cae/checksums.txt (SHA-256: b74413441542006ba8adb02566cc28f1ba67e444b2e9a252a10f6026c7d36c68)
- release/silver/bioif-silver-b05bdbc371d43cae/rebuild_receipt.json (SHA-256: fb29ee7acea332b9daa70d5d21b0e523879e6222f651e1d04b08668bc9821ad7)
- docs/execplans/T047_silver_data_release.md
- sequence-43 record in reports/task_ledger.jsonl

## Limitations

- Silver assembly is fixture-backed and offline.
- Quarantined rows remain excluded from accepted clean analytical use until reviewed.
- No live source data or locked-test payloads were accessed.
