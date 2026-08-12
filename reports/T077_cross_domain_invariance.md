# T077 Cross-domain Invariant Learning Evidence

Date: 2026-08-12  
Task: Add cross-domain invariant learning  
Implementation commit: `b652387` (`feat-fit-cross-domain-invariant-m7`)

## Scope

The M7 workflow compares ERM, groupDRO, IRM-like, and hierarchical ERM models under one frozen tuning budget. It constructs two domain definitions from non-target metadata, audits label leakage, evaluates held-out validation domains as OOD, and accepts added complexity only when the OOD improvement exceeds the preregistered threshold.

## Acceptance results

Command:

```text
biointerfaceos train m7 --config configs/models/m7.yaml
```

Observed first and resumed runs:

```text
M7_VALID rows=16 train=8 validation=8 domain_definitions=2 selected_model=hierarchical_erm hierarchical_erm_rmse=0.080885 ood_rmse=0.080885 leakage_passed=true resumed=0 target_values_exposed=false
M7_VALID rows=16 train=8 validation=8 domain_definitions=2 selected_model=hierarchical_erm hierarchical_erm_rmse=0.080885 ood_rmse=0.080885 leakage_passed=true resumed=1 target_values_exposed=false
```

Study and protocol metadata provide two domain definitions. Validation domains `STUDY_C` and `STUDY_D` are unseen during training, and no target-derived source is permitted. The groupDRO alternative is numerically better on this fixture (`0.065875` vs hierarchical ERM `0.080885`), but the improvement is `0.015010`, below the frozen `0.02` complexity gate. Therefore the workflow retains `hierarchical_erm` as the selected main model and records the invariant comparison without over-accepting complexity.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m7.yaml`
- `reports/models/m7/domain_audit.json`
- `reports/models/m7/model_comparison.json`
- `reports/models/m7/ood_evaluation.json`
- `reports/models/m7/m7_results.json`
- `reports/models/m7/failure_ledger.json`
- `reports/models/m7/m7_receipt.json`
- `reports/models/m7/m7_log.json`
- `reports/models/m7/m7_manifest.json`
- `tests/fixtures/models/m7_fixture.json`
- `tests/models/test_m7_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 274 passed; ruff, format, and mypy passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or public target-value exposure was used.

## Handoff

T077 is complete. T078 is the next active task: add calibrated uncertainty and abstention, compare domain calibration and selective risk, and reject overconfident OOD predictions.
