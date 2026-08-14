# R4-T278 post-T277 multi-agent editorial scorecard

Date: 2026-08-15  
Basis: T273/T274/T275/T277 author-side executions, KAUST cross-environment receipts, and the standing external-gate protocol.  
Decision rule: the arithmetic mean is descriptive only; strong-Q1 readiness is hard-gated by independent evidence.

## Panel scores

| Module | Score / 100 | Panel consensus | Remaining evidence required for 90+ |
|---|---:|---|---|
| Data compatibility and sample foundation | 78 | Four paper-derived source/laboratory anchors, seven frozen common targets, row-level ledgers and 112 technical-replicate groups; donor/biological-unit semantics and redistribution rights remain incomplete for the full route. | At least three independent sources with explicit rights and independently confirmed biological-unit/sample semantics, or a licensed redistributable raw-data package. |
| Statistical analysis design | 92 | Primary estimand, pre-frozen target intersection, laboratory-held-out split, grouped nested selection, cluster bootstrap, missingness/coverage rules and selection-aware null are explicit. | Bind the final manuscript claims and evaluator lockbox inputs to the same frozen protocol. |
| Statistical execution and effective sample | 94 | T277 refit uses 783 raw rows -> 671 pre-model fit units, 112 duplicate groups, 115 batches, four held-out anchors; local and KAUST verify and all 11 artifact hashes agree. | Independent confirmation of sample-unit semantics and a final manuscript/figure/table binding. |
| Models, ablation, OOD and uncertainty | 75 | Real ridge/constant/composition models, four-fold held-out metrics, paired ablation, 2,000-cluster bootstrap and 256 selection-aware null permutations execute successfully. The incremental sequence effect is 0 in all four T277 folds. | A pre-specified external OOD/lockbox result with raw-input provenance and uncertainty, preferably from a source not used to construct the common-target panel. |
| Independent non-author lockbox | 0 | Protocol and handoff package exist; no signed non-author evaluator receipt exists. | One evaluator-controlled receipt with input hash, frozen version, environment, output hash and signature/timestamp. |
| No-author scientific reproduction | 0 | Clean-room instructions exist; no independent team has executed from raw-input reacquisition through result. | One end-to-end reproduction report from a team with no author execution assistance. |
| External user adoption | 0 | Public branch and install scripts exist; no independently verifiable external install/use record, issue/PR or citation exists. | At least two external teams/users with reproducible install/run receipts and public or signed records. |
| DOI and version citability | 10 | Release metadata and an archive build receipt exist; the current metadata still has `doi_archived=false`, so no authenticated DOI read-back is available. | Deposit the exact release, read it back through the DOI/API, and verify version/manifest/source checksums. |

Descriptive arithmetic mean: **43.6/100**. The current decision remains **Major Revision / not strong-Q1 submission-ready** because the three external evidence gates are still zero and DOI authentication is open.

## What T277 genuinely adds

T277 closes the previously open author-side technical-replicate refit. The collapse happens before the laboratory split, nested alpha selection, fit and negative-control permutation. The four held-out full-ridge Spearman values are 0.9262, 0.6920, 0.6845 and 0.7662; the selection-aware null upper-tail P-values are 0.0117, 0.0623, 0.0272 and 0.0195. The paired full-minus-composition Spearman effect is exactly 0.0000 in every fold.

These are real quantitative values extracted from published full-text or supplementary materials, but they remain author-side paper-data evidence. They must not be described as a non-author lockbox, independent scientific replication, donor-level effective n, or community adoption.

## Hard-gate checklist

- [x] Frozen protocol and row-level provenance.
- [x] Biological-unit/coverage/technical-replicate handling executed.
- [x] Nested, held-out, cluster-aware model execution and selection-aware null.
- [x] Local/KAUST cross-environment byte identity.
- [ ] Non-author protected lockbox receipt.
- [ ] No-author raw-input scientific reproduction.
- [ ] Two independent external adoption records.
- [ ] Authenticated DOI read-back.
- [ ] Final multi-agent review after all external gates close.

`scientific_submission_ready` remains `false`.
