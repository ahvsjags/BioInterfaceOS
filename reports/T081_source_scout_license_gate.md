# T081 SourceScout and LicenseGate Evidence

Date: 2026-08-12  
Task: Implement SourceScout and LicenseGate agents  
Implementation commit: `dd10de0` (`feat-add-source-scout-license-gate`)

## Scope

SourceScout recovers anonymous public metadata from deterministic candidates. LicenseGate delegates classification to the existing default-deny `SourcePolicyEngine`, preserves evidence locations, writes a deterministic rejection registry, and never requests credentials.

## Acceptance results

Command:

```text
biointerfaceos agent eval source-license
```

Observed first and resumed runs:

```text
AGENT_SOURCE_LICENSE_VALID cases=5 recovered=2 rejected_or_quarantined=3 evidence_complete=true no_credentials_requested=true agent_value=0 resumed=0
AGENT_SOURCE_LICENSE_VALID cases=5 recovered=2 rejected_or_quarantined=3 evidence_complete=true no_credentials_requested=true agent_value=0 resumed=1
```

The cases include CC-BY admission, CC-BY-NC analysis-only admission, login-required rejection, restricted-license rejection, and unknown-license quarantine. All five decisions cite fixture metadata evidence; three rejected/quarantined records are written to `rejected_sources.parquet`. Agent value is `0` because deterministic policy fallback produces the same accepted/rejected outcome.

## Determinism and artifacts

Outputs:

- `tests/fixtures/agents/source_license_fixture.json`
- `reports/agents/source_license/source_scout.json`
- `reports/agents/source_license/license_gate.json`
- `reports/agents/source_license/source_license_audit.json`
- `reports/agents/source_license/rejected_sources.parquet`
- `reports/agents/source_license/failure_ledger.json`
- `reports/agents/source_license/source_license_receipt.json`
- `reports/agents/source_license/source_license_log.json`
- `reports/agents/source_license/source_license_manifest.json`
- `tests/agents/test_source_license_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 286 passed; ruff, format, and mypy passed.
- `biointerfaceos agent eval source-license`: passed with no credential request.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T081 is complete. T082 is the next active task: implement ExtractionAgent parser selection and schema-valid evidence-grounded experiment extraction, retaining the fixed pipeline when agent value is not positive.
