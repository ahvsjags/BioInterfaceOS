# T127: Results-blind Paper C protocol or validated results manuscript

## Purpose

Position Paper C as a results-blind registered protocol until a protected
real-data evaluation is carried out by an independent evaluator. Only then may
a separate results version be considered.

## Preconditions

T121 analysis rules and T125 literature scope are available. T123 is blocked
without a compatible target, and T124 has only an external-evaluator readiness
protocol rather than an evaluator receipt from protected observations.

## Non-goals

Do not use historical `paper_c_prelock` fixture results, state that a candidate
expression is a law, write replication/refutation language, manufacture an
evaluator signature, or access protected values.

## Interfaces and invariants

- Protocol outline: `docs/manuscripts/R2_PAPER_C_PROTOCOL_OUTLINE.md`.
- Evaluator protocol: `docs/data/R2_INDEPENDENT_EVALUATION_PROTOCOL.json`.
- Aggregate receipt schema: `schemas/independent_evaluation_receipt.schema.json`.
- Portfolio audit: `python -m biointerfaceos manuscript audit-portfolio --strict`.
- A future result manuscript requires a T124 signed aggregate-only receipt
  tied to a T123-frozen bundle; raw values remain outside the repository.

## Implementation plan

1. Retire historical fixture pre-lock claims from the R2 manuscript scope.
2. Create a registered-protocol outline defining target admission, frozen
   bundle hashes, independence safeguards, aggregate reporting and deviations.
3. Bind it to the R2 protocol figure suite, T123 receipt, T124 readiness
   receipt and verified comparator scope with the portfolio audit.
4. Once T123 passes, freeze the target, model, split, predictions and
   thresholds; hand these to an evaluator outside the author environment.
5. Convert the protocol to a results manuscript only if the evaluator receipt
   and later T128 reproduction meet their respective gates.

## Progress

- [x] 2026-08-12: Created the results-blind C outline, evaluator-receipt
  schema and strict portfolio audit; its current status is explicitly blocked.
- [ ] T123 target admission and frozen real-model bundle.
- [ ] Independent evaluator's signed aggregate-only receipt from protected
  observations.
- [ ] Results-version manuscript and external scientific reproduction.

## Discoveries

The historical fixture lockbox is contract-only. It cannot be substituted for
the independent protected-data evaluator required by T124.

## Decisions

Paper C remains a protocol, not a law-discovery manuscript. Its output states
what must be frozen and what the evaluator must disclose, without pre-filling
or predicting an empirical outcome.

## Validation

- `python -m pytest tests/lockbox/test_independent_evaluation_workflow.py tests/manuscripts/test_manuscript_portfolio_workflow.py -q`
- `python -m biointerfaceos lockbox evaluate-independent --strict`
- `python -m biointerfaceos manuscript audit-portfolio --strict`

The present receipts must remain blocked with `external_evaluator_receipt_verified=false`
and `scientific_submission_ready=false`.

## Failure recovery

If T123 lacks a target or no external evaluator is available, retain the
protocol version and publish no result language. If the evaluator receipt is
malformed or reports a deviation, preserve it and start a new protocol version
rather than changing the frozen original.

## Outputs

Paper C protocol outline, evaluator protocol/schema, portfolio receipt, this
ExecPlan, and only after independent evaluation: a signed aggregate receipt,
claim ledger transition and candidate results manuscript.

## Completion note

The protocol route is ready and audited. T127 remains blocked until the real
external evaluation and later reproduction evidence are available.
