# R4 PXD060795 Dalian source status

Status: `ADMITTED_R4_SMALL_N_INDEPENDENT_SOURCE_PENDING_SENSITIVITY_PROTOCOL`

PXD060795 is a CC0 PRIDE dataset from Dalian University of Technology containing a Proteome Discoverer result workbook for human-plasma corona formed on PLA micro/nanoplastics before and after UV aging. The workbook is byte-verified and mapped only against the frozen R3 sequence-feature table.

The audit found 547 protein rows, 27 direct shared frozen-R3 accessions, and 243 source cells across nine normalized-abundance columns. The three `A_PLA` and three `PLA` corona columns contain 21, 20, 19, 17, 16 and 16 positive shared targets respectively; all six pass the predeclared ten-positive-target threshold. The three `HP` columns are plasma controls and are excluded from the corona batch count. The positive candidate-cell count is 109.

This is useful evidence from a new laboratory anchor and is eligible for a separately frozen small-n sensitivity protocol. It does not satisfy the primary R4 external-OOD minimum of twelve qualifying corona batches, donor-level independence is not reported in the result workbook, and it is not merged with another study by concatenating author abundance scales. No model has been fitted on this source and no submission-readiness claim is made.

The machine-checkable registry is `docs/data/R4_T162_PXD060795_DALIAN_SOURCE_REGISTRY.json`; the audit implementation is `src/biointerfaceos/r4_dalian_plasma_corona_source_audit.py`; and the receipt is under `reports/review_round_4/dalian_plasma_corona_source_audit/v1.0.0/`.

The separately frozen small-n sensitivity run used all 2,724 frozen R3 development observations for fitting and 109 Dalian target observations for scoring. Sequence-ridge full achieved mean batch Spearman 0.2323 (MAE 0.2562; RMSE 0.3118); the composition-only ablation achieved 0.2317, with full-minus-composition 0.0006 and 95% cluster-bootstrap interval [-0.0130, 0.0135]. The within-batch permutation control gave an upper-tail p-value of 0.0929. These results are exploratory and do not support a strong external-generalization claim. The sensitivity protocol and receipt are `docs/data/R4_T163_PXD060795_SENSITIVITY_PROTOCOL.json` and `reports/review_round_4/dalian_plasma_corona_sensitivity/v1.0.0/`.
