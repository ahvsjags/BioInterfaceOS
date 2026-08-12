# T100 Run OOD leave-group and sensitivity suite

## Objective

Measure supported model and candidate behavior under leave-group and sensitivity
shifts across study, lab, family, species, biofluid, and time groups. Report
primary metrics, calibration, selective risk, low-n warnings, and evidence-grade
sensitivity without retuning the development models.

## Scope and constraints

- Use the frozen model, uncertainty, multimodal, mediation, symbolic-law, and
  candidate-audit interfaces from T078, T079, T091, T093, T098, and T099.
- Freeze the leave-group definitions, primary metrics, calibration metrics,
  abstention thresholds, sensitivity perturbations, low-n threshold, and
  largest-group selection before evaluating held-out groups.
- Run leave-one-study/lab/family/species/biofluid/time evaluations with group keys
  generated independently of outcome values. Preserve the same model budgets and
  development fit policy for every leave-group run.
- Include leave-largest-study and evidence-grade sensitivity analyses. Flag low-n
  groups rather than pooling them silently; narrow applicability claims when
  calibration or selective risk fails.
- Remain offline and fixture-backed: no network, credentials, raw download, locked
  payload, hidden targets, or post-hoc group selection.

## Planned implementation

1. Add `agents/robustness/ood.v1.json` defining group keys, leave-out policy,
   low-n flags, calibration/selective-risk metrics, sensitivity perturbations, and
   claim narrowing rules.
2. Add `tests/fixtures/robustness/ood_fixture.json` with six group dimensions,
   held-out groups, largest-study metadata, evidence-grade labels, and sensitivity
   scenarios.
3. Implement `src/biointerfaceos/ood_workflow.py` with frozen model reuse,
   leave-group scoring, calibration/selective-risk summaries, low-n warnings,
   largest-study and evidence-grade sensitivity checks, and abstention policy.
4. Expose `biointerfaceos robustness ood --all` and emit group-key audit, primary
   metrics, calibration/selective-risk, sensitivity, low-n ledger, claim gate,
   lockbox scan, receipt, and manifest under `reports/robustness/ood/`.
5. Add focused tests for all group dimensions, no group leakage, low-n flags,
   largest-study selection, evidence-grade sensitivity, and resume determinism.
6. Run focused tests and the complete lockfile, quality, data, release, state, and
   diff gates before recording T100.

## Acceptance criteria

- All six leave-group dimensions run with stable, outcome-independent keys.
- Primary metrics, calibration, selective risk, low-n warnings, leave-largest-
  study, and evidence-grade sensitivity are reported.
- Any failed or low-support group narrows the applicability/wording gate rather
  than being hidden by pooling or retuning.
- Full repository and immutable-release gates pass.

## Failure fallback

Restrict claims to groups with adequate support and calibrated selective risk.
Flag or abstain on low-n/OOD groups, and downgrade the applicable claim language
when leave-group or sensitivity results are unstable.
