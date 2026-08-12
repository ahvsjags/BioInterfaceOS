# T070 Representation Baselines Evidence

Date: 2026-08-12  
Task: Implement representation benchmark baselines  
Implementation commit: `70d2dd4` (`feat-add-representation-baselines`)

## Scope

The representation runner compares descriptor, fingerprint, text, and available polymer-embedding representations under the same T067 train/validation rows and deterministic metric/CI contract. Structure-dependent representations retain all rows in the primary split and expose available-subset metrics separately.

## Acceptance results

Command:

```text
biointerfaceos benchmark run-baselines --group representation
```

Observed first and resumed runs:

```text
REPRESENTATIONS_VALID group=representation baselines=4 successful=4 validation_instances=8 best_rmse=0.377238 resumed=0 target_values_exposed=false
REPRESENTATIONS_VALID group=representation baselines=4 successful=4 validation_instances=8 best_rmse=0.377238 resumed=1 target_values_exposed=false
```

Full-split primary validation RMSE results:

| Representation | Validation RMSE | 95% bootstrap interval | Validation coverage |
| --- | ---: | ---: | ---: |
| descriptor | 0.488469 | [0.323547, 0.636269] | 3/8 (0.375) |
| fingerprint | 0.377238 | [0.260303, 0.462553] | 3/8 (0.375) |
| text | 0.412300 | [0.324568, 0.490662] | 8/8 (1.000) |
| polymer embedding | 0.406077 | [0.294124, 0.478852] | 0/8 (0.000) |

The structure-dependent coverage audit reports structure missing fraction `0.5625`. Descriptor and fingerprint available-subset metrics are retained, while their full-split missingness-indicator results remain primary. Text is available for all rows. Polymer embedding has three train-side available rows and no validation-side available rows; its full-split result is retained as a declared pilot/coverage limitation rather than presented as an available-subset validation result.

All four results include seed `23`, bootstrap count `128`, family/split/group metrics, train/full-validation metrics, availability counts, missingness-indicator usage, and target isolation. No complete-case result replaces the primary full split.

## Determinism and artifacts

The second run returned `resumed=1` after byte-for-byte comparison. Outputs:

- `reports/benchmark/representations/representation_results.json`
- `reports/benchmark/representations/coverage_audit.json`
- `reports/benchmark/representations/failure_ledger.json`
- `reports/benchmark/representations/representation_receipt.json`
- `reports/benchmark/representations/representation_log.json`
- `reports/benchmark/representations/representation_manifest.json`
- `tests/fixtures/benchmark/representation_fixture.json`
- `tests/benchmark/test_benchmark_representations.py`

## Verification

- `UV_OFFLINE=1 make check`: 253 passed; ruff, format, and mypy passed.
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

T070 is complete. T071 is the next active task: fit the hierarchical mixed-effect M1 baseline with variance partition, diagnostics, grouped CV/calibration, and toy parameter recovery.
