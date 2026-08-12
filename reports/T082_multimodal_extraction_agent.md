# T082 Multimodal ExtractionAgent Evidence

Date: 2026-08-12  
Task: Implement multimodal ExtractionAgent  
Implementation commit: `279a4d2` (`feat-add-extraction-agent-evaluation`)

## Scope

The ExtractionAgent selects an allowlisted parser for table, figure, supplement, and PDF cases. Every emitted field is checked for type/schema validity, confidence range, and `asset:` evidence locators. The agent is compared with the fixed pipeline and is retained only when its declared metric improves.

## Acceptance results

Command:

```text
biointerfaceos agent eval extraction
```

Observed first and resumed runs:

```text
AGENT_EXTRACTION_VALID cases=4 agent_correct=4 fixed_correct=3 agent_accuracy=1.000000 fixed_accuracy=0.750000 selected_pipeline=extraction_agent schema_valid=true evidence_grounded=true trace_events=8 resumed=0
AGENT_EXTRACTION_VALID cases=4 agent_correct=4 fixed_correct=3 agent_accuracy=1.000000 fixed_accuracy=0.750000 selected_pipeline=extraction_agent schema_valid=true evidence_grounded=true trace_events=8 resumed=1
```

The agent improves accuracy from `0.75` to `1.0`, all four parser selections are correct, all emitted records are schema-valid and evidence-grounded, and the fixed-pipeline fallback remains encoded in the acceptance rule for future cases. The 8-event tool trace records parser selection and evidence validation for every case.

## Determinism and artifacts

Outputs:

- `tests/fixtures/agents/extraction_agent_fixture.json`
- `reports/agents/extraction/parser_decisions.json`
- `reports/agents/extraction/extracted_records.json`
- `reports/agents/extraction/metric_comparison.json`
- `reports/agents/extraction/tool_trace.jsonl`
- `reports/agents/extraction/tool_trace_seal.json`
- `reports/agents/extraction/failure_ledger.json`
- `reports/agents/extraction/extraction_agent_receipt.json`
- `reports/agents/extraction/extraction_agent_log.json`
- `reports/agents/extraction/extraction_agent_manifest.json`
- `tests/agents/test_extraction_agent_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 289 passed; ruff, format, and mypy passed.
- `biointerfaceos agent eval extraction`: passed with resumed byte-identical output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T082 is complete. T083 is the next active task: implement Resolution and EvidenceAuditor agents with conflict injection, false-merge controls, and preservation of original assertions.
