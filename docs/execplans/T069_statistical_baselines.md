# T069 Implement data/statistical benchmark baselines

## Purpose

Implement reproducible simple data/statistical baselines over the validated T067 benchmark instances and T068 grader contract. The baseline runner must execute mean, family, kNN, linear, and declared mixed-effect controls from one command, log seeds/configuration, and report primary OOD metrics with confidence intervals.

## Preconditions

T067 instances are schema-valid and split-frozen. T068 grading and abstention metrics are executable and deterministic. Baselines must consume public inputs and controlled grading interfaces without reading locked test data or using network access.

## Non-goals

This task will not tune against validation outcomes, alter group assignments, train neural models, fetch external data, or silently remove missing structures. Representation baselines belong to T070.

## Interfaces and invariants

`biointerfaceos benchmark run-baselines --group simple` runs every declared simple baseline under the same train/validation split and metric configuration. Each result records seed, feature policy, eligible rows, missingness, grouped metrics, primary OOD metric, and a deterministic confidence interval. Failures are retained as explicit baseline limitations.

## Implementation plan

1. Define versioned baseline and metric configuration with fixed seeds and a no-ID feature audit.
2. Build public feature matrices with explicit missingness indicators and family/group-key joins.
3. Implement train-only mean, family mean, kNN, linear, and a bounded mixed-effect/simple fallback baseline.
4. Evaluate with T068 grader metrics, bootstrap confidence intervals, and train/validation/group reports.
5. Emit deterministic baseline results, failure ledger, receipt/log/manifest, focused tests, and CLI output.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos benchmark run-baselines --group simple`
- all five simple baselines attempted from one command with seeds/configs logged
- primary OOD metrics, confidence intervals, missingness, and group containment audited
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If a baseline cannot run because the development fixture is underpowered, preserve the failure and report it as a baseline limitation; do not silently skip it or use validation outcomes for tuning. Any group leakage or ID feature detection blocks the benchmark run.

## Outputs

Versioned baseline configuration and feature audit, baseline result/metric artifacts, failure ledger, deterministic receipts/logs/manifests, focused tests, evidence report, and state/ledger advancement.
