# T075 Dynamic Corona M5 Evidence

Date: 2026-08-12  
Task: Fit dynamic corona world model  
Implementation commit: `ade3652` (`feat-fit-dynamic-corona-m5-fallback`)

## Scope

The M5 workflow validates time-course corona trajectories against T057 PRIDE-QC and T056 module inputs, applies a G3 data-sufficiency gate, and fits a constrained discrete-kinetics fallback when the high-capacity path is underpowered.

## Acceptance results

Command:

```text
biointerfaceos train m5 --config configs/models/m5.yaml
```

Observed first and resumed runs:

```text
M5_VALID trajectories=3 train_trajectories=2 validation_trajectories=1 model_kind=discrete_kinetics sufficiency_passed=false validation_rmse=0.022236 resumed=0 target_values_exposed=false
M5_VALID trajectories=3 train_trajectories=2 validation_trajectories=1 model_kind=discrete_kinetics sufficiency_passed=false validation_rmse=0.022236 resumed=1 target_values_exposed=false
```

The G3 threshold is six trajectories while the fixture provides three, so the neural ODE/high-capacity path is explicitly `WAIVED` and the declared `discrete_kinetics` fallback is used. Validation trajectory RMSE is `0.022236`; two-fold leave-study-out mean RMSE is `0.064118`. All input and predicted compositions satisfy simplex/mass constraints with zero maximum mass error and zero negative values after the declared clip-and-renormalize policy. Toy dynamics recovery passes.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m5.yaml`
- `reports/models/m5/sufficiency_gate.json`
- `reports/models/m5/trajectory_results.json`
- `reports/models/m5/trajectory_constraints.json`
- `reports/models/m5/leave_study_out.json`
- `reports/models/m5/toy_recovery.json`
- `reports/models/m5/failure_ledger.json`
- `reports/models/m5/m5_receipt.json`
- `reports/models/m5/m5_log.json`
- `reports/models/m5/m5_manifest.json`
- `tests/fixtures/models/m5_fixture.json`
- `tests/models/test_m5_workflow.py`

## Verification

- `UV_OFFLINE=1 make check`: 268 passed; ruff, format, and mypy passed.
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

T075 is complete. T076 is the next active task: preregister DAG/estimands, assess overlap/confounding sensitivity and alternative DAGs, and automatically downgrade causal language when gates fail.
