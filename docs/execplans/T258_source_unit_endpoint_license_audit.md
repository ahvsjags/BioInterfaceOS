# T258 — Source-unit, endpoint-compatibility and license audit

## Objective

Freeze an auditable accounting layer over the T249 four-source paper-derived
common-target asset. The audit must distinguish laboratory/source provenance,
reported biological units, encoded biological units, technical replicates and
the narrower source-local rank endpoint.

## Acceptance criteria

- Recompute all four source maps from their SHA-256-pinned paths.
- Reconcile 15,971 source rows and 10,852 rank-eligible rows with T249.
- Report encoded biological units without imputing donor identity:
  Edinburgh 0, PMC6592156 0, Dalian 0, UCD 30.
- Record technical replicate semantics: PMC6592156 has three explicit
  replicate labels and UCD has two; neither is treated as independent
  biological n.
- Emit all six pairwise endpoint rows. The source-local rank endpoint is
  conditionally portable after within-source ranking; a pooled calibrated
  biological-effect endpoint is not claimed.
- Record CC-BY/CC0 reuse classes and source locators for all four maps.
- Bind the report, source-unit ledger and endpoint matrix with SHA-256 in a
  receipt and keep `scientific_submission_ready=false`.

## Required commands

```text
biointerfaceos data audit-r4-t258-source-unit-endpoint-license --strict
biointerfaceos data verify-r4-t258-source-unit-endpoint-license --strict
```

## Claim boundary

This is an internal provenance and compatibility audit over public paper data.
It does not create independent donor-level validation, cannot replace a
non-author lockbox evaluator, and does not close no-author reproduction,
external adoption, DOI or submission-ready gates.
