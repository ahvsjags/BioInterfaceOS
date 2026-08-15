# R4-T289 full-objective completion audit — 2026-08-15

## Decision

**INCOMPLETE — external evidence gates remain open.** The author-controlled
paper-data fallback is executable and release-bound, but the project is not a
strong-Q1 submission-ready biological validation study.

## Requirement-by-requirement audit

| Requirement | Current authoritative evidence | Status |
|---|---|---|
| Redistributable, row-traceable common target across at least three laboratory anchors | T192/T195 registry; T282 report: 3 laboratory anchors, 9 frozen targets, 809 raw observations, 644 pre-model observations, 85 batches | **Author-side condition met with declared pooled/donor-ID caveats** |
| Pre-registered study-held-out/nested/cluster-aware execution | T282 protocol, receipt and local/KAUST parity; 3 outer laboratory-held-out folds, nested selection and cluster uncertainty | **Met author-side** |
| Real models, paired ablation, negative control, OOD and uncertainty | T282 predictions/model metrics/ablation/permutation; T284 nine route-level OOD rows with 3 positive, 3 negative and 3 near-zero effects | **Met author-side; external independence absent** |
| Non-author protected lockbox evaluation | T286 handoff and receipt template only; `verified_lockbox_receipt_count=0` | **Missing** |
| No-author raw-input-to-result reproduction | T287 KAUST clean-room path check explicitly marked author-controlled; `verified_no_author_reproduction_count=0` | **Missing** |
| Public repository and fixed version | Public repository, immutable `v0.1.3-r10.57`, tag target `3557fac2019e57fd8968cdcf55b106750eafa750` | **Met** |
| Version DOI with exact archive read-back | KAUST archive and sidecar verified; DOI metadata prepared; `doi_archived=false` and no immutable DOI locator | **Missing** |
| Independent installation and external users/adoption | Runner and issue form are public; no verified non-author adoption receipts | **Missing** |
| Final multi-agent editorial review | T285 five-role evidence-bound review: Major Revision; no post-receipt final PASS review exists | **Missing** |
| Strong-Q1 hard gate | Current state in T286 protocol: all external counters zero and `scientific_submission_ready=false` | **Not met** |

## Current score evidence

The latest evidence-bound panel score is T285: data compatibility 92,
statistical design 92, statistical execution 94, models/OOD/uncertainty 88,
independent lockbox 0, no-author reproduction 0, external adoption 0 and DOI
citation 10. Descriptive mean is 45.75; hard gates dominate and are not
averaged away.

## Required state transition

The final PASS review may only be opened after all of the following are
independently archived and audited:

1. one protected-input lockbox receipt from a non-author evaluator;
2. one no-author accession-to-result receipt;
3. two distinct non-author installation/use receipts;
4. an authenticated DOI/archive read-back binding the exact tag, manifest and
   archive bytes; and
5. a new multi-agent editorial review that rechecks the manuscript claims,
   figures and tables against those receipts.

Until then, the only supported positioning is an auditable computational-
biology methods/resource paper with exploratory, source-conditional
paper-derived portability evidence.
