# R4-T241: Canonical release-manifest hash audit

Date: 2026-08-14  
Status: `CANONICAL_CLEAN_CHECKOUT_HASH_RESTORED`

## Finding

An end-to-end clean-clone check of the public `v0.1.3-r10.28` tag resolved the expected tag target:

```text
5f72487023f80dd37d6b550b97638fb0246eb3fa
```

The release manifest content was unchanged, but the local Windows worktree had a stale CRLF checkout while `.gitattributes` declares LF. The previously recorded `4e35d6...` value was therefore a platform-specific working-tree hash, not the canonical byte hash of the immutable Git blob. A clean clone produced the canonical SHA-256:

```text
1c939f964b97463dab4c5b0899df1f5deab92a7d8a7257d2a306f14f1f881491
```

This would have caused valid external clean checkouts to fail the handoff hash guard.

## Remediation

All current fixed-release consumers now use the canonical LF checkout/blob hash:

- `R4ExternalReceiptPreflightWorkflow.FIXED_RELEASE`;
- `scripts/r4_external_reproduction.sh` on the moving execution branch;
- R4-T218, T234, T235, T239, and T240 JSON/Markdown handoff records;
- DOI preparation metadata.

The preflight repository-anchor check now hashes the manifest bytes resolved from
`git show <tag>:<manifest_path>` rather than platform-normalized working-tree
bytes. This keeps a Windows CRLF checkout from disagreeing with the immutable
LF Git blob.

The immutable r10.28 tag itself was not rewritten. Its existing tag target remains unchanged. The addendum still requires an external participant to perform the clean-checkout, tag-target, and manifest-hash guards before submitting any receipt.

## Verification evidence

- Clean clone exact tag: `v0.1.3-r10.28`.
- Clean clone tag target: `5f72487023f80dd37d6b550b97638fb0246eb3fa`.
- Clean clone manifest SHA-256: `1c939f964b97463dab4c5b0899df1f5deab92a7d8a7257d2a306f14f1f881491`.
- Clean clone manifest `source_commit`: `b676433`.
- Clean clone working tree: clean.
- The clean clone contains the committed PMC6592156 supplementary asset, derived source map, sequence-feature table, and reproduction script.

## Claim boundary

The clean-clone check is an author-side release-integrity check. It is not an external scientific reproduction, lockbox evaluation, adoption receipt, or DOI archive. External gates remain false until independent actors submit verifiable receipts.
