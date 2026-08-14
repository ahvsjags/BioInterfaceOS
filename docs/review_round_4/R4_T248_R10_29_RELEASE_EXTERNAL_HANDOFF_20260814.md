# R4-T248: r10.29 immutable release and external evidence handoff

Date: 2026-08-14  
Status: `HANDOFF_READY_NO_EXTERNAL_RECEIPTS`  
Release tag: `v0.1.3-r10.29`  
Tag target: `2cecba46a5b51af6f8a00aaeec8a5294dc96313b`  
Source commit: `e414acc9ec15f11b5e069407850327a490280e8b`

## What changed

The current paper-data evidence is now bound to a new public immutable tag.
The overlay manifest is
`release/empirical_candidate_v0.1.3-r10.29/release_manifest.json` with
SHA-256
`4d49bc2ff6be959cd0c09495682b2571e6263f3747d3f879847f4375f11a706a`.
It inherits the audited r10.28 release manifest and records the byte-verified
PMC11328176 article/SI assets, source-cell map, PMC9047655 screening assets,
T246 model script, execution outputs and editorial review files.

The tag contains an external reproduction script that rejects moving branches
and checks the r10.29 manifest hash. The public protocol, receipt template,
release metadata and external handoff records all point to the same tag and
manifest. A deterministic KAUST `git archive` was built at
`/ibex/user/xup0a/BioInterfaceOS-v0.1.3-r10.29.tar.gz` with 103253867 bytes
and SHA-256
`cd2ae04cab071b3ca85a27a04470195a800bd9c27eda4a24145a7288e07b798e`.
The tag and archive are release-integrity anchors, not a DOI receipt.

## External work packages

The handoff is ready for three genuinely independent parties:

1. A non-author lockbox evaluator holds protected held-out/unseen real input and
   returns aggregate results only.
2. A no-author team independently reacquires PMC6592156 and runs the fixed
   accession-to-result route.
3. Two distinct non-author users or institutions install the tag and run
   materially different real tasks.

Each receipt must include identity/institution, role and COI, fixed tag and
manifest hash, input or protected-data attestation, environment/dependency
hashes, commands, output hashes, failures, deviations, signed attestation and
an immutable archive locator. The project must not receive protected row-level
inputs or tuning feedback from the lockbox evaluator.

## Gate state

This release closes the stale-release binding problem but creates no external
receipt. Therefore the following remain false:

```text
independent_validation=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

The internal PMC11328176 route remains technical/source-conditional evidence:
six core facilities processed one common prepared material and must not be
described as six independent biological cohorts.
