# R4-T254: full-text paper-derived evidence status — 2026-08-14

## Decision

The no-new-wet-lab fallback is now organized as a stratified evidence package.
The defensible paper position remains:

> BioInterfaceOS is an author-run, paper-derived, source-conditional benchmark
> for protein-corona rank portability with auditable provenance, fold-local
> availability rules and explicit failure boundaries.

This is not a claim of four independent biological cohorts, donor-level
generalization, universal sequence-feature superiority, or external validation.

## What the full-text route actually adds

The package records ten source lineages or screening candidates. The primary
T238 route uses four public source maps and has 115 measurement batches, 3,844
fold-expanded ledger rows, 3,061 development observations and 783 held-out
test-only observations. Target membership is selected within each outer fold
from development sources only; nested alpha selection is rerun in the finite
permutation null.

The additional paper-derived routes remain separate strata:

| Route | Evidence role | Result/boundary |
|---|---|---|
| T238 | primary availability-aware four-source analysis | 4 held-out source folds; exploratory rank portability |
| T246 / PMC11328176 | multicore technical sensitivity | 6 core anchors, one common material; not six biological cohorts |
| T177 / PMC13106918 | technical OOD | one pooled material, 16 eligible batches; heterogeneous/weak signal |
| T203 / PMC10257194 | analysis-only paper OOD | 45 paper-attached subject columns; not in public release |
| T209 / PMC13212878 | analysis-only paper OOD | 60 paper-anchored patient clusters, negative sequence increment; not in public release |
| T184 / PMC3252235 | source screen | two frozen-target overlaps; no model admission |
| PMC9047655 | source screen/biological context | no donor-by-protein target matrix in public supporting files |

The package preserves negative and exclusion results. It does not use a new
paper to change the target threshold or to rescue a failed route after seeing
its outcome.

The current conservative R4-T239 panel snapshot remains 82/88/77/75 for the
four internal scientific modules and 12/8/46/25 for the four external modules;
the descriptive overall mean is 51.6 and the decision is `MAJOR_REVISION`.
T254 records the evidence needed for a future reassessment; it does not
pre-award a 90-point score.

## Submission consequence

The internal data/statistical/model evidence is now auditable as a methods,
benchmark or provenance resource. The hard external predicates remain
unverified: a protected non-author lockbox receipt, a no-author reproduction,
two real non-author adoption receipts, and authenticated DOI/archive read-back.
The final flag therefore remains `scientific_submission_ready=false`.

## Primary artifacts

- [T254 evidence package](../data/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_PACKAGE_20260814.json)
- [T238 protocol](../data/R4_T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_PROTOCOL.json)
- [T238 execution report](../../reports/review_round_4/t238_four_source_availability_execution/v1.0.0/t238_four_source_availability_execution_report.json)
- [T246 technical screen](../data/R4_T246_PMC11328176_MULTICORE_SCREEN_20260814.json)
- [T177 technical OOD protocol](../data/R4_T177_PMC13106918_TECHNICAL_OOD_PROTOCOL.json)
- [T253 editorial review](R4_T253_MULTI_AGENT_EDITORIAL_REVIEW_20260814.md)
