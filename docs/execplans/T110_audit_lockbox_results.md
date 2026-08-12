# T110 Audit lockbox results and update claim statuses

## Objective

Audit the sealed T109 evaluator outputs against the T107 prediction package and
update every claim status without changing thresholds, predictions, or frozen
development analyses.

## Audit boundary

- Verify the T108 release signature and T109 first-run receipt before reading
  aggregate evaluator metadata.
- Map each prediction to exactly one of `REPLICATED`, `REFUTED`, or
  `INCONCLUSIVE`.
- Preserve abstentions, failure classes, unresolved contradictions, and the
  T100/T101 applicability limits.
- Do not tune thresholds, exclude inconvenient cases, or rewrite the T107
  prediction table.

## Implementation steps

1. Add a versioned post-lock audit schema and fixture.
2. Implement `lockbox audit-results --strict` with signature, receipt, claim
   coverage, contamination, threshold immutability, and status-transition gates.
3. Add focused tests for complete mapping, duplicate/missing prediction IDs,
   threshold mutation, receipt tampering, and protected-value contamination.
4. Add the CLI command and `make lockbox-audit` target.
5. Run the full offline gate and generate a sealed claim-transition report.
6. Record T110 and activate T111 only after all transitions are auditable.

## Acceptance criteria

- Five predictions map to five explicit post-lock statuses.
- No threshold or prediction changes occur.
- Replicated, refuted, inconclusive, and abstained cases remain visible.
- Claim transitions cite both pre-lock and sealed post-lock artifacts.
- Contamination scan passes and no protected raw value enters development files.

## Fallback

Downgrade or refute unsupported claims. Preserve inconclusive and abstained
claims as unresolved. Never remove inconvenient evaluator cases or retune a
threshold after seeing the sealed result.
