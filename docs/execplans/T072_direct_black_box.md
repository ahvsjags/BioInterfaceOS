# T072 Fit direct black-box baseline

## Purpose

Implement a deterministic direct black-box M2 baseline over public material/environment/protocol features. The fit must use train-only configuration, preserve OOD validation, report calibration and feature importance, and exclude identifiers.

## Preconditions

T069 simple baselines, T070 representation coverage, T071 M1 diagnostics, and T063 group keys are valid. M2 must consume public inputs only, preserve all split rows, and use no network or locked test payload.

## Non-goals

This task will not tune on validation outcomes, use IDs or group keys as predictive features, claim causal effects, or replace the M1 mixed-effect baseline. More complex mediator/compositional models belong to later tasks.

## Interfaces and invariants

`biointerfaceos train m2 --config configs/models/m2.yaml` runs the declared direct model and reports train/validation OOD metrics, calibration, feature audit, permutation/SHAP-style importance, and deterministic artifacts. If the fixture is too small for a complex model, a declared simpler ridge/tree fallback is valid.

## Implementation plan

1. Define versioned M2 config and public feature audit with IDs/group keys excluded.
2. Build deterministic material/environment/protocol feature vectors with missingness indicators.
3. Fit a bounded direct black-box baseline on train only and evaluate validation OOD.
4. Compute calibration, grouped metrics, permutation importance and a declared interpretability audit.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m2 --config configs/models/m2.yaml`
- train-only fit, OOD validation, calibration, grouped metrics, and ID exclusion assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If the fixture is too small for a high-capacity model, preserve a simpler declared fallback and report the limitation. Any ID-feature detection, validation tuning, or split mismatch blocks the fit.

## Outputs

Versioned M2 config, model/result/diagnostic artifacts, feature/importance audit, calibration/OOD report, focused tests, evidence report, and state/ledger advancement.
