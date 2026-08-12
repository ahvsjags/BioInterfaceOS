# T087 Reproducibility and Lockbox evaluator evidence

Date: 2026-08-12  
Task: Implement Reproducibility and Lockbox evaluator agents  
Implementation commit: `d14a6bb` (`feat: add reproducibility lockbox evaluator`)

## Scope

The reproducibility evaluator verifies the immutable fixture release, rebuilds a public grading receipt in a temporary directory, compares independent hashes, and records a metadata-only Lockbox evaluator gate. Unsigned activation is rejected and the evaluator capability surface contains no training methods.

## Acceptance results

Command:

```text
biointerfaceos agent eval reproducibility
```

Observed stable run:

```text
AGENT_REPRODUCIBILITY_VALID release_verified=true rebuild_clean=true hash_match=true lockbox_activation_blocked=true training_methods_exposed=false selected_pipeline=reproducibility_agent trace_events=4 resumed=1
```

The frozen release `bioif-data-20260811-42783ef-e32d9290` verified successfully. The fixture result was rebuilt cleanly and matched its independent recomputed hash. The unsigned freeze token was rejected with `SIGNED_FREEZE_REQUIRED`, and the evaluator capability scan found no `train`, `fit`, `optimize`, `backprop`, or `download` method.

## Determinism and artifacts

Outputs:

- `agents/reproducibility/reproducibility.v1.json`
- `tests/fixtures/agents/reproducibility_fixture.json`
- `reports/agents/reproducibility/reproduction_comparison.json`
- `reports/agents/reproducibility/rebuild_receipt.json`
- `reports/agents/reproducibility/lockbox_activation_gate.json`
- `reports/agents/reproducibility/evaluator_capabilities.json`
- `reports/agents/reproducibility/input_manifest.json`
- `reports/agents/reproducibility/reproducibility_trace.jsonl`
- `reports/agents/reproducibility/reproducibility_trace_seal.json`
- `reports/agents/reproducibility/failure_ledger.json`
- `reports/agents/reproducibility/reproducibility_receipt.json`
- `reports/agents/reproducibility/reproducibility_manifest.json`
- `tests/agents/test_reproducibility_agent_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 304 passed; ruff, format, and mypy passed.
- `biointerfaceos agent eval reproducibility`: passed with resumable output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T087 is complete. T088 is next: run the end-to-end scientific-agent benchmark across the completed workflow suite.
