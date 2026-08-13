# T136: Fail-closed preflight for external verification receipts

## Purpose

Make the later T124 and T128 handoffs executable without pretending that any
external evaluator, reproducer or editor has acted.  The preflight accepts a
contributor-held directory containing one hashed independent-evaluator receipt,
one external reproduction receipt and one editorial re-review report.

## Invariants

- Every supplied document path is a relative POSIX path below the submitted
  documents root and its SHA-256 must match the bytes read by the command.
  Each submitting role separately declares that it is not an author role; this
  declaration remains subject to later identity audit.
- The evaluator receipt must bind all seven frozen-bundle hashes, include only
  aggregate metrics and affirm no author access, raw protected values or
  post-freeze tuning.
- The reproduction receipt must declare a non-author team, independent checkout
  and environment, source reacquisition/attestation, commands, deviations and
  an aggregate-only result summary.
- The editorial report must declare a non-author reviewer and map every
  `R2-01` through `R2-09` finding to evidence, downgrade or an open blocker;
  its critical count must agree with that matrix.
- The command cannot validate a cryptographic signature or real-world identity.
  It returns only `STRUCTURALLY_COMPLETE_REQUIRES_IDENTITY_AND_SCOPE_AUDIT`,
  never an admission, external-validation result or submission-ready state.

## Interface

```bash
python -m biointerfaceos data preflight-external-verification \
  --bundle /secure/incoming/verification-bundle.json \
  --documents-root /secure/incoming/verification-documents --strict
```

Use `docs/data/R2_EXTERNAL_VERIFICATION_BUNDLE_TEMPLATE.json` only as a blank
starting point.  The expected shapes are defined in
`schemas/external_verification_bundle.schema.json`,
`schemas/external_reproduction_receipt.schema.json` and
`schemas/external_editorial_rereview.schema.json`.  Incoming documents and
protected values remain outside this repository.

## Acceptance evidence

- `src/biointerfaceos/external_verification_intake.py` and the three schemas.
- Regression tests for a synthetic structural bundle and rejection of checksum
  mutation, evaluator raw-value leakage, author-team reproduction and a missing
  R2 finding.
- This execution plan and the non-submittable template.

## Completion note

This is only an implementation prerequisite.  No external role, signature,
real protected observation, scientific reproduction or editorial acceptance is
created by T136; T124 and T128 retain their external gates.
