# R4-T227：r10.27 immutable release 与外部复现入口状态

日期：2026-08-14

## Release binding

- GitHub tag：`v0.1.3-r10.27`
- release commit：`7ac136af2b53fa3f8915ba8c45d00253784a297f`
- source/provenance commit：`f7eb8976f3e2282ed7bf02bfe930c8e886b016a1`
- manifest：`release/empirical_candidate_v0.1.3-r10.27/release_manifest.json`
- manifest SHA-256：`419e1226c0dce92c53a10c32e2ee1aaa97f052f6110f9d2557046cdf90dcf3dc`
- public tarball：`BioInterfaceOS-v0.1.3-r10.27.tar.gz`，94,126,379 bytes
- tarball SHA-256：`dfd86dad04140c1ea6af8b8b918ba25a6662260a72bba843584a276027c35d59`
- GitHub release：[v0.1.3-r10.27](https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.27)

r10.26 remains immutable historical release. r10.27 is the current candidate and includes explicit fresh output roots for the public PMC6592156 source audit and external OOD, reconciliation of an already tracked source-cell map against reacquired input, and a fixed-tag one-command replay script.

## KAUST replay evidence

- Fresh source audit: 30 measurement batches, 13,485 source cells, 9,357 positive source cells.
- Fresh external OOD: 2,724 development observations, 953 external observations, 50 shared canonical proteins, 30 external batches, 3 models.
- The replay was author-run on KAUST and therefore remains `external_scientific_reproduction=false`.
- The earlier r10.26 R3/R4 regression remains `58 passed, 4 skipped`; r10.27 changed only replay plumbing and release metadata after that regression.

## Scientific and external gate state

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

The r10.27 replay path is now operational for a real no-author team, but operation by the author team is not the required receipt.
