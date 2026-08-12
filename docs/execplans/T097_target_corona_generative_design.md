# T097 Implement target-corona conditional generative design

## Objective

Evaluate a bounded target-corona conditional design generator against the T096
constrained baseline. The workflow must first decide whether the available,
public, fixture-backed data support a generator; if not, it must explicitly waive
deep generation and retain the validated BO/NSGA-II baseline.

## Scope and constraints

- Use only T096 design artifacts and the T079 representation contract as declared
  inputs, with checksums verified before any generation or comparison.
- Freeze the target-corona conditioning variables, component/range support,
  validity rules, OOD threshold, uncertainty policy, budgets, split policy, and
  comparison metrics before proposal generation.
- Gate on data sufficiency: independent groups, target coverage, support density,
  and held-out evaluation must meet predefined thresholds. A failed gate is a
  valid result and must not be converted into a deep-generator claim.
- Compare at least the selected T096 baseline with a deterministic generator
  candidate only when the sufficiency gate passes. Score validity, novelty,
  Pareto coverage, uncertainty, and OOD abstention on held-out candidates.
- Run predefined ablations for conditioning, uncertainty penalty, and support
  restriction. Preserve invalid, OOD, and abstained candidates in ledgers.
- Remain offline and fixture-backed: no network, credentials, raw download,
  locked payload, hidden target values, or post-hoc metric selection.

## Planned implementation

1. Add `agents/design/target_corona_generative.v1.json` with the sufficiency,
   conditioning, generation, validity, OOD, comparison, and ablation contracts.
2. Add `tests/fixtures/design/target_corona_generative_fixture.json` containing
   independent groups, target-corona conditioning records, held-out candidates,
   baseline outputs, and both pass/fail sufficiency scenarios.
3. Implement `src/biointerfaceos/target_corona_generative_workflow.py` with the
   data-sufficiency gate, bounded conditional proposal path, baseline comparison,
   OOD uncertainty handling, ablations, and resume receipts.
4. Expose `biointerfaceos design generative --fixture` and emit preregistration,
   sufficiency audit, proposal ledger, validity/novelty/Pareto comparison,
   uncertainty and abstention ledgers, ablation matrix, lockbox scan, receipt,
   and manifest under `reports/design/generative/`.
5. Add focused tests for sufficiency gating, baseline comparison, OOD abstention,
   ablation completeness, invalid-candidate retention, and deterministic resume.
6. Run focused tests and the complete lockfile, quality, data, release, state, and
   diff gates before recording T097.

## Acceptance criteria

- `DESIGN_GENERATIVE_VALID` reports a frozen data-sufficiency decision and the
  selected fallback or generator path.
- If the gate passes, the generator beats the T096 baseline on predefined
  validity/novelty/Pareto metrics without worse OOD uncertainty; otherwise the
  fallback is explicitly waived and no generator superiority claim is emitted.
- Conditioning, uncertainty, and support-restriction ablations are complete and
  reproducible; invalid/OOD candidates remain auditable.
- Full repository and immutable-release gates pass.

## Failure fallback

If data sufficiency, held-out validity, or OOD uncertainty fails, waive the deep
generator and retain the T096 BO/NSGA-II baseline as the supported design path.
Restrict proposals to observed components and ranges and label all remaining
outputs exploratory.
