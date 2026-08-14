# R4-T240: External receipt fixed-release binding audit

Date: 2026-08-14  
Status: `STRUCTURAL_RELEASE_BINDING_HARDENED_EXTERNAL_GATES_STILL_OPEN`

## Finding

The external receipt preflight already checked the repository, tag, manifest path, and field shapes. Before this task, however, a submitted bundle could provide arbitrary values for the tag target commit, the release-manifest `source_commit`, and the manifest SHA-256. When no repository root was supplied, the bundle could therefore claim a different immutable release while still passing the structural field checks.

That was a provenance-integrity defect in the handoff contract. It did not create scientific evidence, but it could have weakened the identity boundary around a future external receipt.

## Remediation

`R4ExternalReceiptPreflightWorkflow.FIXED_RELEASE` now binds all release identity fields to the audited r10.28 values:

```text
repository:      https://github.com/ahvsjags/BioInterfaceOS
tag:             v0.1.3-r10.28
tag target:      5f72487023f80dd37d6b550b97638fb0246eb3fa
source_commit:   b676433
manifest path:   release/empirical_candidate_v0.1.3-r10.28/release_manifest.json
manifest SHA256: 4e35d6cbe8343e13419a28aca97b526e0e91c17ab297d1f6c33df6866bb7b6f4
```

The preflight now rejects incomplete or unexpected fixed-release fields and rejects drift in the release commit, source commit, or manifest digest. The receipt template contains these same anchors to reduce transcription errors, but remains explicitly `TEMPLATE_NOT_EVIDENCE`.

## Verification

- Targeted preflight tests: `7 passed`.
- Review-round-4 regression: `55 passed`.
- Combined review-round-3 and review-round-4 regression: `64 passed`.
- `git diff --check`: passed.

## Claim boundary

This task creates no evaluator receipt, no no-author reproduction receipt, no external adoption receipt, and no DOI archive. It only makes future receipt identity checks stricter. The external gates therefore remain false and `scientific_submission_ready` remains false until independently supplied artifacts pass the existing verification protocol.

## Reproducibility anchors

- Release tag: `v0.1.3-r10.28`
- Release tag target: `5f72487023f80dd37d6b550b97638fb0246eb3fa`
- Release manifest SHA-256: `4e35d6cbe8343e13419a28aca97b526e0e91c17ab297d1f6c33df6866bb7b6f4`
- Release manifest source commit: `b676433`
- Protocol: `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json`

