# T069 Statistical Baselines Evidence

Date: 2026-08-12  
Task: Implement data/statistical benchmark baselines  
Implementation commit: `65ac83c` (`feat-add-simple-benchmark-baselines`)

## Scope

The simple baseline runner consumes T067 public instances and the T068 metric artifact through a fixture-only numeric target contract. It constructs deterministic public feature vectors with an explicit identifier/locator/cluster audit, uses the frozen train/validation split, and runs five baselines under one command.

## Acceptance results

Command:

```text
biointerfaceos benchmark run-baselines --group simple
```

Observed first and resumed runs:

```text
BASELINES_VALID group=simple baselines=5 successful=5 validation_instances=8 best_rmse=0.409268 resumed=0 target_values_exposed=false
BASELINES_VALID group=simple baselines=5 successful=5 validation_instances=8 best_rmse=0.409268 resumed=1 target_values_exposed=false
```

All five requested baselines completed: mean, family mean, kNN, ridge-linear, and shrinkage mixed-effect. Validation primary OOD RMSE and deterministic 95% bootstrap intervals were recorded:

| Baseline | Validation RMSE | 95% bootstrap interval |
| --- | ---: | ---: |
| mean | 0.409268 | [0.325000, 0.476314] |
| family mean | 0.436248 | [0.259808, 0.600260] |
| kNN | 0.425041 | [0.270352, 0.554996] |
| linear | 0.439561 | [0.318383, 0.537817] |
| mixed-effect | 0.425000 | [0.276275, 0.561736] |

Every baseline records seed `17`, bootstrap sample count `128`, configuration, train/validation metrics, family/split/group metrics, primary OOD metric, confidence interval, and validation missingness. No baseline silently uses a complete-case subset; an instance-level missingness indicator is included.

The feature audit marks identifier features excluded and records excluded `candidate_count`, `evidence_grade`, `evidence_locator`, `panel_id`, and `protocol_cluster` fields. Group keys are used for reporting only and never as predictive features. No target value is written to result, receipt, log, manifest, or failure artifacts.

## Determinism and artifacts

The second run returned `resumed=1` after byte-for-byte comparison. Outputs:

- `reports/benchmark/baselines/baseline_results.json`
- `reports/benchmark/baselines/feature_audit.json`
- `reports/benchmark/baselines/failure_ledger.json`
- `reports/benchmark/baselines/baseline_receipt.json`
- `reports/benchmark/baselines/baseline_log.json`
- `reports/benchmark/baselines/baseline_manifest.json`
- `tests/fixtures/benchmark/baseline_fixture.json`
- `tests/benchmark/test_benchmark_baselines.py`

## Verification

- `UV_OFFLINE=1 make check`: 250 passed; ruff, format, and mypy passed.
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

T069 is complete. T070 is the next active task: compare descriptor, fingerprint, text, and available polymer-embedding representation baselines under identical splits with explicit missing-structure coverage.
