# T052 PRIDE Triage and Sample-Plan Evidence

## Result

T052 is complete on the KAUST Ibex server. The development-scope triage produced three auditable PRIDE project cards linked to paper families where available:

- projects: 3
- eligible for split construction: 1 (`PXD000001`)
- parked for review: 1 (`PXD000002`)
- metadata-only locked project: 1 (`PXD000003`)
- sample-map rows: 8
- raw files downloaded: false
- locked payload accessed: false
- pseudo-replicates created: false

`PXD000001` has public result and RAW metadata, captured SHA-256 checksums, resolved family `FAMILY-001`, explicit serum/material arms, and balanced 3+3 sample replicates. `PXD000002` is parked because RAW access is restricted and sample labels do not resolve arms or replicates. `PXD000003` is retained as metadata-only because it is locked and has no raw/search payload access. No ambiguous map was silently repaired.

## Quality gate

All commands ran in `/ibex/user/xup0a/BioInterfaceOS` on CPython 3.11.15:

- `UV_OFFLINE=1 uv lock --check`: exit 0.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: exit 0.
- `UV_OFFLINE=1 make check`: exit 0; 200 tests passed; ruff, format, and mypy passed.
- `biointerfaceos omics pride triage --scope development`: exit 0; projects=3, eligible=1, review=1, metadata_only=1, sample_rows=8, raw_downloaded=false, locked_payload_accessed=false.
- `biointerfaceos report data-coverage`: passed; studies=7, gaps=4, bias_warnings=9, no_imputation=true.
- `biointerfaceos data validate silver --fixture`: passed; 8 tables, 36 rows, 2 quarantined rows.
- `biointerfaceos data validate gold-auto --fixture`: passed; admitted_fields=3, excluded_fields=2, reverse_traces=3.
- `biointerfaceos review export --sample stratified`: passed; packets=3, strata=3, unsigned_packets=3.
- `biointerfaceos assets verify`: references=2, blobs=2, bytes=61.
- `biointerfaceos catalog check`: source_rows=4, asset_rows=2, rejection_rows=9, join_rows=2.
- `biointerfaceos lockbox self-test`: passed; blocked_read=True, field_detected=True, hash_detected=True.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed; files=6, manifest_hash=e32d9290d59f89ffd98bd616540e31529cd27741ee7a97665c42b9dac06c2456.
- `biointerfaceos state validate`: passed; tasks=115.
- `compileall` and `git diff --check`: passed.
- 23 append-only JSONL ledgers validate.

## Artifacts

- `src/biointerfaceos/pride_triage.py`
- `src/biointerfaceos/cli.py`
- `tests/fixtures/omics/pride_triage.json`
- `tests/omics/test_pride_triage.py`
- `reports/omics/pride/project_cards.json` (SHA-256: `56287b931705c1642538e2fb2430d51d596d696baf325be4405710ca0e088857`)
- `reports/omics/pride/sample_maps.json` (SHA-256: `4d0d309296bbe8e25af524dca7e7e72ef8fa0be1a8f387143861e807383d9e34`)
- `reports/omics/pride/split_eligibility.json` (SHA-256: `5780315a719c48c4c8f0e7db3d0c86edf990b3b2a3c84cb3e2a310c212e0f743`)
- `reports/omics/pride/review_queue.json` (SHA-256: `065c3ab1f184e3a4798216c644d30c6687755d8466f659bd3c24d6a62ee6eeda`)
- `reports/omics/pride/triage_receipt.json` (SHA-256: `71a1a44c47a5209787d4dabc3d83f2be62e9f07778754ea152766c96d91a0f00`)
- `tests/fixtures/omics/pride_triage.json` (SHA-256: `433daf63caf7937b914e51e78aa881702a200353a4132b09ed9f5df3d959c9f5`)
- sequence-48 record in `reports/task_ledger.jsonl`

## Limitations

- Project cards and decisions are sanitized fixtures; no live PRIDE endpoint was contacted.
- Only one project is currently split-eligible; the other two remain explicitly excluded or metadata-only.
- The eligible project contains a 2 GB public RAW file, but this task only freezes metadata and checksums; conversion belongs to T053.
