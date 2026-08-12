# T083 Resolution and EvidenceAuditor Evidence

Date: 2026-08-12  
Task: Implement Resolution and EvidenceAuditor agents  
Implementation commit: `ea1fb86` (`feat: add resolution evidence auditor`)

## Scope

The Resolution and EvidenceAuditor workflow evaluates unit, entity, and evidence assertions against deterministic conflict rules. Conflicting candidates are detected and quarantined, while agreeing candidates remain resolved. The workflow copies original assertions before auditing and records them unchanged in every decision; it never exposes target values as a hidden acceptance signal.

## Acceptance results

Command:

```text
biointerfaceos agent eval audit
```

Observed first and resumed runs:

```text
AGENT_AUDIT_VALID cases=4 conflicts=3 detected=3 quarantined=3 original_assertions_preserved=true false_merge_rate=0.000000 selected_pipeline=resolution_audit_agent trace_events=4 resumed=0
AGENT_AUDIT_VALID cases=4 conflicts=3 detected=3 quarantined=3 original_assertions_preserved=true false_merge_rate=0.000000 selected_pipeline=resolution_audit_agent trace_events=4 resumed=1
```

All injected unit, entity, and evidence conflicts are detected. The deterministic quarantine fallback handles all three unresolved cases, the agreement case remains resolved, the false-merge rate is `0`, and all original assertions are preserved. The four-event hash-chained trace is sealed and resumable.

## Determinism and artifacts

Outputs:

- `tests/fixtures/agents/resolution_audit_fixture.json`
- `reports/agents/audit/audit_decisions.json`
- `reports/agents/audit/audit_comparison.json`
- `reports/agents/audit/quarantine.json`
- `reports/agents/audit/audit_trace.jsonl`
- `reports/agents/audit/audit_trace_seal.json`
- `reports/agents/audit/failure_ledger.json`
- `reports/agents/audit/audit_receipt.json`
- `reports/agents/audit/audit_log.json`
- `reports/agents/audit/audit_manifest.json`
- `tests/agents/test_resolution_audit_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 292 passed; ruff, format, and mypy passed.
- `biointerfaceos agent eval audit`: passed with resumed output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T083 is complete. T084 is next: implement exploratory Mechanism and hypothesis agents with formalized, evidence-linked, falsifiable, nonduplicate proposals and zero lockbox contamination.
