# T078 Calibrated uncertainty and abstention

## Purpose

Add calibrated uncertainty and abstention around the accepted hierarchical/predictive models, with domain-wise calibration, coverage, selective-risk curves, and an OOD detector compared against a simple distance baseline.

## Preconditions

T071, T072, T074, T076, and T077 are valid. The uncertainty layer must consume model predictions and held-out domain metadata without accessing hidden test labels or retuning on test outcomes.

## Non-goals

This task will not report overconfident predictions on OOD inputs, use validation targets to tune the hidden test threshold, or claim calibrated probabilities when only fixture residuals are available.

## Interfaces and invariants

`biointerfaceos train uncertainty --config configs/models/uncertainty.yaml` will emit ensemble/conformal uncertainty, domain calibration, coverage and selective-risk curves, OOD detector comparison, and an abstention policy. Conservative conformal or ensemble fallback is selected if calibration gates fail.

## Implementation plan

1. Define a sanitized prediction/residual fixture with in-domain and OOD distance metadata.
2. Fit deterministic ensemble/conformal intervals using a frozen calibration split.
3. Evaluate calibration by domain, coverage, selective risk, and abstention thresholds.
4. Compare OOD detection against a simple feature-distance baseline and reject overconfident OOD predictions.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train uncertainty --config configs/models/uncertainty.yaml`
- calibration-by-domain, coverage, selective-risk monotonicity, and OOD detector assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If calibration is insufficient or OOD detection is weak, use conservative ensemble/conformal intervals and abstain on high-distance inputs. Record the failure and never retain an overconfident OOD prediction.

## Outputs

Versioned uncertainty config, calibration audit, conformal/ensemble intervals, selective-risk curve, OOD detector comparison, abstention policy, focused tests, evidence report, and state/ledger advancement.
