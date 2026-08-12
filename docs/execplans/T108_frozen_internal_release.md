# T108 Create signed internal frozen release before lockbox

## Objective

Create the internal frozen development release after T103 through T107 have
passed. The release must bind every development artifact, claim matrix,
preregistration/prediction package, data/model configuration, manuscript and
figure hash, and the evaluator-only lockbox access plan.

## Release boundary

- Require a clean working tree and a reproducible implementation commit.
- Verify T103 benchmark, T104 data/model, T105 Paper A, T106 Paper B, and T107
  Paper C pre-lock artifacts.
- Record all schema, fixture, receipt, manifest, claim, model, prediction, and
  figure hashes in the freeze receipt.
- Generate an authorization token only for the evaluator path.
- Keep protected test payloads unread and keep the release evaluator-only.

## Implementation steps

1. Add a versioned pre-lock release schema and fixture.
2. Implement `release freeze-prelock --strict` with clean-tree, hash, claim,
   configuration, prediction, and lockbox-plan gates.
3. Add focused tests for first freeze, byte-stable resume, checksum mutation,
   tampering, dirty-tree rejection, and forbidden lockbox access.
4. Add the CLI command and the strict Make target if required by the task graph.
5. Run the complete offline gate and verify the immutable release.
6. Record the release report and activate T109 only after all gates pass.

## Acceptance criteria

- T103–T107 artifacts are hash-bound and their claims are internally consistent.
- The working tree is clean at freeze time.
- The release is immutable and resumes byte-for-byte.
- No protected result or lockbox payload is accessed.
- The authorization token is evaluator-only and is not used by development code.
- Critical audit failures block the freeze and require a new candidate.

## Fallback

If any hash, claim, configuration, manuscript, or figure changes, create a new
freeze candidate. Do not overwrite the prior release. If a critical audit
fails, keep the release unfrozen and retain the failure report.
