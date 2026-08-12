# T077 Cross-domain invariant learning

## Purpose

Compare hierarchical ERM with ERM/groupDRO/IRM-like invariant-learning alternatives across at least two domain definitions while preserving environment-label leakage controls and an explicit OOD-improvement gate.

## Preconditions

T071 hierarchical mixed effects, T074 compositional corona, and T076 causal-world audits are valid. Domain labels must be derived from allowed environment metadata and must not expose validation/test outcomes or target-derived fields.

## Non-goals

This task will not use hidden test labels, tune separately on validation environments, or retain a higher-complexity invariant method without an OOD benefit over the hierarchical ERM reference.

## Interfaces and invariants

`biointerfaceos train m7 --config configs/models/m7.yaml` will emit identical-budget model comparisons, at least two domain definitions, a label-leakage audit, OOD metrics, and a complexity decision. If invariant methods fail to improve OOD performance, hierarchical ERM remains the selected main model.

## Implementation plan

1. Define domain-safe feature and environment contracts with a sanitized fixture.
2. Fit hierarchical ERM, groupDRO, and IRM-like alternatives under one frozen tuning budget.
3. Evaluate held-out-domain/OOD performance and audit environment-label leakage.
4. Apply the complexity acceptance rule and emit model comparison, failure ledger, receipt, and manifest.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m7 --config configs/models/m7.yaml`
- at least two domain definitions, identical tuning budgets, no target leakage, and OOD gate assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If invariant methods do not improve OOD performance or fail the leakage audit, retain hierarchical ERM as the main model and record the failure reason. Never use validation/test environment outcomes to construct domains or tune a method.

## Outputs

Versioned M7 config, domain definitions, leakage audit, model comparison, OOD evaluation, complexity decision, focused tests, evidence report, and state/ledger advancement.
