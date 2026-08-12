# T126: Merged A+B real-data benchmark and method manuscript

## Purpose

Build one non-overlapping A+B manuscript route rather than retain separate
fixture-backed benchmark and method manuscripts. Its eventual contribution is
a real-data provenance, benchmark and model-method manuscript.

## Preconditions

T120--T122 and T125 are complete. T123 currently has no compatible
cross-study target, paired model runs, ablations, declared OOD cohort or
negative-control output. Therefore a results manuscript cannot yet be built.

## Non-goals

Do not reuse `release/manuscripts/paper_a` or `paper_b`, copy their fixture
metrics, or write a biological-prediction, causal-effect, robustness or
external-validation result before T123 passes.

## Interfaces and invariants

- Portfolio: `docs/manuscripts/R2_MANUSCRIPT_PORTFOLIO.json`.
- Outline: `docs/manuscripts/R2_PAPER_AB_PROTOCOL_OUTLINE.md`.
- Audit: `python -m biointerfaceos manuscript audit-portfolio --strict`.
- R2 A+B has exactly one route and must cite
  `R2_PAPER_AB_REAL_BENCHMARK_METHOD` from the verified comparator map.
- Only R2 Figures 1--3 may appear before empirical figures are field-mapped,
  evidence-linked and generated from admitted real-model output.

## Implementation plan

1. Retire historical A and B manuscripts from R2 submission scope and retain
   their immutable audit history.
2. Create one merged protocol outline with source-locator scope, statistical
   boundary, comparator positioning, figures, availability statements and
   transition conditions.
3. Bind the outline to the T119 figure suite, T123 compatibility receipt and
   T125 literature receipt using a strict portfolio audit.
4. After T123 passes, replace the protocol-only sections with raw real-model
   predictions, paired ablations, negative controls and declared OOD results.
5. Keep the manuscript blocked until T128 independently reproduces the scoped
   empirical conclusions and editorial re-review accepts the evidence map.

## Progress

- [x] 2026-08-12: Created the merged A+B protocol outline and a strict audit
  that verifies its related-work scope, protocol figures and withdrawal of all
  legacy fixture figures.
- [ ] Obtain a compatible cross-study target and real paired model outputs
  through T123.
- [ ] Build the complete real-data A+B manuscript, methods, data/code
  statements, figures and tables.
- [ ] Obtain external scientific reproduction and editorial acceptance through
  T128.

## Discoveries

T122's raw-cell locator result is suitable only for provenance/benchmark
workflow description. T123's current receipt has zero compatible targets, so
it cannot supply model results to A+B.

## Decisions

The present A+B artifact is a merged protocol outline, not a result-paper
draft. It retains the explicit route from admissible data to later results and
avoids duplicated A/B contribution claims.

## Validation

- `python -m pytest tests/manuscripts/test_manuscript_portfolio_workflow.py -q`
- `python -m biointerfaceos manuscript audit-portfolio --strict`
- `python scripts/validate_execution_pack.py`

The current audit must report exactly two protocol routes, three protocol
figures, 15 withdrawals, zero T123 compatible targets and no submission-ready
status.

## Failure recovery

If a source, figure or comparator binding differs, restore the protocol-only
route and resolve the audit finding. If T123 cannot admit a target, retain the
portfolio as an honest provenance/benchmark protocol rather than submitting a
fixture result.

## Outputs

Merged outline, portfolio registry, strict audit and receipt, R2 figure/source
cards, literature comparator map, this ExecPlan, and future result-paper
artifacts only after T123/T128 evidence is available.

## Completion note

The protocol route is ready and audited. T126 remains blocked pending genuine
real-model and external-reproduction evidence.
