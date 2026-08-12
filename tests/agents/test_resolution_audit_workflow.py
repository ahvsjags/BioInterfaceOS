import json
from pathlib import Path

import pytest

from biointerfaceos.resolution_audit_workflow import ResolutionAuditError, ResolutionAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_resolution_auditor_detects_conflicts_and_preserves_assertions(tmp_path: Path) -> None:
    summary = ResolutionAuditWorkflow(_root(), output_root=tmp_path / "audit").run()

    assert summary.cases == 4
    assert summary.conflicts == 3
    assert summary.detected == 3
    assert summary.quarantined == 3
    assert summary.original_assertions_preserved is True
    assert summary.false_merge_rate == 0.0
    assert summary.selected_pipeline == "resolution_audit_agent"
    assert summary.trace_events == 4
    assert summary.resumed == 0

    decisions = json.loads((tmp_path / "audit" / "audit_decisions.json").read_text())
    assert all(item["original_preserved"] for item in decisions["decisions"])
    assert {item["reason"] for item in decisions["decisions"]} >= {
        "UNIT_CONFLICT",
        "ENTITY_CONFLICT",
        "EVIDENCE_CONFLICT",
    }


def test_resolution_auditor_writes_only_unresolved_quarantine(tmp_path: Path) -> None:
    ResolutionAuditWorkflow(_root(), output_root=tmp_path / "audit").run()

    quarantine = json.loads((tmp_path / "audit" / "quarantine.json").read_text())
    assert len(quarantine["records"]) == 3
    assert all(record["status"] == "QUARANTINED" for record in quarantine["records"])


def test_resolution_auditor_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = ResolutionAuditWorkflow(_root(), output_root=tmp_path / "audit")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(ResolutionAuditError, match="--fixture is required"):
        workflow.run(fixture=False)
