# T068 Benchmark Grader Evidence

Date: 2026-08-12  
Task: Implement executable graders and abstention metrics  
Implementation commit: `ac7a81a` (`feat-add-benchmark-grader-metrics`)

## Scope

The grader consumes the T067 public instance layer and metadata-only hidden registry, with target values supplied only by a marked fixture-only control file. It emits per-instance correctness/abstention scores, overall metrics, family/split/group-key metrics, failure ledger, and deterministic processing artifacts. No network path or locked payload path is used.

## Acceptance results

Command:

```text
biointerfaceos benchmark grade --fixture
```

Observed first and resumed runs:

```text
BENCHMARK_GRADE_VALID cases=3 instances=16 perfect_accuracy=1.000000 wrong_accuracy=0.000000 abstain_coverage=0.000000 resumed=0 target_values_exposed=false
BENCHMARK_GRADE_VALID cases=3 instances=16 perfect_accuracy=1.000000 wrong_accuracy=0.000000 abstain_coverage=0.000000 resumed=1 target_values_exposed=false
```

The three controls are generated from explicit fixture-only targets: perfect predictions score accuracy 1.0, wrong predictions score accuracy 0.0, and complete abstention scores coverage 0.0 with 16 abstentions. Metrics are computed for all eight families, train/validation splits, and both attached paper-family group keys. Calibration error, mean uncertainty, answered accuracy, coverage, selective risk, and abstention counts are deterministic and present in `metrics.json`.

The grader validates the T067 public and hidden-registry hashes, rejects unknown or duplicate identities, requires complete target coverage in the controlled fixture, and rejects forbidden target fields from the public benchmark. Score artifacts contain only instance identity/group metadata plus correctness, abstention, and uncertainty; target values and predictions are not written. Every grading artifact records `target_values_exposed=false`.

## Determinism and artifacts

The first grading run wrote the artifacts and the second run returned `resumed=1` after byte-for-byte comparison. Outputs:

- `reports/benchmark/grading/instance_scores.json`
- `reports/benchmark/grading/metrics.json`
- `reports/benchmark/grading/failure_ledger.json`
- `reports/benchmark/grading/grading_receipt.json`
- `reports/benchmark/grading/grading_log.json`
- `reports/benchmark/grading/grading_manifest.json`
- `tests/fixtures/benchmark/grading_fixture.json`
- `tests/benchmark/test_benchmark_grading.py`

## Verification

- `UV_OFFLINE=1 make check`: 247 passed; ruff, format, and mypy passed.
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

T068 is complete. T069 is the next active task: implement one-command data/statistical baselines with logged seeds/configs, primary OOD metrics, and confidence intervals.
