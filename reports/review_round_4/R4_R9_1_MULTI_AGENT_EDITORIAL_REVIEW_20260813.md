# R4 R9.1 multi-agent editorial re-review

Date: 2026-08-13

## Editorial conclusion

R9.1 improves release provenance and makes the author-run KAUST verification explicit, but it does not create any independent scientific evidence. The panel decision remains **Major Revision**. The work can be positioned as an auditable methods/software and exploratory benchmark paper; it is not yet a strong-Q1 biological discovery or independent-validation paper.

## Evidence checked

- immutable public tag/release: `v0.1.3-r9.1`;
- strict public asset audit: `bioif-public-release-audit-v1.12.0`, `PASS_PUBLIC_RELEASE_AUDIT`, 2,429 tracked assets;
- KAUST author-run receipt: 32 R3/R4 tests passed, T180 source verifier valid, T181 biological-cohort OOD verifier valid;
- T181 execution: 141 biological units, 705 measurement batches, 666 qualified batches, 34 shared canonical proteins, 17,026 external observations, 3 models;
- model results: full subject-equal Spearman `0.06845` (95% CI `[0.05253, 0.08293]`), composition-only `0.03917`, paired delta `0.02928` (95% CI `[0.02413, 0.03451]`), negative-control upper-tail `p=0.24125`, and full-model MAE/RMSE worse than the constant baseline.

## Conservative panel scores

| Module | Score | Reason |
|---|---:|---|
| Data compatibility and sample basis | 85 | Row-level source audit and 141 biological units are real and traceable; the cohort still has one laboratory anchor and 34 shared proteins. |
| Statistical design | 84 | Estimand, nested development selection, subject-cluster bootstrap and missingness boundary are explicit; informative missingness and selection-aware negative-control sensitivity remain open. |
| Statistical execution and effective n | 72 | Real model execution and effective biological-unit accounting exist; batch qualification excludes 39/705 batches and sensitivity across all exclusions is incomplete. |
| Model, ablation and OOD evidence | 56 | Paired incremental signal is exploratory, but absolute correlation is low, the negative control is non-supportive, and error metrics do not beat the constant baseline. |
| Protected independent lockbox | 4 | Protocol and handoff exist; no real non-author evaluator receipt. |
| No-author external scientific reproduction | 0 | No clean-checkout, independently reacquired-input, signed end-to-end receipt. |
| External user adoption | 0 | No independently verifiable adoption receipt; intake count remains zero. |
| DOI/archive provenance | 25 | Fixed Git tag, release notes, manifest and public asset audit exist; DOI remains `PENDING_NOT_ARCHIVED`. |
| Strict strong-Q1 composite | 30 | External hard gates cannot be offset by internal engineering evidence. |

## What R9.1 changed

R9.1 closed an internal release-consistency issue: the current handoff text no longer calls the public route R8, the README reports the current 32-test KAUST run, and the author-run receipt binds the T180/T181 verification to the R9 tree. These changes improve traceability only. They do not change `independent_validation`, `external_scientific_reproduction`, `community_adopted`, or `scientific_submission_ready`.

## Devil's Advocate blockers

1. A passed asset audit is not scientific validation.
2. A KAUST author-run test is not a no-author reproduction.
3. A complete handoff protocol is not an evaluator receipt.
4. A GitHub release is not an immutable DOI archive.
5. The same-laboratory cohort cannot be described as independent laboratory replication.
6. The full model's small rank correlation and failure to beat the constant baseline do not support a mechanistic or clinical claim.

## Required before a strong-Q1 claim

The remaining gates require real external parties or new scientific data: a non-author protected lockbox evaluator receipt, a no-author end-to-end reproduction receipt, at least two independently verifiable adoption receipts, an immutable DOI/archive receipt, and prespecified sensitivity analyses for excluded batches and informative missingness. Until those artifacts are verified, the project must remain `IN_PROGRESS` with `scientific_submission_ready=false`.
