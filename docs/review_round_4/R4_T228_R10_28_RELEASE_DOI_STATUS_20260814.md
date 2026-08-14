# R4-T228：r10.28 immutable release 与 clean replay 状态

日期：2026-08-14

## Release binding

- GitHub tag：`v0.1.3-r10.28`
- release commit：`5f72487023f80dd37d6b550b97638fb0246eb3fa`
- source/provenance commit：`b676433d85837e78c5502c0e75012ae2275c4992`
- manifest：`release/empirical_candidate_v0.1.3-r10.28/release_manifest.json`
- manifest SHA-256：`4e35d6cbe8343e13419a28aca97b526e0e91c17ab297d1f6c33df6866bb7b6f4`
- public tarball：`BioInterfaceOS-v0.1.3-r10.28.tar.gz`，94,265,141 bytes
- tarball SHA-256：`f83388c9f7ec67e55aa941871867e20b3f69ed81e5f7a9cbee04accf7885e5a0`
- GitHub release：[v0.1.3-r10.28](https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.28)

r10.27 remains immutable historical release. r10.28 is the current candidate and adds explicit clean-public-checkout skip gates for analysis-only T214/T217 reports while retaining the fresh-output external replay path.

## Clean-tag replay evidence

In `/ibex/user/xup0a/BioInterfaceOS-r10.28-clean-replay-20260814`, cloned from the immutable tag:

- full R3/R4 suite：`49 passed, 13 skipped in 92.69s`；无失败。
- skips are explicit for analysis-only Manchester, PMC13106918, PMC3252235, T214 and T217 assets excluded from the public release.
- fresh source audit：30 measurement batches, 13,485 source cells, 9,357 positive source cells.
- fresh external OOD：2,724 development observations, 953 external observations, 50 shared canonical proteins, 30 external batches and 3 models.
- the one-command script completed lockfile check, output hashing and conservative gate reporting.

This replay was executed by the project team on KAUST and therefore is not a non-author scientific reproduction receipt.

## Scientific and external gate state

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

The fixed public engineering route is now ready for a real non-author team. External identity, scope and signed receipt evidence remain outstanding.
