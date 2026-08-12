# T102 Run negative controls and deliberate leakage attacks

## Objective

Stress-test the data/model/claim boundary with negative controls and deliberate
leakage attacks. Verify that label shuffles, random mediators, study/journal/year/
layout proxies, unit/missingness proxies, and duplicate attacks do not produce
accepted performance or claim leakage. Critical leaks must invalidate the affected
release/model and rebuild from the last clean state.

## Scope and constraints

- Use T086 extraction outputs, T099 ablation controls, T100 OOD groups, and T101
  selection/missingness ledgers as frozen inputs.
- Freeze attack names, attack budgets, expected-failure thresholds, criticality,
  leakage detectors, duplicate fingerprints, and release rollback policy before
  running any attack.
- Run each negative control under the same split/group and model budget as its
  corresponding positive path. Keep attack features isolated from target values.
- Treat expected negative-control failure as a pass for the firewall; treat any
  critical attack that retains performance or leaks target proxies as a hard fail.
- Preserve attack traces and evidence for every control. Do not suppress a failed
  control because it changes the headline metric.
- Remain offline and fixture-backed: no network, credentials, raw download, locked
  payload, hidden targets, or provider-backed attack data.

## Planned implementation

1. Add `agents/robustness/negative_controls.v1.json` defining attacks, budgets,
   expected outcomes, criticality, leak detectors, and rollback behavior.
2. Add `tests/fixtures/robustness/negative_controls_fixture.json` with positive
   controls, shuffled labels, random mediators, metadata proxies, units/missingness,
   duplicate fingerprints, and attack traces.
3. Implement `src/biointerfaceos/negative_controls_workflow.py` with attack
   execution, performance/leakage thresholds, duplicate detection, critical-fail
   gate, and clean-release rollback receipt.
4. Expose `biointerfaceos robustness negative-controls --strict` and emit attack
   preregistration, control results, leakage audit, duplicate audit, rollback/claim
   gate, lockbox scan, receipt, and manifest under `reports/robustness/negative_controls/`.
5. Add focused tests for expected attack failures, critical leak detection,
   duplicate attacks, strict-mode exit behavior, and resume determinism.
6. Run focused tests and the complete lockfile, quality, data, release, state, and
   diff gates before recording T102.

## Acceptance criteria

- All declared negative controls and deliberate leakage attacks run under frozen
  budgets/splits.
- Expected attacks fail performance or are detected; critical leakage count is
  zero and the strict claim gate passes.
- Duplicate, unit/missingness, and metadata-proxy attacks are explicitly audited.
- Any critical leak triggers the declared rollback/invalidation path.
- Full repository and immutable-release gates pass.

## Failure fallback

Invalidate the affected model/data release and restore the last clean release when
any critical leak survives the firewall. Narrow claims and retain the failing
attack trace until a clean rebuild is verified.
