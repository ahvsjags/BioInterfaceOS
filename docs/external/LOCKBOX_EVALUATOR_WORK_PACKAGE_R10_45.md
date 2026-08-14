# Non-author protected lockbox work package — r10.45

Status: `PREPARED_NO_LOCKBOX_RECEIPT`

This package is an intake contract for one genuinely non-author evaluator. It
does not assert that an evaluator has run.

## Fixed inputs

- release: `v0.1.3-r10.45`
- repository: `https://github.com/ahvsjags/BioInterfaceOS.git`
- T238 protocol SHA-256: `a89a2cf4236caee0826fddde5ac89747f939dd656636d600595adf9af6bed7ea`
- T249 protocol SHA-256: `53d9aa48c78f3140b8870bb9469b9264f63bd125beb2a9be4c504bef2e341b63`
- T258 protocol SHA-256: `200be8bb0312a155174d7430024644acadf445ae17edc83ebe16d7925ec449b6`

The evaluator freezes the estimand, input custody, unit semantics, missingness,
selection, clustering, ablation and negative-control rules before one-shot
execution. The evaluator must not return protected rows or intermediate state.

## Aggregate-only receipt

The signed receipt must contain:

1. identity, institution, role and conflict-of-interest statement;
2. fixed release/tag/commit and all protocol hashes;
3. protected-input custody statement, source/unit semantics and input digest;
4. environment/dependency digest, commands and stdout/stderr hashes;
5. effective n by target, cluster and source lineage;
6. model, paired-ablation, OOD and uncertainty summaries;
7. permutation/null-control results;
8. complete deviations, failures and negative runs;
9. signed attestation and immutable archive locator.

The receipt is accepted only after independent identity, custody and conflict
review. A structural preflight or template is not acceptance:

```bash
uv run biointerfaceos data preflight-r4-external-receipts \
  --bundle external_bundle.json \
  --documents-root external_receipts \
  --receipt-out r4_preflight_receipt.json \
  --strict
```

The project keeps `scientific_submission_ready=false` until a real receipt
passes the external verification gate and the final editorial panel.
