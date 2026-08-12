# T093 Discover unit-aware symbolic design laws

## Objective

Implement a deterministic, fixture-backed symbolic-law discovery workflow over normalized material features, T090 functional axes, and outcomes. The workflow must enforce dimensional consistency, compare symbolic candidates against flexible GAM/tree controls, use nested study-level cross-validation, measure bootstrap expression stability and validation OOD behavior, and freeze the complexity penalty before fitting.

## Scope and constraints

- Use T071 normalized feature contracts, T089 frozen hypothesis/preregistration configuration, and T090 functional axes.
- Freeze candidate grammar, allowed operators, unit map, complexity penalty, bootstrap seed, and nested study-CV folds before fitting.
- Generate a bounded candidate set containing interpretable unit-valid expressions and intentionally invalid dimensional candidates that must be rejected.
- Compare symbolic candidates with a GAM-like smooth control and a tree-like flexible control without allowing controls to alter symbolic selection after held-out inspection.
- Report Pareto fronts over error and complexity, expression stability under bootstrap, replication/OOD performance, and an explicit fallback when no stable simple law exists.
- Keep all outcomes fixture-backed and sanitized; no network, credential, raw download, locked payload, or hidden target access.

## Planned implementation

1. Add `agents/discovery/symbolic_laws.v1.json` for grammar, unit constraints, nested folds, controls, complexity, stability, OOD, and claim policy.
2. Add `tests/fixtures/omics/symbolic_laws_fixture.json` with normalized features, units, functional-axis inputs, study/material groups, development/validation/OOD splits, and candidate expressions.
3. Implement `src/biointerfaceos/symbolic_laws_workflow.py` with dimensional algebra, candidate rejection, nested study CV, bounded symbolic scoring, GAM/tree controls, bootstrap expression stability, Pareto ranking, and OOD validation.
4. Expose `biointerfaceos discover symbolic-laws --fixture` and write preregistration, unit audit, candidate ledger, model comparison, Pareto report, stability report, OOD report, fallback/claim gate, lockbox scan, receipt, and manifest under `reports/omics/symbolic_laws/`.
5. Add focused tests for dimensional rejection, study-disjoint folds, frozen complexity, candidate stability, OOD handling, resume determinism, and flexible-control separation.
6. Run focused tests, `UV_OFFLINE=1 make check`, and the complete dependency/assets/catalog/lockbox/release/state gate before recording T093.

## Acceptance criteria

- `SYMBOLIC_LAWS_VALID` reports unit-valid candidates and rejected dimensional candidates.
- Nested study CV is explicit and material/study leakage is absent.
- GAM/tree controls are evaluated but cannot rewrite the frozen symbolic selection rule.
- Complexity penalty, bootstrap configuration, and grammar are frozen before fitting.
- Expression stability and validation OOD behavior are reported; unstable laws trigger the flexible-model fallback and no simple-law claim.
- Resume output is deterministic and full repository/release gates pass.

## Failure fallback

If no candidate satisfies unit, stability, and OOD gates, publish no simple symbolic law. Retain the flexible control as a predictive baseline and report the failure reason and supported scope.
