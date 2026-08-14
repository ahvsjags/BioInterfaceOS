# R4-T283 post-T282 primary paper-data refit and all-module-90 gate

This document records the next improvement target after the T280 route decision and the T281 role-panel review. It uses published full-text/supplementary data where redistribution is permitted, but it does not relabel author-run paper-data execution as external validation.

## Frozen evidence route

| Role | Route | Why it is retained |
|---|---|---|
| Primary manuscript route | T195 three-lab common-target route | 3 laboratory anchors, 9 frozen common targets, row-level provenance, and redistributable CC-BY/CC0 source packages. |
| Biological-unit sensitivity | T265 paper-attached cohort route | Preserves the five-target biological-unit sensitivity while keeping analysis-only licensing boundaries visible. |
| Target-rich sensitivity | T193 pre-frozen target-rich route | Tests whether the primary conclusion depends on the narrow nine-target intersection. |
| Technical-replicate sensitivity | T277 four-source route and T282 T195 refit | Tests pre-split replicate handling without pooling routes or changing the primary estimand. |

The route decision is frozen in `docs/data/R4_T280_PAPER_DATA_PRIMARY_ROUTE_DECISION_20260815.json`. T282 is a refit of the T195 primary route, not a post-hoc replacement of T195 with a favorable dataset.

## T282 executed result

T282 collapses technical replicates before laboratory split, nested selection, fitting, negative-control permutation and uncertainty estimation. The canonical run was completed both locally and on KAUST.

| Quantity | Result |
|---|---:|
| Raw observations | 809 |
| Pre-model collapsed observations | 644 |
| Technical-replicate groups collapsed | 165 |
| Laboratory anchors | 3 |
| Frozen common targets | 9 |
| Measurement batches | 85 |
| Model families | 3 |
| Outer folds | 3 |
| Selection-aware null permutations | 2,000 per outer fold |

Outer held-out full-ridge mean batch Spearman:

| Held-out laboratory | Spearman | 95% cluster-bootstrap interval | Paired full-minus-composition |
|---|---:|---:|---:|
| Dalian University of Technology | 0.8302 | [0.7770, 0.8750] | 0.0000 |
| University College Dublin / Conway Institute | 0.2534 | [0.2121, 0.2920] | 0.0000 |
| University of Edinburgh-led study | 0.4081 | [0.3619, 0.4536] | 0.0000 |

Selection-aware negative-control upper-tail P-values are 0.0039, 0.2685 and 0.0623 for the same folds. These results support a cautious source-conditional portability statement; they do not establish universal biological superiority or sequence-feature utility.

The T282 source accounting keeps biological-unit limits explicit: Dalian is pooled/unspecified, Edinburgh donor IDs are not encoded in the current map, and UCD technical replicate columns are collapsed rather than treated as independent units.

## Cross-environment verification

- Local T282 targeted test: `1 passed`.
- KAUST T282 targeted test: `1 passed in 325.84s`.
- KAUST strict execute: `R4_T282_T195_REPLICATE_AWARE_REFIT_VALID`.
- KAUST strict verify: `R4_T282_T195_REPLICATE_AWARE_REFIT_VERIFY_VALID`.
- The 11 canonical T282 CSV/JSON artifacts have identical SHA-256 hashes locally and on KAUST.
- T282 receipt: `reports/review_round_4/t282_t195_replicate_aware_refit/v1.0.0/t282_t195_replicate_aware_refit_receipt.json`.
- T282 report: `reports/review_round_4/t282_t195_replicate_aware_refit/v1.0.0/t282_t195_replicate_aware_refit_report.json`.

## Current evidence-bound scorecard

The panel scores are operational scores, not claims of acceptance. The arithmetic mean is descriptive; strong-Q1 readiness remains hard-gated.

| Module | Current score | Status | What is still required for >=90 |
|---|---:|---|---|
| Data compatibility and sample foundation | **92** | strengthened | Independent confirmation of biological-unit semantics and final manuscript-to-ledger binding. |
| Statistical analysis design | **92** | meets target | Independent lockbox execution using the same frozen estimand and selection rules. |
| Statistical execution and effective sample | **94** | meets target | Independent reproduction of denominators, intervals, null and ablation artifacts. |
| Models, ablation, OOD and uncertainty | **86** | below target | Non-author lockbox/OOD result with raw-input provenance; retain zero incremental ablation and negative results. |
| Independent lockbox evaluation | **0** | open hard gate | One genuine evaluator-controlled protected-input receipt. |
| No-author scientific reproduction | **0** | open hard gate | One raw-input reacquisition-to-result receipt from a team with no author execution assistance. |
| External user adoption | **0** | open hard gate | Two distinct external installation/use receipts for real downstream tasks. |
| DOI/version citability | **10** | open | Authenticated DOI/archive read-back with exact release and manifest hash match. |

Descriptive arithmetic mean: **45.5/100**. This low mean is driven by the four still-empty identity/adoption/archive gates and is not repaired by adding more author-side paper-data runs.

## T283 all-module-90 acceptance criteria

T283 remains open until every criterion below is machine-verifiable:

1. `verified_lockbox_receipt_count >= 1`, with evaluator identity, conflict-of-interest declaration, protected-input hash, immutable release, environment, command, output hash and signature/timestamp.
2. `verified_no_author_reproduction_count >= 1`, with fresh environment, raw public-input acquisition log, input/output hashes, failures, deviations and no-author attestation.
3. `verified_distinct_adoption_receipt_count >= 2`, from distinct external users or institutions and real downstream tasks, not stars, downloads or template runs.
4. `doi_archive_verified == true`, including DOI/API read-back, immutable record, release tag, archive bytes and manifest equality.
5. The final manuscript, figures, tables and claims bind to T195/T282 artifacts without route switching or selective fold reporting.
6. A final five-role editorial review returns PASS only after criteria 1-5 are verified.

Until then, `scientific_submission_ready` must remain `false` and the editorial decision remains **Major Revision / not yet strong-Q1 submission-ready**. The paper may be positioned as an auditable methods/resource study with exploratory published-data evidence, not as an independently validated biological predictor.
