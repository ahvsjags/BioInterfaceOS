# GitHub Issue #2 coordination update: T246 paper-data strong-Q1 closure

Date: 2026-08-14  
Repository: `ahvsjags/BioInterfaceOS`  
Fixed public candidate for third parties: `v0.1.3-r10.28`

## What is now available

- Fixed release tag: `v0.1.3-r10.28`
- Fixed tag target: `5f72487023f80dd37d6b550b97638fb0246eb3fa`
- Release manifest SHA-256: `1c939f964b97463dab4c5b0899df1f5deab92a7d8a7257d2a306f14f1f881491`
- Latest post-CI engineering branch commit: `0a3483d4d6860108955765aa7a61807e02bf54d0`
- Latest GitHub CI run: `31784714986`, conclusion `success`
- Latest KAUST verification: `make check` passed, `573 passed, 13 skipped`
- New paper-data goal and panel: `docs/review_round_4/R4_T246_PAPER_DATA_STRONG_Q1_CLOSURE_GOAL_20260814.md`

The paper-data routes now support a bounded technical/source-conditional
portability analysis. They do not claim independent biological validation.

## Participants requested

1. One genuinely non-author evaluator with protected held-out input or an
   unseen real dataset. The authors must not see row-level inputs,
   intermediates or predictions before the evaluator receipt is finalized.
2. One no-author team that starts from the public accession/release and returns
   an accession-to-result reproduction receipt.
3. Two distinct non-author users or institutions that install the fixed release
   in clean environments and run distinct real tasks.

Each receipt must state identity/institution, conflict of interest, fixed tag
and manifest hash, input/download hashes, environment digest, commands,
stdout/stderr or output hashes, deviations/failures and a signed statement.
The existing handoff contract is
`docs/external/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.md`.

## Current gate state

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

Please respond in this issue with role, institution, conflict-of-interest
statement and the intended receipt type before running. Do not upload protected
data or private credentials to the repository.

