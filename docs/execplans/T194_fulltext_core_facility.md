# T194 — Full-text empirical evidence expansion

## Objective

Convert the openly licensed full-text quantitative asset from PMC9633814 into a
reproducible, row-traceable, leakage-controlled technical-domain evaluation of
BioInterfaceOS. This target addresses the current shortage of executable
paper-attached measurements without claiming that technical replicates are
independent biological cohorts.

## Frozen evidence boundary

- Source: `10.1038/s41467-022-34438-8`, PMC9633814, CC-BY-4.0.
- Asset: `R3_PMC9633814_semiquantitative_source_cell_map.csv`.
- Source map: 9,909 rows; 12 quantitative core-facility domains.
- Biological semantics: one common pooled human-plasma aliquot, processed in
  technical triplicate at each core; biological-unit count is one.
- Target universe: the pre-existing 99-accession R3 ledger, selected before
  T194 execution and never reselected inside an outer fold.
- Missingness: average only numeric positive author replicates; retain a target
  row when at least one replicate is numeric; exclude rows with no numeric
  replicate.

## Execution contract

Each core facility is held out once. Within every outer fold, ridge alpha is
selected by leave-core-out nested selection on development cores only. The
primary model, composition-only ablation, constant baseline, core-cluster
bootstrap interval and within-development-core rank-permutation negative
control are all emitted as immutable artifacts. Cross-core numeric scale
calibration is prohibited.

## Acceptance

The T194 gate is satisfied only when both commands pass and the receipt remains
explicitly non-submission-ready:

```text
python -m biointerfaceos data evaluate-r4-t194-fulltext-core-facility --strict
python -m biointerfaceos data verify-r4-t194-fulltext-core-facility --strict
```

Recorded execution: 707 target observations, 99 target accessions, 12 outer
folds, 3 models, 2,000 core-cluster bootstrap resamples and 500 permutations
per outer fold. The full model's core-cluster bootstrap Spearman interval is
0.383–0.478. These values support exploratory technical portability only.

## Remaining hard gates

T194 does not clear the independent evaluator, no-author scientific
reproduction, external adoption, DOI, independent biological validation or
`scientific_submission_ready` gates. Those require real third-party receipts
and cannot be manufactured from an author-run analysis.
