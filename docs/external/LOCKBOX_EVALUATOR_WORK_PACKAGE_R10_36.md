# Non-author protected lockbox work package — r10.36 handoff

Status: `PREPARED_NO_LOCKBOX_RECEIPT`

This package is for one genuinely non-author evaluator who controls the
row-level input and intermediate outputs. The authors must not receive the
protected rows, row-level predictions, tuning traces or failure-level results
before the one-shot run. Public availability of a source does not remove the
custody requirement: the evaluator must independently reacquire it, freeze its
bytes and keep the working input/output directory private until the aggregate
receipt is archived.

## Fixed software and protocol

Use the scientific candidate `v0.1.3-r10.32` and the T218 protocol. Verify the
tag target and manifest before obtaining evaluator access to the protected
input. Freeze the primary estimand, source-local rank rule, missingness,
measurement-batch clustering, nested selection, ablation and permutation rules
before the run. No author feedback or post-access tuning is allowed.

The evaluator may use an independently acquired public paper/accession route
that is not supplied as a row-level file by the authors, or a genuinely unseen
contributed source. The evaluator must record the source locator, license,
bytes/hash, unit semantics and why the input is protected from the authors.

## One-shot output contract

Return aggregate-only results containing:

- primary source-local rank estimand and cluster-aware interval;
- row, measurement-batch, source/laboratory and resolvable biological-unit counts;
- full versus composition-only paired ablation;
- within-batch permutation null and its predeclared selection policy;
- all model summaries, OOD/held-out summaries and uncertainty intervals;
- complete failure, deviation and negative-run ledger;
- commands, environment/dependency hashes, stdout/stderr and output hashes;
- evaluator identity, institution, COI statement, signed attestation and
  immutable archive locator.

Do not return protected rows, row-level predictions, intermediate model state
or a selectively edited success-only summary. Run the structural preflight only
after the evaluator has produced the signed bundle:

```bash
uv run biointerfaceos data preflight-r4-external-receipts \
  --bundle external_bundle.json \
  --documents-root external_receipts \
  --receipt-out r4_preflight_receipt.json \
  --strict
```

The expected structural result is `STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW`.
It is not an accepted scientific claim until identity, custody, independence,
hashes and conflicts are audited by the editorial gate.
