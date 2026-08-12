# T072 Direct Black-Box M2 Evidence

Date: 2026-08-12  
Task: Fit direct black-box baseline  
Implementation commit: `4dd1679` (`feat-fit-direct-black-box-m2`)

## Scope

The M2 workflow fits a declared low-capacity `regularized_polynomial_fallback` direct model from public material/environment/protocol features. It uses train-only fitting, preserves all validation rows for OOD evaluation, includes a missingness indicator, and excludes instance/family/group/split identifiers.

## Acceptance results

Command:

```text
biointerfaceos train m2 --config configs/models/m2.yaml
```

Observed first and resumed runs:

```text
M2_VALID instances=16 train=8 validation=8 model_kind=regularized_polynomial_fallback validation_rmse=0.474494 resumed=0 target_values_exposed=false
M2_VALID instances=16 train=8 validation=8 model_kind=regularized_polynomial_fallback validation_rmse=0.474494 resumed=1 target_values_exposed=false
```

Validation RMSE is `0.474494` with deterministic bootstrap interval `[0.400115, 0.535286]`; validation MAE is `0.457643`, calibration error is `0.353439`, and the uncertainty source is train residual SD. Family, validation split, and paper-family group metrics are present. Feature importance combines train permutation delta and coefficient L1; protocol and material features are the leading declared inputs in this fixture.

The feature audit reports `identifier_features_used=false`, excludes `instance_id`, `family`, `group_key`, and `split`, records `train_only_fit=true`, `validation_used_for_tuning=false`, and preserves missingness. The diagnostics state that the low-capacity fallback is intentional because the fixture is small; it is not silently presented as a high-capacity tree/MLP result.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m2.yaml`
- `reports/models/m2/m2_results.json`
- `reports/models/m2/calibration.json`
- `reports/models/m2/feature_audit.json`
- `reports/models/m2/feature_importance.json`
- `reports/models/m2/diagnostics.json`
- `reports/models/m2/failure_ledger.json`
- `reports/models/m2/m2_receipt.json`
- `reports/models/m2/m2_log.json`
- `reports/models/m2/m2_manifest.json`
- `tests/fixtures/models/m2_fixture.json`
- `tests/models/test_m2_workflow.py`

## Verification

- `UV_OFFLINE=1 make check`: 259 passed; ruff, format, and mypy passed.
- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or public target-value exposure was used.

## Handoff

T072 is complete. T073 is the next active task: fit the static corona mediator model with paired-unit audit, direct/mediated comparison, random-mediator control, and uncertainty propagation.
