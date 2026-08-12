# T071 Hierarchical Mixed-Effect M1 Evidence

Date: 2026-08-12  
Task: Fit hierarchical mixed-effect baseline  
Implementation commit: `35e218a` (`feat-fit-hierarchical-mixed-effect-m1`)

## Scope

The M1 workflow fits a deterministic regularized hierarchical baseline with fixed covariate effects and study/protocol/material random effects. Training uses eight train rows only; all eight validation rows have held-out study/protocol/material groups. The model reports variance partition, diagnostics, grouped CV, calibration, and toy parameter recovery.

## Acceptance results

Command:

```text
biointerfaceos train m1 --config configs/models/m1.yaml
```

Observed first and resumed runs:

```text
M1_VALID instances=16 train=8 validation=8 converged=true toy_recovery=true validation_rmse=0.403467 resumed=0 target_values_exposed=false
M1_VALID instances=16 train=8 validation=8 converged=true toy_recovery=true validation_rmse=0.403467 resumed=1 target_values_exposed=false
```

The fit converged with finite residuals/coefficients, identity features disabled, and explicit regularization/non-identifiability limitation. Variance partition is recorded for study, protocol, and material effects; grouped leave-one-study-out CV has four folds and mean RMSE `0.188310`. Validation RMSE is `0.403467` with deterministic bootstrap interval `[0.307747, 0.477449]`; calibration error is `0.298742` using train residual SD as the uncertainty source. The toy fixed-effect control recovers intercept `1.0` and covariate coefficient `2.0` within tolerance `0.01`.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m1.yaml`
- `reports/models/m1/m1_results.json`
- `reports/models/m1/variance_partition.json`
- `reports/models/m1/diagnostics.json`
- `reports/models/m1/calibration.json`
- `reports/models/m1/toy_recovery.json`
- `reports/models/m1/failure_ledger.json`
- `reports/models/m1/m1_receipt.json`
- `reports/models/m1/m1_log.json`
- `reports/models/m1/m1_manifest.json`
- `tests/fixtures/models/m1_fixture.json`
- `tests/models/test_m1_workflow.py`

## Verification

- `UV_OFFLINE=1 make check`: 256 passed; ruff, format, and mypy passed.
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

T071 is complete. T072 is the next active task: fit the direct black-box baseline with train-only tuning, OOD/calibration evaluation, and ID-feature audit.
