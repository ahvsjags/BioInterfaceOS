# R4-T260 — external-gate handoff status

## Status

`HANDOFF_OPEN_NO_EXTERNAL_RECEIPTS`

T260 supersedes the stale r10.32/r10.36 coordination instructions with an
execution package bound to the next immutable release `v0.1.3-r10.45`. The
package includes a clean-room helper, current lockbox contract, two materially
different adoption tasks and a machine-readable receipt predicate.

## What is executable

- the helper clones the fixed tag into a fresh directory;
- PMC6592156 supplementary bytes are reacquired from the public endpoint and
  checked against the declared SHA-256 before extraction;
- locked dependencies, T249/T258 verification, source audit and paper-attached
  OOD are run with stdout/stderr and output hashes;
- the participant receives an execution bundle but must add identity, COI,
  signed attestation, complete failure ledger and immutable archive locator.

## What is not yet evidence

No non-author evaluator, no-author reproduction team, external user or archive
service has supplied a verified receipt. Templates, author runs, CI, KAUST and
issue comments remain excluded from the external gates.

```text
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```
