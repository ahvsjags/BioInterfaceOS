# T067 Benchmark Instances Evidence

Date: 2026-08-12  
Task: Build BioInterfaceBench task instances  
Implementation commit: `1944caf` (`feat-build-benchmark-instances`)

## Scope

The development-only benchmark builder consumes the approved T048 Gold-auto, T056 corona-module, T062 modality-link, and T065 frozen split artifacts. It emits a public instance layer, a metadata-only hidden-target registry, family coverage/missingness audit, and deterministic processing receipt, log, and manifest.

## Acceptance results

Command:

```text
biointerfaceos benchmark build --dev --fixture
```

Observed first and resumed runs:

```text
BENCHMARK_BUILD_VALID instances=16 families=8 primary_families=8 pilot_families=0 train=8 validation=8 missingness_mean=0.075000 resumed=0 target_values_exposed=false
BENCHMARK_BUILD_VALID instances=16 families=8 primary_families=8 pilot_families=0 train=8 validation=8 missingness_mean=0.075000 resumed=1 target_values_exposed=false
```

All eight declared families (E1/C1/U1/S1/B1/CF1/D1/A1) have two instances, one train and one validation instance, so all remain PRIMARY. No family was underpowered or silently dropped. Every instance has a non-empty T065 paper-family group key, an evidence locator, a bounded missingness value, and a hidden-target reference plus lowercase SHA-256 digest.

The public layer contains no hidden-target reference or digest and the recursive forbidden-field audit is empty. The hidden registry contains only instance identity, split/family metadata, reference, and digest; no target value is stored. `target_values_exposed=false` is recorded in the public layer, hidden registry, coverage audit, receipt, and manifest.

## Determinism and artifacts

The first build wrote the artifacts and the second build returned `resumed=1` after byte-for-byte comparison. Outputs:

- `reports/benchmark/instances/public_instances.json`
- `reports/benchmark/instances/hidden_target_registry.json`
- `reports/benchmark/instances/coverage_audit.json`
- `reports/benchmark/instances/processing_receipt.json`
- `reports/benchmark/instances/processing_log.json`
- `reports/benchmark/instances/processing_manifest.json`
- `tests/fixtures/benchmark/benchmark_fixture.json`
- `tests/benchmark/test_benchmark_instances.py`

## Verification

- `UV_OFFLINE=1 make check`: 244 passed; ruff, format, and mypy passed.
- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or target-value access was used.

## Handoff

T067 is complete. T068 is the next active task: implement executable graders and abstention metrics over these validated instances, with known perfect/wrong/abstain fixtures before any model comparison.
