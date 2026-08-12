# T088 End-to-end scientific-agent benchmark

## Purpose

Build a reproducible development benchmark over the completed SourceScout/LicenseGate, ExtractionAgent, Resolution/EvidenceAuditor, Mechanism/Hypothesis, ModelBuilder/Statistician, RedTeam, and Reproducibility/Lockbox workflows.

## Preconditions

T067 benchmark instances, T081–T087 agent receipts, typed runtime contracts, split audits, and the immutable fixture release are valid.

## Non-goals

This task will not claim production-scale provider performance, expose locked targets, silently discard failures, or compare multi-agent quality without reporting coordination cost.

## Interfaces and invariants

`biointerfaceos benchmark agents --dev` will execute seven tasks and report no-tool, single-agent, and multi-agent modes. Each mode records completion, correctness, evidence, schema, safety, reproducibility, and cost. The benchmark emits Wilson 95% confidence intervals and a failure taxonomy with preserved failure records.

## Implementation plan

1. Define the benchmark schema, seven-task fixture, metric contract, mode contract, and cost units.
2. Execute each completed workflow through its typed fixture interface and collect resumable receipts.
3. Compute single/multi/no-tool mode metrics, confidence intervals, cost comparison, and failures.
4. Preserve all task outcomes, verify target-value and lockbox invariants, and add CLI/tests.
5. Add evidence report and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos benchmark agents --dev`
- seven tasks complete; all required metrics and confidence intervals are present
- failure taxonomy and cost report are preserved; no locked payload is accessed
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Persist every failed task with a severity and failure type, retain the no-tool baseline, and publish the benchmark even if a multi-agent mode does not improve quality.

## Outputs

Versioned benchmark schema, task fixture, task results, mode comparison, confidence intervals, cost report, failure taxonomy, receipt, focused tests, evidence report, and state/ledger advancement.
