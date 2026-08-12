# T113 Run manuscript claim-to-evidence and language audit

## Objective

Audit every manuscript quantitative/scientific sentence against its claim and
evidence ledgers, the frozen Paper A/B/C manifests, T110 sealed claim
transitions, and T112 public-package boundaries. Produce a FINAL_CLAIM_AUDIT
and revised manuscript copies only where the audit requires wording or evidence
scope changes.

## Audit gates

- Every quantitative/scientific sentence has a claim ID and evidence path.
- Paper C C1-C5 wording reflects replicated/refuted/inconclusive outcomes and
  preserves abstentions and failure classes.
- C6 remains association-only; C7 retains OOD/selection applicability limits;
  C8 no longer claims pre-lock status where evaluator metadata is authorized.
- No causal, mechanistic, universal, broad-transfer, or experimental-validation
  wording is introduced without an explicit eligible evidence record.
- Dates, citations, release IDs, source-data licenses, and file hashes resolve.
- The public package contains only the T112 redistributable subset.

## Implementation steps

1. Add a versioned claim-audit schema and fixture for all three manuscripts.
2. Implement `claim audit-manuscripts --strict` with sentence extraction,
   claim/evidence joins, forbidden-language scanning, date/citation checks, and
   public-package boundary validation.
3. Add focused tests for missing claim IDs, orphan evidence, causal wording,
   unsupported experimental validation, stale lockbox statuses, and citation
   date/hash mismatch.
4. Add the CLI command and `make claim-audit` target.
5. Generate FINAL_CLAIM_AUDIT and revised manuscript audit receipts.
6. Record T113 and activate T114 only after critical findings are zero.

## Fallback

Downgrade unsupported wording to association-only, bounded, exploratory,
inconclusive, or refuted language. Do not invent citations, data, experiments,
or numbers. Block submission if a critical claim cannot be linked to evidence.
