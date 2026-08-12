# T096 Implement constrained multiobjective design baseline

## Objective

Implement a deterministic, fixture-backed multiobjective design baseline over the public component space. The workflow must enforce mixture/structure constraints, active uncertainty and applicability-domain penalties, recover observed controls, and emit a reproducible Pareto set using enumeration plus bounded NSGA-II/BO-style comparisons.

## Scope and constraints

- Use T041 material/component identity, T078 calibrated uncertainty, T090 functional axes, and T095 supported-scope counterfactuals.
- Freeze component catalog, composition simplex, structure rules, objective definitions, uncertainty/AD penalty weights, search budget, random seed, and Pareto dominance policy before generation.
- Compare exhaustive bounded enumeration against deterministic NSGA-II and Bayesian-optimization-style candidate proposals; retain all invalid candidates in an exclusion ledger.
- Require mixture and structure constraint pass rate ≥0.98, active uncertainty and AD penalties, and recovery of predefined observed controls.
- Keep candidate designs within observed component/range support unless explicitly labeled OOD and abstained. Do not use hidden targets or post-hoc objective changes.
- Remain offline and fixture-backed; no network, credential, raw download, locked payload, or hidden target access.

## Planned implementation

1. Add `agents/design/constrained_baseline.v1.json` for catalog, constraints, objectives, penalties, search budget, control recovery, Pareto, and abstention schemas.
2. Add `tests/fixtures/design/constrained_design_fixture.json` with public components, observed controls, valid/invalid mixtures, structure constraints, surrogate predictions, uncertainty, AD distance, and expected Pareto members.
3. Implement `src/biointerfaceos/design_baseline_workflow.py` with deterministic enumeration, bounded NSGA-II/BO proposal baselines, constraint validation, uncertainty/AD penalties, control recovery, and Pareto selection.
4. Expose `biointerfaceos design baseline --fixture` and emit preregistration, candidate ledger, constraint audit, method comparison, penalty audit, control recovery, Pareto set, abstention ledger, lockbox scan, receipt, and manifest under `reports/design/baseline/`.
5. Add focused tests for simplex/structure constraints, penalty activation, invalid-candidate retention, control recovery, Pareto reproducibility, resume determinism, and OOD abstention.
6. Run focused tests, `UV_OFFLINE=1 make check`, and the complete dependency/assets/catalog/lockbox/release/state gate before recording T096.

## Acceptance criteria

- `DESIGN_BASELINE_VALID` reports enumeration, NSGA-II, and BO-style comparisons under the same frozen budget.
- Mixture/structure constraints pass at least 0.98 and invalid candidates remain auditable.
- Uncertainty and AD penalties are active in the objective and affect Pareto selection.
- Predefined observed controls are recovered within the stated tolerance.
- Pareto output is reproducible; unsupported OOD candidates abstain.
- Full repository/release gates pass.

## Failure fallback

Restrict the design space to observed components and ranges when support or constraint coverage is insufficient. Retain invalid/OOD candidates in audit artifacts and do not present them as valid designs.
