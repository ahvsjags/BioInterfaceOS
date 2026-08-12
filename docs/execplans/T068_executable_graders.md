# T068 Implement executable graders and abstention metrics

## Purpose

Implement the deterministic BioInterfaceBench grading path over T067 public instances and the metadata-only hidden target registry. The grader must score known perfect, wrong, and abstaining submissions, report uncertainty/calibration and grouped metrics, and never require network access.

## Preconditions

T067 benchmark instances are schema-valid, leakage-audited, split-frozen, and resumed deterministically. Hidden target values remain unavailable to public benchmark artifacts and are represented only by controlled fixture-side grading inputs.

## Non-goals

This task will not train models, compare real model releases, alter split assignments, fetch data, or expose hidden targets through the public instance layer.

## Interfaces and invariants

`biointerfaceos benchmark grade --fixture` accepts a versioned submission fixture and computes per-instance correctness, abstention/coverage, uncertainty, calibration, and group-aware train/validation metrics. Perfect, wrong, and abstain controls must produce expected scores. Invalid or leaked submissions fail closed.

## Implementation plan

1. Define metric configuration and a strict submission schema with explicit abstention and uncertainty fields.
2. Add a fixture-backed grader that verifies benchmark and submission hashes, resolves controlled hidden targets, and rejects target leakage or unknown instances.
3. Implement exact-match/task-family metrics, abstention coverage/selective risk, uncertainty calibration, and group-key aggregation.
4. Emit deterministic per-instance scores, aggregate metrics, failure ledger, receipt/log/manifest, and focused tests for perfect/wrong/abstain cases.
5. Add the CLI command and validate resume behavior before any model comparison.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos benchmark grade --fixture` for perfect, wrong, and abstain controls
- grouped train/validation metrics, uncertainty/calibration, target-isolation, and no-network assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If a grader exposes a target field, produces a non-deterministic metric, or mis-scores a control, stop benchmark comparison, preserve the failing fixture and receipt, and bump the benchmark version only after the grader contract is corrected.

## Outputs

Versioned grader package, metric configuration, controlled submission fixtures, score/metric artifacts, focused tests, evidence report, and state/ledger advancement.
