# T050 Extraction Benchmark Evidence

## Result

T050 is complete on the KAUST Ibex server. The fixture-backed extraction benchmark covers numeric, entity, arm, and evidence fields, reports calibration by modality/material/year, emits an explicit error taxonomy and model card, and evaluates the G2 automatic-field gate.

- rows: 8
- correct: 4
- errors: 4
- overall accuracy: 0.5
- automatic confidence threshold: 0.85
- eligible rows: 4
- eligible correct: 4
- eligible precision: 1.0
- eligible recall: 1.0
- expected calibration error: 0.05500000000000002
- G2 status: PASS
- locked-test payload accessed: false

The four errors are retained with source locators and classified as `NUMERIC_VALUE_MISMATCH`, `ENTITY_RESOLUTION_ERROR`, `ARM_LABEL_ERROR`, and `EVIDENCE_LOCATOR_UNRESOLVED`. The model card explicitly limits the result to sanitized fixtures and does not claim expert validation.

## Quality gate

All commands ran in `/ibex/user/xup0a/BioInterfaceOS` on CPython 3.11.15:

- `UV_OFFLINE=1 uv lock --check`: exit 0.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: exit 0.
- `UV_OFFLINE=1 make check`: exit 0; 194 tests passed; ruff, format, and mypy passed.
- `biointerfaceos benchmark extraction`: exit 0; rows=8, correct=4, errors=4, eligible=4, precision=1.000, recall=1.000, calibration_error=0.055, G2 PASS.
- `biointerfaceos data build-bronze --fixture`, `data build-silver --fixture`, and `data build-gold-auto --fixture`: passed with the existing immutable release hashes.
- `biointerfaceos data validate silver --fixture` and `data validate gold-auto --fixture`: passed.
- `biointerfaceos review export --sample stratified`: passed; packets=3, strata=3, unsigned_packets=3.
- `biointerfaceos assets verify`: references=2, blobs=2, bytes=61.
- `biointerfaceos catalog check`: source_rows=4, asset_rows=2, rejection_rows=9, join_rows=2.
- `biointerfaceos lockbox self-test`: passed; blocked_read=True, field_detected=True, hash_detected=True.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed; files=6, manifest_hash=e32d9290d59f89ffd98bd616540e31529cd27741ee7a97665c42b9dac06c2456.
- `biointerfaceos state validate`: passed; tasks=115.
- `compileall` and `git diff --check`: passed.
- 23 append-only JSONL ledgers validate.

`catalog build` was not used as a final gate because it rewrites the DuckDB binary and changes the frozen release hash; the generated mutation was restored to the committed frozen artifact, and the read-only catalog/release checks then passed.

## Artifacts

- `src/biointerfaceos/extraction_benchmark.py`
- `src/biointerfaceos/cli.py`
- `tests/fixtures/benchmark/extraction.json`
- `tests/benchmark/test_extraction.py`
- `reports/benchmark/extraction_metrics.json` (SHA-256: `591f19129979985cb26394f670a6bd1fadb2f510891e48c6fcdecab43ed1df60`)
- `reports/benchmark/calibration.json` (SHA-256: `0ad54ad4e7a83ad08411ddc6ad7e81eb3e29bb2743211b0c7e03bb4ef593ae85`)
- `reports/benchmark/error_taxonomy.json` (SHA-256: `54eb3a4f9f9db6c52b737d2699b9c79390b157b09420fb56c9165dee14e4968e`)
- `reports/benchmark/model_card.json` (SHA-256: `9c99c08c9ff673939ab9bb3b38ae5d5d14f33a50387526c6903150621197996f`)
- `reports/benchmark/benchmark_receipt.json` (SHA-256: `096ecc8a263e1f41268b2004decae90d23528a1c4ffffcf6c8227888d0854712`)
- `tests/fixtures/benchmark/extraction.json` (SHA-256: `c4391035ad37cf332a89b5ab22336d0e10ad951126656118f13783abe96c8971`)
- sequence-46 record in `reports/task_ledger.jsonl`

## Limitations

- Benchmark rows are sanitized fixtures and do not represent signed expert review.
- High-confidence gating does not resolve missing or ambiguous evidence.
- No live endpoints, credentials, model downloads, or locked-test payloads were accessed.
