# T125: External literature, comparator and domain-definition evidence

## Purpose

Create a verified, auditable external evidence packet for the two R2 manuscript
targets: one merged real-data benchmark/method manuscript (A+B) and a
results-blind Paper C protocol. Define material, biology, protocol, outcome,
independent unit, evidence locator and OOD group so a later manuscript cannot
borrow terms, units or comparator results without stating the boundary.

## Preconditions

T115 and T120 are complete. T123 remains active and currently blocks real
model claims; T124 remains unavailable because an external evaluator and
protected real observations are not yet supplied.

## Non-goals

This work does not fit a model, create an OOD result, validate a biological
mechanism, replace a real-data gate with citations, or alter the immutable
historical fixture manuscripts.

## Interfaces and invariants

- Command: `python -m biointerfaceos manuscript audit-related-work --strict`.
- Inputs: `docs/literature/R2_EXTERNAL_EVIDENCE.json`,
  `R2_MANUSCRIPT_COMPARATOR_MAP.json`, and `R2_OPERATIONAL_GLOSSARY.md`.
- Every cited source must have a verified HTTPS landing record, peer-reviewed
  status, title/year, and a DOI when a DOI exists.
- The audit requires both R2 manuscript scopes, at least twelve citations,
  eight comparators, and all seven glossary terms for every scope.
- Outputs preserve the statement that historical fixture manuscripts are not
  retroactively cleared and scientific submission readiness is false.

## Implementation plan

1. Search and source-verify reporting standards, ontology/data-integration
   resources, claim-evidence/OOD/reproducibility comparators, corona-prediction
   papers and preregistration precedent.
2. Map every source to a specific A+B or C scope and record the
   non-equivalence boundary that prevents imported evidence or overclaiming.
3. Freeze a glossary that prevents unit/assay/endpoint conflation.
4. Run the strict, immutable audit and regression tests.

## Progress

- [x] Verified external evidence registry, comparator map and glossary.
- [x] Implemented strict citation/scope/comparator/glossary audit and tests.
- [ ] Complete KAUST isolated validation and state transition.

## Discoveries

- Existing protein-corona prediction papers are meaningful domain comparators,
  but their corpora and reported metrics are not R2 data or R2 baselines.
- The current R2 source-locator benchmark has three endpoint/unit groups with
  effective n=1 each; it cannot meet the external-OOD expectation.

## Decisions

- Paper A+B is one future manuscript to avoid duplicated contribution claims.
- Paper C is protocol-only until T124 has a signed, independent evaluator
  receipt based on protected real observations.

## Validation

- Strict audit must reject unknown citations, omitted glossary terms, duplicate
  identifiers and any claim that historical fixtures were retroactively cleared.

## Failure recovery

If a source cannot be verified, remove it from the registry and its manuscript
scope; do not retain a vague or unverified citation. If a required glossary
term is unavailable, keep the relevant manuscript scope technical/protocol
only.

## Outputs

- `docs/literature/R2_EXTERNAL_EVIDENCE.json`
- `docs/literature/R2_MANUSCRIPT_COMPARATOR_MAP.json`
- `docs/literature/R2_OPERATIONAL_GLOSSARY.md`
- `reports/review_round_2/related_work/v1.1.0/`

## Completion note

Pending remote validation.
