# T080 Typed Multi-Agent Runtime Evidence

Date: 2026-08-12  
Task: Implement typed multi-agent runtime  
Implementation commit: `035a281` (`feat-implement-typed-agent-runtime`)

## Scope

The runtime defines typed agent, task, and tool-step contracts; enforces tool allowlists and per-task budgets; executes a deterministic mock/rule backend; retries transient failures; replays runs byte-for-byte; and persists an append-only hash-chain trace with a seal. No provider key is required.

## Acceptance results

Command:

```text
biointerfaceos agent self-test
```

Observed first and resumed runs:

```text
AGENT_SELF_TEST_VALID agents=3 tasks=3 events=14 schema_validated=true tool_allowlist=true budget=true replay=true retries=true trace_sealed=true provider_key_required=false resumed=0
AGENT_SELF_TEST_VALID agents=3 tasks=3 events=14 schema_validated=true tool_allowlist=true budget=true replay=true retries=true trace_sealed=true provider_key_required=false resumed=1
```

The typed fixture contains retrieval, extraction, and validation agents. Negative checks reject an undeclared tool and budget overflow; a deterministic transient backend error recovers on the declared retry. The replay trace is byte-identical, and the 14-event hash chain validates against `trace_seal.json`. The mock/rule backend declares `provider_key_required=false`.

## Determinism and artifacts

Outputs:

- `agents/runtime/agent_runtime.v1.json`
- `tests/fixtures/agents/runtime_fixture.json`
- `reports/agents/runtime_audit.json`
- `reports/agents/runtime_results.json`
- `reports/agents/runtime_trace.jsonl`
- `reports/agents/trace_seal.json`
- `reports/agents/failure_ledger.json`
- `reports/agents/agent_receipt.json`
- `reports/agents/agent_log.json`
- `reports/agents/agent_manifest.json`
- `tests/agents/test_agent_runtime.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 283 passed; ruff, format, and mypy passed.
- `biointerfaceos agent self-test`: passed with `provider_key_required=false`.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T080 is complete. T081 is the next active task: implement SourceScout and LicenseGate workflows that recover eligible sources, reject restricted injected cases, and cite metadata evidence without credential requests.
