# R4-T226：r10.26 immutable release 与 DOI 状态

日期：2026-08-14

## Release binding

- GitHub tag：`v0.1.3-r10.26`
- release commit：`72d331ce8db95073f2b9189a8253b5d67a8acf30`
- source/provenance commit：`90941fad703d972cf5eb75ff7bd979aef8d4df55`
- manifest：`release/empirical_candidate_v0.1.3-r10.26/release_manifest.json`
- manifest SHA-256：`43e38b2de1db9dd2f0f69df07af9598e95dc658cb39603b628e7f0b3ad98d46a`
- public tarball：`BioInterfaceOS-v0.1.3-r10.26.tar.gz`，93,983,017 bytes
- tarball SHA-256：`17e74074f01bdb3852d831ac89b6439591572bd09aa785735c522ee3d397bff1`
- GitHub release：[v0.1.3-r10.26](https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.26)

r10.25 remains an immutable historical release. It was not moved or overwritten. r10.26 contains the corrected dynamic tag/manifest anchor so an external checkout can resolve its actual tag target and compare the manifest source commit and hash without a self-referential hard-coded release commit.

## Verification

- KAUST clean checkout：`/ibex/user/xup0a/BioInterfaceOS-r3-real-data-execution-20260814-clean` fast-forwarded to `72d331c`。
- New T226 preflight/T222 targeted tests：`7 passed`。
- R3/R4 full regression：`58 passed, 4 skipped in 90.92s`。
- The four skips are explicit analysis-only PMC13106918/PMC3252235 asset skips in a clean public checkout; they are not counted as completed external evidence.
- GitHub API reports both r10.26 tarball and SHA-256 sidecar as `uploaded`; the API tarball digest matches the local digest above.

## Scientific and external gate state

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

The public paper-data fallback improves auditable source coverage and author-run execution evidence. It cannot replace a genuinely non-author lockbox evaluator, no-author reproduction, two independent adoption receipts or a DOI/archive receipt.
