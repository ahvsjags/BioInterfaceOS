# T078 Calibrated Uncertainty and Abstention Evidence

Date: 2026-08-12  
Task: Add calibrated uncertainty and abstention  
Implementation commit: `895b27c` (`feat-add-calibrated-uncertainty-abstention`)

## Scope

The uncertainty workflow consumes validated T071/T072/T074/T076/T077 receipts, calibrates an ensemble/conformal interval by domain, evaluates coverage and selective risk, compares uncertainty against a simple feature-distance OOD detector, and rejects overconfident OOD predictions.

## Acceptance results

Command:

```text
biointerfaceos train uncertainty --config configs/models/uncertainty.yaml
```

Observed first and resumed runs:

```text
UNCERTAINTY_VALID rows=12 calibration=6 validation=6 selected_model=conservative_conformal calibration_passed=false coverage=0.500000 selective_risk_decreases=true ood_abstentions=2 resumed=0 target_values_exposed=false
UNCERTAINTY_VALID rows=12 calibration=6 validation=6 selected_model=conservative_conformal calibration_passed=false coverage=0.500000 selective_risk_decreases=true ood_abstentions=2 resumed=1 target_values_exposed=false
```

The conformal radius is `0.04`, while validation coverage is `0.5` against the `0.8` target; domain coverage is reported for DOMAIN_A, DOMAIN_B, and DOMAIN_C_OOD. The calibration gate therefore selects the conservative conformal fallback. Selective RMSE decreases from `0.129228` at full coverage to `0.014142` at one-third coverage. Both the simple-distance and uncertainty detectors achieve precision/recall/F1 of `1.0` on the two OOD rows, and both OOD rows are abstained with zero overconfident OOD predictions.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/uncertainty.yaml`
- `reports/models/uncertainty/calibration_audit.json`
- `reports/models/uncertainty/selective_risk.json`
- `reports/models/uncertainty/ood_detection.json`
- `reports/models/uncertainty/abstention_policy.json`
- `reports/models/uncertainty/uncertainty_results.json`
- `reports/models/uncertainty/failure_ledger.json`
- `reports/models/uncertainty/uncertainty_receipt.json`
- `reports/models/uncertainty/uncertainty_log.json`
- `reports/models/uncertainty/uncertainty_manifest.json`
- `tests/fixtures/models/uncertainty_fixture.json`
- `tests/models/test_uncertainty_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 277 passed; ruff, format, and mypy passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or public target-value exposure was used.

## Handoff

T078 is complete. T079 is the next active task: compare multimodal material/document representations with missing-modality masks, source-identity leakage checks, and OOD persistence tests.
