# R4-T295 non-DOI phase acceptance audit — 2026-08-15

## Phase decision

**Author-side implementation and execution: ACCEPTED for this phase.**

The paper-data fallback, frozen statistical execution, T290 tie-aware OOD correction, KAUST replay, external-helper self-test and regression suite are complete. DOI/archive and GitHub immutable-release work is explicitly deferred per the user's latest instruction.

**Strong-Q1 scientific acceptance: NOT YET.** The remaining lockbox, no-author reproduction and external-adoption gates require real people outside author/project control. No author run, internal agent, issue comment or self-test is counted as one of those receipts.

## Completed evidence

| Area | Evidence | Result |
|---|---|---|
| Common-target data foundation | T192/T195/T282 registries and row-level ledgers | 3 laboratory anchors, frozen targets, declared pooled/donor-ID/technical-replicate limitations |
| Nested study-held-out statistics | T282 protocol, report and receipt | laboratory-held-out folds, nested selection and cluster-aware uncertainty |
| Paper-data OOD | T290 protocol/report/receipt | 6 route-native estimands; 3 positive, 2 negative, 1 indeterminate |
| Cross-environment replay | T292 KAUST replay | byte-identical T290 CSV/report/receipt on KAUST |
| External helper readiness | T293/T294 | fresh fixed-tag clone, locked environment, T250 verification and test passed; author-controlled self-test only |
| Regression suite | `pytest -q tests/review_round_4` | **105 passed** in 349.44 s |
| External handoff | T286/T293 handoff and issue form | current fixed-tag instructions, protected-data rules and signed-receipt requirements |

## Evidence-bound scorecard

| Module | Score | Phase status |
|---|---:|---|
| Data compatibility and sample foundation | 92 | accepted author-side |
| Statistical analysis design | 92 | accepted author-side |
| Statistical execution and effective sample | 94 | accepted author-side |
| Models, ablation, OOD and uncertainty | 89 | accepted author-side; below 90 because external independence is absent |
| Non-author protected lockbox | 0 | receipt missing |
| No-author scientific reproduction | 0 | receipt missing |
| External user adoption | 0 | two receipts missing |
| DOI/version citability | deferred | user explicitly postponed |
| GitHub immutable-release refresh | deferred | user explicitly postponed |

## Current hard-gate state

```text
verified_lockbox_receipt_count=0
verified_no_author_reproduction_count=0
verified_distinct_adoption_receipt_count=0
doi_archive_verified=false
scientific_submission_ready=false
```

These values remain false. This phase audit is an acceptance of the completed author-side work, not a strong-Q1 certificate or a waiver of the original objective's independent-evidence requirements.

## Exact remaining action

The next meaningful state change is receipt intake from a genuinely non-author evaluator/team: one protected lockbox receipt, one no-author raw-input reproduction receipt and two distinct external-use receipts. After identity, custody, signatures and immutable archive locators are audited, a new five-role editorial re-review can reassess the scores. DOI and GitHub release work can then be resumed without changing the scientific evidence boundary.

