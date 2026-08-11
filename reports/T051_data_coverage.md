# T051 Data Coverage and Missingness Evidence

## Result

T051 is complete on the KAUST Ibex server. The audit joins the immutable Silver release to the sealed search-candidate registry and counts stable `study_id` units rather than candidate rows or extracted fields.

- independent study units: 7
- search candidate rows: 14
- admitted search candidates: 13
- represented admitted candidates: 7
- missing values across required dimensions: 4
  - lab: 2
  - species: 1
  - publication year/date: 1
- coverage gaps: 4
  - material: silica
  - endpoints: hemolysis, endosomal_escape
  - date: 2024
- bias/missingness warnings: 9
- no imputation or pseudo-replicates: true

Coverage is reported by study, lab, material, species, endpoint, date, and evidence status. The missingness model provides overall rates and descriptive profiles by source, Silver status, and search scope; it makes no causal claim. One Silver row remains `REVIEW_REQUIRED` and is retained as an explicit warning rather than promoted.

## Quality gate

All commands ran in `/ibex/user/xup0a/BioInterfaceOS` on CPython 3.11.15:

- `UV_OFFLINE=1 uv lock --check`: exit 0.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: exit 0.
- `UV_OFFLINE=1 make check`: exit 0; 197 tests passed; ruff, format, and mypy passed.
- `biointerfaceos report data-coverage`: exit 0; studies=7, admitted_candidates=13, represented_candidates=7, missing_values=4, gaps=4, bias_warnings=9, no_imputation=true.
- `biointerfaceos data validate silver --fixture`: passed; release `bioif-silver-b05bdbc371d43cae`, 8 tables, 36 rows, 2 quarantined rows.
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

- `src/biointerfaceos/coverage_audit.py`
- `src/biointerfaceos/cli.py`
- `tests/fixtures/coverage/data_coverage.json`
- `tests/coverage/test_coverage.py`
- `reports/data_coverage/coverage_tables.json` (SHA-256: `3f28797ca709bb30393840a8cdc0fefe7d75fb5b6cab7944cfb7e15239406af5`)
- `reports/data_coverage/coverage_report.json` (SHA-256: `ee7061c70467a1604dfee58a451ab870493a804f088009f33e5b109669ee36d8`)
- `reports/data_coverage/missingness_model.json` (SHA-256: `681a264b71a5b638c1e2548a6c7dbb20860036d36f5b06dc57e6bd45e6e47cc1`)
- `reports/data_coverage/bias_warnings.json` (SHA-256: `d7cff4ca0e083917164074992a88e9272ed1504a6efd795424a2090fd8e5a678`)
- `reports/data_coverage/data_coverage_receipt.json` (SHA-256: `6253fb4abad60e83bbb8169387592385592c952b8833527cde280ca3ade5ae81`)
- `tests/fixtures/coverage/data_coverage.json` (SHA-256: `e394e3732d08bd314102f0c0a06117902e57460a04b5ec2409d63a84471d93a1`)
- sequence-47 record in `reports/task_ledger.jsonl`

## Limitations and actions

- The fixture is sanitized and does not represent live literature prevalence.
- Six admitted candidates remain unmapped to independent study rows; they require study-identity resolution or targeted search.
- Missing lab/species/date fields remain missing; scope reduction or targeted search is required before downstream claims.
- No live endpoints, credentials, model downloads, or locked-test payloads were accessed.
