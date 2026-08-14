# R4-T252 current external handoff — 2026-08-14

## Status

`HANDOFF_READY_NO_EXTERNAL_RECEIPTS`

The current fixed candidate is `v0.1.3-r10.32`, target commit
`b8331e647d4194b85f68feb6e2d9e30a4f9e0a9d`, with release-manifest SHA-256
`d56a070a974675be2e3cff217c437d451eb765719ee95cc9c836abebf40c0c51`.
The KAUST archive is `BioInterfaceOS-v0.1.3-r10.32.tar.gz` with SHA-256
`69848b75aa143f83df9d69668caad52a1e386bc4a0000d5bf2041561e8d8fd25`.
The public handoff overlay is released at
`https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.38`;
it does not change the scientific candidate.

## Reproducible paper-data route

The release contains a four-source common-target route: four laboratory
anchors, seven exact common canonical accessions, 783 row-traceable
observations, 115 measurement batches, four held-out laboratory folds, three
models, nested selection, batch-cluster uncertainty, paired composition
ablation and within-batch rank-permutation controls. It is development-only
evidence. Technical condition batches and pooled/unspecified plasma units are
not counted as donor-level independent biological cohorts.

The recommended no-author route is the public PMC6592156/PXD007648 source.
The reproducing team must reacquire the public bytes independently, verify its
own hashes, start from the fixed tag, preserve failed/negative runs, and submit
the signed receipt without author assistance or tuning feedback.

## Required independent work packages

1. One non-author evaluator runs a one-shot protected lockbox and returns
   aggregate results only; authors must not see row-level input or intermediate
   results.
2. One non-author team performs accession-to-result reproduction from the fixed
   tag and public source.
3. Two distinct non-author users or institutions install the release and run
   materially different real tasks.
4. An authenticated archive service returns a DOI or immutable record whose
   manifest and archive hashes read back exactly.

Every receipt must include identity, institution, conflict disclosure, fixed
release anchors, environment/dependency hashes, commands, output hashes,
deviations, failures/negative runs, signed attestation and an immutable
archive locator. Templates and author-run runs are not evidence.

## Gate state

```text
independent_validation=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

The public coordination issue remains a request for participants, not a
receipt. The current multi-agent editorial decision therefore remains
`MAJOR_REVISION` until real external artifacts are received and independently
audited.
