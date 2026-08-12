import json
from pathlib import Path

import pytest

from biointerfaceos.extraction_agent_workflow import (
    ExtractionAgentError,
    ExtractionAgentWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_extraction_agent_selects_parsers_and_improves_fixed_pipeline(tmp_path: Path) -> None:
    summary = ExtractionAgentWorkflow(_root(), output_root=tmp_path / "extraction").run()

    assert summary.cases == 4
    assert summary.agent_correct == 4
    assert summary.fixed_correct == 3
    assert summary.agent_accuracy == 1.0
    assert summary.fixed_accuracy == 0.75
    assert summary.selected_pipeline == "extraction_agent"
    assert summary.schema_valid is True
    assert summary.evidence_grounded is True
    assert summary.trace_events == 8
    assert summary.resumed == 0

    comparison = json.loads((tmp_path / "extraction" / "metric_comparison.json").read_text())
    assert comparison["agent_value"] == 1


def test_extraction_agent_trace_contains_tool_decisions(tmp_path: Path) -> None:
    ExtractionAgentWorkflow(_root(), output_root=tmp_path / "extraction").run()

    records = [
        json.loads(line)
        for line in (tmp_path / "extraction" / "tool_trace.jsonl").read_text().splitlines()
    ]
    assert len(records) == 8
    assert {record["event_type"] for record in records} == {
        "parser_selected",
        "evidence_validated",
    }


def test_extraction_agent_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = ExtractionAgentWorkflow(_root(), output_root=tmp_path / "extraction")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(ExtractionAgentError, match="--fixture is required"):
        workflow.run(fixture=False)
