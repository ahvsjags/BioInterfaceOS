# GitHub Issue #2 — current r10.32 coordination update

This is a public request for independent work, not evidence that any work has
already occurred.

## Current fixed candidate

- tag: `v0.1.3-r10.32`
- tag target: `b8331e647d4194b85f68feb6e2d9e30a4f9e0a9d`
- manifest: `release/empirical_candidate_v0.1.3-r10.32/release_manifest.json`
- manifest SHA-256: `d56a070a974675be2e3cff217c437d451eb765719ee95cc9c836abebf40c0c51`
- archive SHA-256: `69848b75aa143f83df9d69668caad52a1e386bc4a0000d5bf2041561e8d8fd25`
- external receipt protocol: `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json`
- receipt preflight: `python -m biointerfaceos data preflight-r4-external-receipts --strict`

## Requested participants

1. One non-author evaluator holding protected held-out or unseen real input,
   returning aggregate results only.
2. One non-author team independently reacquiring the public PMC6592156/PXD007648
   route and producing an accession-to-result receipt.
3. Two distinct non-author users or institutions installing the tag and running
   materially different real tasks.

Each receipt must disclose identity, institution, role, conflicts, fixed
release anchors, environment/dependency hashes, commands, output hashes,
deviations, failures/negative runs, signed attestation and an immutable archive
locator. Do not post protected row-level data or credentials in this issue.

The project currently has zero verified receipts. Downloads, stars, page views,
author-controlled runs, Codex/agent runs, templates and simulated receipts do
not count. `scientific_submission_ready` remains false until the receipts and
DOI read-back pass independent audit.
