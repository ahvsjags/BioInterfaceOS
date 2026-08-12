# T088 End-to-end scientific-agent benchmark evidence

Date: 2026-08-12  
Task: Build end-to-end scientific-agent benchmark  
Implementation commit: `259fe20` (`feat: add end-to-end agent benchmark`)

## Scope

The BioInterfaceAgentBench suite runs the completed T081–T087 workflows as seven deterministic tasks and reports no-tool, single-agent, and multi-agent modes. It records completion, correctness, evidence grounding, schema validity, safety, reproducibility, cost units, Wilson 95% confidence intervals, and a preserved failure taxonomy.

## Acceptance results

Command:

```text
biointerfaceos benchmark agents --dev
```

Observed stable run:

```text
AGENT_BENCHMARK_VALID tasks=7 modes=3 completion=1.000000 correctness=1.000000 evidence=1.000000 schema=1.000000 safety=1.000000 reproducibility=1.000000 failures=0 selected_mode=single_agent resumed=1
```

All seven workflows completed successfully. The single-agent and multi-agent modes have identical fixture quality metrics; the multi-agent mode carries explicit coordination cost above single-agent. The no-tool baseline, mode comparison, cost report, confidence intervals, and seven-entry failure taxonomy are all persisted. No failure was hidden or overwritten.

## Determinism and artifacts

Outputs:

- `agents/benchmark/agent_benchmark.v1.json`
- `tests/fixtures/agents/benchmark_fixture.json`
- `reports/benchmark/agents/task_results.json`
- `reports/benchmark/agents/mode_comparison.json`
- `reports/benchmark/agents/confidence_intervals.json`
- `reports/benchmark/agents/cost_report.json`
- `reports/benchmark/agents/failure_taxonomy.json`
- `reports/benchmark/agents/agent_benchmark_receipt.json`
- `reports/benchmark/agents/agent_benchmark_manifest.json`
- `tests/agents/test_agent_benchmark_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 307 passed; ruff, format, and mypy passed.
- `biointerfaceos benchmark agents --dev`: passed with resumable output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T088 is complete. T089 is next: freeze hypothesis tournament and preregistration rules with training-only evidence, duplicate removal, lockbox scan zero, and a hash receipt.
