# T085 ModelBuilder and Statistician agent evidence

Date: 2026-08-12  
Task: Implement ModelBuilder and Statistician agents  
Implementation commit: `033b979` (`feat: add sandboxed modeling agents`)

## Scope

The typed modeling workflow validates model plans and statistical preregistration before execution. One valid plan is compiled and executed in a temporary sandbox. Three adversarial plans are preserved and rejected for metric hacking, split modification, or held-out tuning. The frozen development split is hashed before and after evaluation and is unchanged.

## Acceptance results

Command:

```text
biointerfaceos agent eval modeling
```

Observed stable run:

```text
AGENT_MODELING_VALID plans=4 executable=1 rejected=3 metric_hacking_rejected=1 split_modification_rejected=1 heldout_tuning_rejected=1 tests_generated=5 preregistration_complete=true sandbox_passed=true splits_unchanged=true selected_pipeline=modeling_agent trace_events=4 resumed=1
```

The valid ModelBuilder plan compiled and ran in the sandbox, generated five test assertions across the fixture plans, and carried a complete preregistration. The Statistician/ModelBuilder attack fixtures were rejected deterministically: one post-evaluation metric-selection plan, one split-modification plan, and one held-out-target tuning plan. The executable plan remains proposal-level with `claim_accepted=false`.

## Determinism and artifacts

Outputs:

- `agents/modeling/modeling.v1.json`
- `tests/fixtures/agents/modeling_fixture.json`
- `reports/agents/modeling/modeling_plans.json`
- `reports/agents/modeling/modeling_rejections.json`
- `reports/agents/modeling/modeling_comparison.json`
- `reports/agents/modeling/preregistration.json`
- `reports/agents/modeling/sandbox_receipt.json`
- `reports/agents/modeling/split_integrity_audit.json`
- `reports/agents/modeling/input_manifest.json`
- `reports/agents/modeling/modeling_trace.jsonl`
- `reports/agents/modeling/modeling_trace_seal.json`
- `reports/agents/modeling/failure_ledger.json`
- `reports/agents/modeling/modeling_receipt.json`
- `reports/agents/modeling/modeling_manifest.json`
- `tests/agents/test_modeling_agent_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 298 passed; ruff, format, and mypy passed.
- `biointerfaceos agent eval modeling`: passed with resumable output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T085 is complete. T086 is next: implement the RedTeam agent suite with mandatory leakage, unit-error, negative-control, and adversarial attacks; severity, remediation, and adverse findings must be preserved.
