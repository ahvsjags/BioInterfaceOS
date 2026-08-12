# T086 RedTeam agent suite evidence

Date: 2026-08-12  
Task: Implement RedTeam agent suite  
Implementation commit: `3bc053d` (`feat: add redteam agent suite`)

## Scope

The RedTeamAgent executes a mandatory offline attack matrix for leakage, unit errors, negative controls, adversarial causal language, and lockbox access. Each finding records its expected and observed status, severity, detector evidence, remediation, and preserved adverse payload. A critical-finding gate blocks release if any critical attack is missed.

## Acceptance results

Command:

```text
biointerfaceos agent red-team --all
```

Observed stable run:

```text
REDTEAM_VALID attacks=5 executed=5 detected=2 blocked=2 critical_findings=0 remediations=5 adverse_results_preserved=true release_blocked=false selected_pipeline=redteam_agent trace_events=5 resumed=1
```

The injected paper-identity leakage and mg/g unit error were detected. The adversarial causal claim and forbidden lockbox read were blocked. The permuted-outcome negative control remained clean. All five remediations and adverse results were preserved, the critical release gate passed with zero unresolved critical findings, and the five-event trace is sealed and resumable.

## Determinism and artifacts

Outputs:

- `agents/redteam/redteam.v1.json`
- `tests/fixtures/agents/redteam_fixture.json`
- `reports/agents/redteam/redteam_findings.json`
- `reports/agents/redteam/adverse_results.json`
- `reports/agents/redteam/redteam_comparison.json`
- `reports/agents/redteam/input_manifest.json`
- `reports/agents/redteam/redteam_trace.jsonl`
- `reports/agents/redteam/redteam_trace_seal.json`
- `reports/agents/redteam/failure_ledger.json`
- `reports/agents/redteam/redteam_receipt.json`
- `reports/agents/redteam/redteam_manifest.json`
- `tests/agents/test_redteam_agent_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 301 passed; ruff, format, and mypy passed.
- `biointerfaceos agent red-team --all`: passed with resumable output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T086 is complete. T087 is next: implement Reproducibility and Lockbox evaluator agents with clean fixture rebuild receipts, signed-freeze activation gating, and no training-method exposure.
