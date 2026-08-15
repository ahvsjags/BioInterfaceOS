# BioInterfaceOS R4-T286 current external evidence handoff

This is the current public coordination request for the BioInterfaceOS scientific candidate. It is not a receipt. Public paper-data analyses, author-run KAUST jobs, agent reviews, downloads, stars and issue comments do not close any external gate.

## Immutable candidate

Use only the immutable tag below. Resolve the dereferenced tag target and record it in the receipt before running:

```text
repository=https://github.com/ahvsjags/BioInterfaceOS.git
tag=v0.1.3-r10.57
manifest=release/empirical_candidate_v0.1.3-r10.57/release_manifest.json
helper=scripts/r4_external_reproduction_r10_57.sh
```

The reproducible public route is the frozen T250 four-source common-target execution. It is a source-conditional portability benchmark with explicit technical-replicate, pooled-material and donor-ID limitations; it is not a claim of four independent biological cohorts.

## Requested contributions

1. One non-author protected lockbox evaluator using evaluator-controlled protected input and returning aggregate-only results.
2. One no-author team reacquiring the public source files independently and executing from raw input to result in a fresh environment.
3. Two distinct non-author users or institutions installing the fixed tag and running materially different real tasks.

Role-specific work packages:

- `docs/data/R4_T286_LOCKBOX_WORK_PACKAGE_20260815.json`
- `docs/data/R4_T286_EXTERNAL_USER_ADOPTION_INTAKE_20260815.json`

The clean-room reproduction command is:

```bash
bash scripts/r4_external_reproduction_r10_57.sh /absolute/path/to/fresh-run-directory
```

For adoption, the two tasks should be materially distinct, such as the public-data reproduction route and the provenance/endpoint/license audit. Each user must preserve failures, limitations, environment/dependency hashes, commands, outputs and a signed receipt.

## Protected lockbox rules

The evaluator controls the protected input. Authors must not see row-level input, intermediate predictions, tuning traces or failure-level results before the signed aggregate receipt is finalized. Do not upload protected data, credentials or private human data to the public issue.

## Receipt and gate policy

Every receipt must include identity, affiliation, role, conflict-of-interest statement, fixed tag/commit, protocol and dependency hashes, input provenance or protected-input attestation, environment fingerprint, exact commands, stdout/stderr and output hashes, complete failure/deviation/negative-result records, signed attestation and an immutable archive locator.

After the four real receipts have been produced, use the current r10.57 template and structural preflight:

The scientific run remains bound to immutable tag `v0.1.3-r10.57`. The T286
receipt-preflight overlay is available on coordination branch
`r3-real-data-execution-20260813` at commit `57f3435`; do not replace the
scientific checkout with the moving branch.

```bash
cp docs/data/R4_T286_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE_20260815.json external_receipt_bundle.json
uv run biointerfaceos data preflight-r4-t286-external-receipts \
  --bundle external_receipt_bundle.json \
  --documents-root external_receipts \
  --receipt-out r4_t286_preflight_receipt.json \
  --strict
```

This command checks byte identity, schema, fixed-release binding and declared safeguards only. It deliberately leaves identity, independence, scientific acceptance and `scientific_submission_ready` false until editorial verification of the actual external participants and immutable archive records.

The project will keep the following false until real evidence is independently audited:

```text
verified_lockbox_receipt_count=0
verified_no_author_reproduction_count=0
verified_distinct_adoption_receipt_count=0
doi_archive_verified=false
scientific_submission_ready=false
```
