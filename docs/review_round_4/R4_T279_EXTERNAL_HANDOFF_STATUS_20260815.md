# R4-T279 external handoff status — 2026-08-15

## Scope

T279 converts the remaining strong-Q1 blockers into a fixed-version, independently executable handoff. It does not manufacture the missing third-party evidence. The fixed paper-data candidate is `v0.1.3-r10.56`, tag target `2b5642f480576e70e362a11fcfe4757420e93f80`, with manifest SHA-256 `553febabf2d6595dd52545c6b75035e901c20c8ef07b1cb69df4e332aeb4a56d`.

## What the paper-data route now supports

- four laboratory anchors and seven exact canonical targets;
- 783 row-traceable raw observations, 671 fit observations after pre-model technical-replicate collapsing, 112 collapsed groups and 115 measurement batches;
- biological-unit grouped outer folds, nested selection, cluster-aware uncertainty, paired full-versus-composition ablation and selection-aware within-batch permutation controls;
- byte-checked local/KAUST author-side replay and a complete failure/negative-result boundary.

These are reproducible author-side analyses of redistributable paper/full-text data. They are not an independent biological cohort, a protected lockbox evaluation, a no-author reproduction or community adoption.

## Delivered handoff artifacts

1. `R4_T279_EXTERNAL_GATE_HANDOFF_PROTOCOL_20260815.json` fixes the route, receipt schema and gate predicates.
2. `R4_T279_LOCKBOX_WORK_PACKAGE_20260815.json` specifies evaluator-controlled protected input and aggregate-only return.
3. `R4_T279_EXTERNAL_USER_ADOPTION_INTAKE_20260815.json` requires two distinct non-author real-task records.
4. `R4_T279_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json` provides the receipt bundle shape.
5. `R4_T279_EXTERNAL_EVIDENCE_REQUEST_20260815.md` gives the clean-room and submission instructions.
6. `r4_t279_external_receipt_preflight.py` and `preflight-r4-t279-external-receipts` verify bytes, schema, fixed-release binding and declared safeguards while keeping all acceptance predicates false.

Local and KAUST T279 contract checks: **5 passed**. The full KAUST `tests/review_round_4` suite completed after synchronization; no external claim was promoted by the tests.

## Current editorial score boundary

| Module | Current score | T279 effect |
|---|---:|---|
| Data compatibility and sample foundation | 78 | strengthens fixed paper-data route; still no cross-study biological common target claim |
| Statistical analysis design | 92 | unchanged; already strong |
| Statistical execution and effective sample | 94 | unchanged; T277 results are now replayable |
| Models, ablation, OOD and uncertainty | 75 | unchanged; paper-data results remain exploratory and author-side |
| Non-author lockbox | 0 | no genuine evaluator receipt |
| No-author scientific reproduction | 0 | no genuine no-author receipt |
| External user adoption | 0 | no two identity- and environment-audited users |
| DOI archive read-back | 10 | archive is built, but no authenticated immutable DOI read-back |

The descriptive mean remains **43.6/100** and `scientific_submission_ready=false`. The handoff is operationally ready; the scientific gates are not closed.

## Remaining acceptance conditions

The final gate requires one genuine non-author protected lockbox receipt, one genuine no-author accession-to-result reproduction receipt, two distinct external-user adoption receipts, an authenticated DOI archive with exact manifest/archive read-back, and a final multi-agent editorial review. A template, a GitHub issue, a Codex/KAUST run, an author-side clean-room replay or a paper-derived dataset cannot satisfy those predicates.
