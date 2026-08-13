# T182 — R9 public release and DOI handoff

## Objective

Create an immutable `v0.1.3-r9` public release that contains the completed T180/T181 source audit, biological-cohort OOD protocol, reports, and external handoff route. Keep DOI and scientific-submission flags conservative until an archival service and real non-author receipts are independently verified.

## Scope

- update `CITATION.cff`, release-status documentation, and external handoff metadata to the R9 tag;
- version the public asset audit so the receipt hashes the post-T181 tracked tree;
- run the existing strict public-release and targeted R4 audits on the clean tracked release state;
- create a Git tag/GitHub release only after the exact commit and manifest are recorded;
- preserve `doi_status=PENDING_NOT_ARCHIVED`, `independent_validation=false`, `external_scientific_reproduction=false`, and `scientific_submission_ready=false`.

## Non-goals

- no redistribution of untracked raw candidate folders;
- no synthetic evaluator, reproduction, adoption, or DOI receipt;
- no claim that the same-laboratory T181 cohort is an independent validation cohort;
- no promotion of exploratory results to mechanistic or clinical evidence.

## Acceptance checks

1. T180/T181 tracked artifacts resolve from the release commit and their source/report hashes remain unchanged.
2. The versioned strict public-release audit returns `PASS_PUBLIC_RELEASE_AUDIT` and records `scientific_submission_ready=false`.
3. KAUST targeted tests and R4 source/OOD verification pass on the same commit.
4. The GitHub release tag resolves to the recorded commit; DOI metadata remains explicitly pending until an archival receipt exists.
5. The handoff documents point to R9 and continue to require real non-author evaluator, reproduction, and adoption receipts.

## Residual external gates

The following cannot be generated from the author-controlled repository: a protected lockbox receipt from a non-author evaluator, a no-author end-to-end scientific reproduction, two independently verifiable adoption receipts, and an immutable DOI/archive receipt. The goal therefore remains `IN_PROGRESS` after T182 unless those external artifacts arrive and pass audit.
