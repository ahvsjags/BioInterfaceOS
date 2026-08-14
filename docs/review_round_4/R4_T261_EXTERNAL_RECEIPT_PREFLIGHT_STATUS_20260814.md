# R4-T261 — current external receipt preflight

## Purpose

The historical R4 preflight remains frozen to r10.32 for old handoff
compatibility. T261 adds a versioned preflight for receipts submitted against
the immutable scientific candidate `v0.1.3-r10.45`.

## Boundary

The T261 command checks schema, hashes, declared non-author roles, protected
input safeguards, failure/deviation records, aggregate-only results and the
r10.45 tag/protocol anchor. It returns
`STRUCTURALLY_COMPLETE_T260_PENDING_IDENTITY_REVIEW`; it does not authenticate
real-world identity, prove independence or set `scientific_submission_ready`.

## Public tooling

The implementation is published in the v0.1.3-r10.46 tooling overlay:

```text
biointerfaceos data preflight-r4-t260-external-receipts --strict
```

The scientific candidate remains r10.45 so the receipt cannot silently change
the endpoint or model after an evaluator receives protected input.
