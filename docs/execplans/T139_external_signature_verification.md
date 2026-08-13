# T139: Trusted-key verification for external R2 records

## Purpose

Upgrade T136's byte-and-structure preflight to verify detached OpenPGP
signatures for the independent-evaluator, external-reproduction and editorial
re-review documents.  The verifier is an external handoff safeguard, not a
scientific acceptance mechanism.

## Required inputs held outside the repository

- A T136-preflighted three-document bundle and documents root.
- One detached signature per document and a signature manifest bound to the
  exact bundle SHA-256.
- A scope-owner-approved trust registry with one distinct full primary-key
  fingerprint per role, plus the corresponding public key bytes and SHA-256.
- An empty, controlled output path for the non-accepting receipt.

Templates are `docs/data/R2_EXTERNAL_SIGNATURE_MANIFEST_TEMPLATE.json` and
`docs/data/R2_EXTERNAL_TRUSTED_SIGNER_REGISTRY_TEMPLATE.json`.  They are not
submissions and contain no trusted key.

## Interface

```bash
python -m biointerfaceos data verify-external-verification-signatures \
  --bundle /secure/incoming/verification-bundle.json \
  --documents-root /secure/incoming/documents \
  --signature-manifest /secure/incoming/signature-manifest.json \
  --signatures-root /secure/incoming/signatures \
  --trusted-signer-registry /secure/trust/signers.json \
  --trusted-keys-root /secure/trust/public-keys \
  --receipt-out /secure/audit/signature-verification-receipt.json --strict
```

## Invariants

- The existing T136 structural preflight must pass first.
- The manifest binds exact bundle bytes; every detached signature is checked
  against its exact receipt bytes.
- Only public keys whose bytes, SHA-256 and full primary fingerprints match an
  independent trust registry are imported into a temporary keyring.  No default
  keyring, keyserver, network fetch or signing operation is used.
- Evaluator, reproducer and editor roles require three distinct registered
  keys.  The receipt's declared fingerprint must match the registered key.
- A successful result is only
  `CRYPTOGRAPHIC_SIGNATURES_VERIFIED_REQUIRES_IDENTITY_SCOPE_AND_SCIENTIFIC_AUDIT`.
  It does not authenticate a person, establish independence or authority,
  accept a scientific claim, clear a T124/T128 gate, or make the project ready
  for submission.

## Validation

- Regression tests generate three ephemeral OpenPGP test keys, sign each
  document, verify the resulting receipt and reject a signature swap, key-role
  reuse and an existing receipt path.
- KAUST runs the production verifier with GnuPG; no real external identity,
  source data or protected observation is created by the test.
