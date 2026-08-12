# T084 Mechanism and hypothesis agent evidence

Date: 2026-08-12  
Task: Implement Mechanism and hypothesis agents  
Implementation commit: `bc6a5bd` (`feat: add exploratory hypothesis agent`)

## Scope

The exploratory MechanismHypothesisAgent consumes only training-split evidence links and a training residual summary. It formalizes candidate mechanisms, checks falsifiability, rejects normalized duplicates and ungrounded candidates, scans the development artifacts for lockbox contamination, and emits proposals that are explicitly exploratory. No proposal is marked as an accepted claim.

## Acceptance results

Command:

```text
biointerfaceos agent eval hypothesis
```

Observed stable runs:

```text
AGENT_HYPOTHESIS_VALID proposals=5 valid=2 rejected=3 duplicates=1 falsifiable=4 formalized=5 evidence_linked=4 schema_valid=true lockbox_clean=true claims_auto_accepted=false selected_pipeline=hypothesis_agent trace_events=5 resumed=1
AGENT_HYPOTHESIS_VALID proposals=5 valid=2 rejected=3 duplicates=1 falsifiable=4 formalized=5 evidence_linked=4 schema_valid=true lockbox_clean=true claims_auto_accepted=false selected_pipeline=hypothesis_agent trace_events=5 resumed=1
```

Two candidates remain as unique, formalized, falsifiable, evidence-linked `EXPLORATORY_PROPOSAL` records. Three candidates are rejected: one normalized duplicate, one non-falsifiable candidate, and one candidate without evidence. All five candidates are training-only, the lockbox scan is clean, and automatic claim acceptance is false. The hash-chained five-event trace and all artifacts are resumable.

## Determinism and artifacts

Outputs:

- `agents/hypothesis/hypothesis.v1.json`
- `tests/fixtures/agents/hypothesis_fixture.json`
- `reports/agents/hypothesis/hypothesis_proposals.json`
- `reports/agents/hypothesis/hypothesis_rejections.json`
- `reports/agents/hypothesis/falsifiability_audit.json`
- `reports/agents/hypothesis/provenance_audit.json`
- `reports/agents/hypothesis/lockbox_scan.json`
- `reports/agents/hypothesis/residual_summary.json`
- `reports/agents/hypothesis/hypothesis_comparison.json`
- `reports/agents/hypothesis/hypothesis_trace.jsonl`
- `reports/agents/hypothesis/hypothesis_trace_seal.json`
- `reports/agents/hypothesis/failure_ledger.json`
- `reports/agents/hypothesis/hypothesis_receipt.json`
- `reports/agents/hypothesis/hypothesis_manifest.json`
- `tests/agents/test_hypothesis_agent_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 295 passed; ruff, format, and mypy passed.
- `biointerfaceos agent eval hypothesis`: passed with resumable output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked; hypothesis scan was clean.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T084 is complete. T085 is next: implement ModelBuilder and Statistician agents with sandboxed plan execution, generated tests/preregistration, metric-hacking rejection, and split invariance.
