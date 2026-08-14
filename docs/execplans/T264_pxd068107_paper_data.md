# T264: PXD068107 paper-derived real-data technical OOD

## Purpose

Convert a license-resolved full-text/public-repository source into a real, row-traceable model/OOD execution while preserving the distinction between technical conditions and biological units. This closes an author-side empirical gap without claiming independent validation.

## Preconditions

- Frozen R3 development protocol, 2,724 development observations and 99 sequence-feature accessions.
- CC0 source assets under `data/raw/r4_candidate_pxd068107/`.
- PMC12808129, PRIDE PXD068107 and BioStudies source-data locators.

## Non-goals

- Do not treat 21 technical rows or the paper-reported 193 patients as 21/193 independent biological units.
- Do not merge PXD068107 into R3 training or use it for target/model selection.
- Do not create a non-author lockbox, no-author reproduction, adoption or DOI receipt.

## Interfaces and invariants

- `biointerfaceos data audit-r4-pxd068107-source --assets-root data/raw/r4_candidate_pxd068107 --strict`
- `biointerfaceos data verify-r4-pxd068107-source --assets-root data/raw/r4_candidate_pxd068107 --strict`
- `biointerfaceos data evaluate-r4-pxd068107-technical-ood --strict`
- `biointerfaceos data verify-r4-pxd068107-technical-ood --strict`
- Source-local positive ranks only; raw cross-study scale is prohibited.
- Expected 21 technical batches, at least 10 positive proteins per batch, 98 shared frozen-R3 proteins and one biological unit.

## Implementation plan

1. Add the PXD068107 registry, source audit, source-cell ledger and frozen technical-OOD protocol.
2. Add the workflow and CLI commands for strict audit, verification, execution and receipt verification.
3. Execute the source audit and model/OOD workflow; bind all input and output hashes.
4. Add regression tests and update the full-text route ledger with conservative scores and claim boundaries.
5. Preserve the external hard gates and carry the task to the next independent-receipt phase.

## Progress

- [x] 2026-08-14 — Verified six BioStudies assets and their SHA-256 values.
- [x] 2026-08-14 — Audited 2,058 source cells, 1,976 positive cells, 21 batches and 98 shared accessions.
- [x] 2026-08-14 — Executed constant/full-ridge/composition-only models, 2,000-cluster bootstrap, paired ablation and 256-permutation negative control.
- [x] 2026-08-14 — Added CLI and regression tests; targeted tests pass (`3 passed`).
- [ ] 2026-08-14 — Obtain and verify non-author lockbox, no-author reproduction, adoption and DOI read-back receipts.

## Discoveries

- Full sequence ridge mean Spearman is `0.17861446667608047` (95% CI `[0.14194138226828856, 0.21417738108202208]`).
- Composition-only ridge is higher at `0.19994159595004432`; full-minus-composition is `-0.02132712927396384` (95% CI `[-0.03863506341472515, -0.004486292748560039]`).
- Within-development-batch permutation upper-tail p is `0.011673151750972763`.
- The result is useful evidence of technical OOD portability and a model-boundary failure mode, not evidence of donor-level biological generalization.

## Decisions

- Admit PXD068107 as an author-run technical OOD source because its CC0 source data are reproducible and cover 98 frozen targets across 21 conditions.
- Keep biological effective n at one because the executed matrix is condition-level, not a protein-by-patient matrix.
- Keep `scientific_submission_ready=false` until independent receipts and DOI read-back are externally verified.

## Validation

Targeted source/OOD tests: `.venv/Scripts/python.exe -m pytest tests/review_round_4/test_r4_pxd068107_source_audit.py tests/review_round_4/test_r4_pxd068107_technical_ood.py -q` → `3 passed`.

## Failure recovery

The source audit and OOD output directories are fail-closed. If a rerun is required, preserve the existing receipts and use a new temporary output root in tests; never overwrite a receipt or mutate the immutable release inputs.

## Outputs

- `docs/data/R4_T264_PXD068107_SOURCE_REGISTRY.json`
- `docs/data/R4_T264_PXD068107_TECHNICAL_OOD_PROTOCOL.json`
- `src/biointerfaceos/r4_pxd068107_source_audit.py`
- `src/biointerfaceos/r4_pxd068107_technical_ood.py`
- `data/raw/r4_candidate_pxd068107/derived/R4_PXD068107_technical_source_cell_map.csv`
- `reports/review_round_4/pxd068107_source_audit/v1.0.0/`
- `reports/review_round_4/pxd068107_technical_ood/v1.0.0/`
- `docs/review_round_4/R4_T264_PXD068107_PAPER_DATA_EXECUTION_20260814.md`

## Completion note

The author-side paper-data execution is complete and independently hash-verifiable within the repository. The broader publication goal remains active because third-party identity/independence receipts, external adoption and DOI archive read-back are still absent.
