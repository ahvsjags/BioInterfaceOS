# R2 real-model source-expansion requirements

## Gate decision

T122 proves three sources can be traced to real, open spreadsheet cells. It
does not provide a common model target: the released benchmark items are GUV
shrinking rate (`um2/s`), nanoemulsion hydrodynamic mean size (`nm`) and
cellular cargo displacement (unit not stated). Each endpoint has one study,
one laboratory and one declared independent unit. They cannot support a
cross-study model, paired ablation, or external OOD evaluation.

The machine-readable decision is
`reports/review_round_2/real_model_compatibility/v1.1.0/compatibility_decision.json`.
It keeps `model_fitted`, `paired_ablations_run`, `external_ood_evaluated` and
`negative_controls_run` false.

## Required admissible target

Before a model may run, choose exactly one endpoint and unit, then admit at
least three independent studies from three laboratories. Every study must
provide row-level, non-fixture primary observations with a stable source URL,
licence, checksum, worksheet/table locator, and a source-defined independent
unit. The initial preferred target is hydrodynamic particle size in `nm`, but
it is only a candidate and must not be silently substituted for another size
definition or measurement modality.

For each independent unit, record: material identity; nominal and measured
size; measurement method; biological/corona condition; medium and ionic
composition; time; dose/concentration; batch/replicate; outcome value and
unit; missingness; source study; laboratory; and any source-defined negative
control. The data dictionary must state which fields are comparable across all
studies and which are study-specific.

## Freeze before fitting

Freeze the target registry, group split, external OOD cohort, fixed seed list,
full and ablated configurations, comparison metric, calibration procedure,
uncertainty method, multiplicity policy, and negative controls before any
outcome values are inspected by model-selection code. All full/ablated pairs
must use identical groups, rows, preprocessing and seeds. Publish row-level
predictions and group-level overlap/effective-n/calibration/uncertainty
artifacts.

No output from this process becomes independent validation; that remains the
T124 protected-data evaluation performed by an external evaluator.

## Candidate expansion audit (2026-08-12)

The checked source-candidate registry is
`data/empirical/R2_T123_REAL_MODEL_SOURCE_CANDIDATES.json`. It records three
open, checksum-verified raw-table packages from distinct studies/laboratories:
the Plaza-Oliver–Santander-Ortega nanoemulsion record, the Ege University
polystyrene-radiotracer record, and the University of Texas at Dallas
verteporfin-LNP record.

They are *not* an admitted target. The source sheets name respectively a
hydrodynamic mean size, a Z-average hydrodynamic diameter, and a hydrodynamic
size with no stated estimator. Their shared `nm` unit is insufficient to claim
one endpoint. Additional provenance and granularity limits are retained in the
machine-readable decision; no model, ablation, OOD, or independent-validation
claim may draw on this batch.
