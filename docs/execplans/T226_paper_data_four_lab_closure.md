# T226: paper-data fourth-source and four-lab execution closure

## Purpose

Replace unavailable wet-lab acquisition with a fully traceable public-paper route and use it to close the internal empirical execution layer. The route must remain a development/exploratory source-compatibility analysis and must not be presented as donor-resolved biological validation.

## Preconditions

- T192 three-source registry and source maps are frozen.
- PMC6592156 full text, PXD007648 metadata and supplementary workbook are locally retained.
- Source license is documented as CC-BY-3.0; raw scale pooling remains prohibited.
- Release-fixed UniProt sequence features are available for the seven-source intersection.

## Non-goals

- No synthetic or imputed measurements.
- No claim that pH/temperature batches are independent donors.
- No replacement of non-author lockbox, no-author reproduction, external adoption or DOI evidence with author-run analysis.

## Interfaces and invariants

- T249 freezes the exact intersection of four source maps: seven canonical accessions.
- Every output row retains source asset, worksheet/row/coordinate, source identifier, measurement batch and author value state.
- T250 uses leave-one-laboratory-anchor-out folds, within-development measurement-batch nested selection, batch-cluster bootstrap and within-batch permutation negative controls.
- `scientific_submission_ready` remains `false` until all external hard gates are independently evidenced.

## Implementation plan

1. Admit PMC6592156/PXD007648 as a byte-verified fourth source and normalize its public supplementary map.
2. Freeze the four-source target intersection and write T249 ledger/report/receipt.
3. Execute T250 with the release-fixed sequence feature table and write model, prediction, ablation, uncertainty and negative-control artifacts.
4. Run targeted and full repository checks.
5. Bind the artifacts to the current release overlay and KAUST clean-checkout replay.
6. Preserve the external handoff and recruit genuine non-author evidence for the remaining hard gates.

## Progress

- [x] 2026-08-14 — PMC6592156 supplementary data normalized to 13,485 source cells with 9,357 positive rank-eligible cells.
- [x] 2026-08-14 — T249 verified 4 source/laboratory anchors, 7 common targets and 783 common observations.
- [x] 2026-08-14 — T250 verified 783 observations, 115 measurement batches, 4 outer folds and 3 fitted models.
- [x] 2026-08-14 — Full local check: Ruff passed, format check passed, mypy passed, 583 tests passed and 5 skipped.
- [ ] Genuine non-author lockbox, no-author reproduction, two adoption receipts and DOI authenticated read-back.

## Discoveries

- PXD007648 exposes a compact supplementary `pH.peptides.csv` and paper supplementary LFQ workbook; the supplementary table is substantially more usable for audit than raw mzML/RAW files alone.
- The fourth source intersects the current nine-target T192 set at seven accessions, so adding it improves source compatibility while reducing the common universe honestly.
- Dalian has only six held-out measurement batches; its high outer Spearman is a low-cluster-count result and is not evidence of stable biological generalization.

## Decisions

- Use source-local ranks only; never compare raw abundance scales across studies.
- Count laboratory/source anchors for portability folds, but report donor independence separately and conservatively.
- Keep T249/T250 exploratory even though internal execution modules exceed 90; external receipt gates remain separate.

## Validation

```text
python -m biointerfaceos data verify-r4-t249-four-lab-common-target --strict
python -m biointerfaceos data verify-r4-t250-four-lab-common-target --strict
python -m pytest tests/review_round_4/test_r4_t249_four_lab_common_target.py tests/review_round_4/test_r4_t250_four_lab_common_target_execution.py -q
```

Expected: T249 `sources=4 laboratories=4 common_targets=7 common_rows=783`; T250 `observations=783 targets=7 laboratories=4 measurement_batches=115 models=3`.

## Failure recovery

- Do not overwrite the immutable T192 release.
- If a source-map or registry hash changes, delete only the fresh T249/T250 output directory and rerun from the frozen protocol.
- If external evidence is absent, leave all external flags false and do not generate surrogate receipts.

## Outputs

- `docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_PROTOCOL.json`
- `docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_REGISTRY.json`
- `docs/data/R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_PROTOCOL.json`
- `docs/data/R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_REGISTRY.json`
- `reports/review_round_4/four_lab_common_target/v1.0.0/`
- `reports/review_round_4/t250_four_lab_common_target_execution/v1.0.0/`
- `docs/review_round_4/R4_T251_MULTI_AGENT_EDITORIAL_REVIEW_20260814.md`

## Completion note

The unavailable wet-lab input is now replaced by real, public, paper-derived proteomics evidence with immutable source-cell lineage and reproducible model execution. This closes the internal data/model gap but not the independent external evidence gates required for a strong-Q1 submission-ready decision.
