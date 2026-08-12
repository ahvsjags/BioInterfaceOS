import json
from pathlib import Path

import pytest

from biointerfaceos.agent_runtime import AgentRuntime, AgentRuntimeError


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_agent_runtime_self_test_passes_all_contract_gates(tmp_path: Path) -> None:
    summary = AgentRuntime(_root(), output_root=tmp_path / "agents").run()

    assert summary.agents == 3
    assert summary.tasks == 3
    assert summary.events > 0
    assert summary.schema_validated is True
    assert summary.tool_allowlist_passed is True
    assert summary.budget_passed is True
    assert summary.replay_passed is True
    assert summary.retry_passed is True
    assert summary.trace_sealed is True
    assert summary.provider_key_required is False
    assert summary.resumed == 0

    audit = json.loads((tmp_path / "agents" / "runtime_audit.json").read_text())
    failures = json.loads((tmp_path / "agents" / "failure_ledger.json").read_text())
    assert audit["provider_key_required"] is False
    assert failures["status"] == "VALID"
    assert failures["failures"] == []


def test_agent_runtime_trace_is_append_only_and_sealed(tmp_path: Path) -> None:
    AgentRuntime(_root(), output_root=tmp_path / "agents").run()

    trace = (tmp_path / "agents" / "runtime_trace.jsonl").read_text().splitlines()
    seal = json.loads((tmp_path / "agents" / "trace_seal.json").read_text())
    assert len(trace) > 0
    assert seal["events"] == len(trace)
    records = [json.loads(line) for line in trace]
    assert [record["sequence"] for record in records] == list(range(1, len(records) + 1))
    assert any(record["event_type"] == "retry_scheduled" for record in records)


def test_agent_runtime_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = AgentRuntime(_root(), output_root=tmp_path / "agents")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(AgentRuntimeError, match="--fixture is required"):
        workflow.run(fixture=False)
