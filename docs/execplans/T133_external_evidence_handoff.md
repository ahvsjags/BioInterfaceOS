# T133: Audited external-evidence handoff package

## Purpose

Turn the remaining R2 data and independence gates into one explicit handoff
contract for a prospective data contributor, protected-data evaluator,
reproduction team and editorial reviewer.  The package is an intake boundary,
not an external result, recruitment action or permission to access data.

## Preconditions

T115, T120, T121, T122 and T125 are complete.  T129 has established that the
current CC0 evidence has zero admissible cross-laboratory numeric-material
targets, so the package must retain `model_use=PROHIBITED`.  T124, T126--T128
remain externally gated.

## Scope and invariants

- The active development cohort is CC0-only.  A CC-BY route is possible only
  after an identified owner explicitly approves the isolated amendment in
  `R2_T129_CCBY_COHORT_AMENDMENT_DECISION.md`; it may not merge with CC0 or
  authorize model fitting by itself.
- Every proposed source must provide the mandatory source and analysis-unit
  fields in `R2_EXTERNAL_EVIDENCE_HANDOFF.json`.  Source labels, paths,
  categorical formulation names and author-specific scales are not inferred
  numeric covariates or shared endpoints.
- Two independent laboratories, one shared preprocessed endpoint and a T121
  amendment are mandatory before a model bundle can be frozen.
- The external evaluator receives only the later frozen bundle and returns a
  signed aggregate-only receipt.  Protected values remain outside this
  repository, and no author may tune after freezing.
- Scientific reproduction and editorial re-review cannot begin before the
  real target, independent evaluation and two protocol routes mature into
  their required evidence packages.

## Implementation

1. Version the machine-readable handoff package with the source-intake fields,
   routing rules, freeze items, external-role safeguards and prohibited actions.
2. Bind it to the current T121, T129, T124, T126/T127, T128, T135/T136, figure
   and public-release receipts using a strict one-shot audit.
3. Publish a read-only report and receipt that state the package is ready for
   intake but that no source, evaluator, reproducer or editor has yet acted.
4. When a contributor supplies a source, run the T135 byte-and-structure
   preflight before source audit.  When independent roles later supply their
   documents, run the T136 verification-bundle preflight before identity,
   signature and scientific-scope audit; neither command accepts a result.

## Validation

```bash
python -m biointerfaceos project audit-r2-external-handoff --strict
python -m pytest tests/review_round_2/test_r2_external_handoff_workflow.py -q
python -m biointerfaceos state validate
```

## Acceptance evidence

- `docs/data/R2_EXTERNAL_EVIDENCE_HANDOFF.json`.
- A checksum-bound report and receipt in
  `reports/review_round_2/external_evidence_handoff/v1.3.0/` that also binds
  the two non-submittable T135/T136 templates.
- Strict tests that reject removed source fields, weakened cohort routing and
  fabricated external-result flags.

## Completion note

The auditable handoff path is complete once the package and its receipt pass.
It does not complete T129, T123--T128, or make any scientific submission
claim; those tasks still require genuine external data and independent actors.
