import json
from pathlib import Path

from biointerfaceos.agent_benchmark_workflow import AgentBenchmarkWorkflow


def test_agent_benchmark_reports_all_modes_and_metrics() -> None:
    root = Path(__file__).parents[2]
    summary = AgentBenchmarkWorkflow(root).run(development=True)

    assert summary.tasks == 7
    assert summary.modes == 3
    assert summary.completion == 1.0
    assert summary.correctness == 1.0
    assert summary.evidence == 1.0
    assert summary.schema == 1.0
    assert summary.safety == 1.0
    assert summary.reproducibility == 1.0
    assert summary.failures == 0
    assert summary.selected_mode == "single_agent"
    comparison = json.loads((root / "reports/benchmark/agents/mode_comparison.json").read_text(encoding="utf-8"))
    assert set(comparison["modes"]) == {"no_tool", "single_agent", "multi_agent"}
    assert comparison["modes"]["multi_agent"]["cost_units"] > comparison["modes"]["single_agent"]["cost_units"]


def test_agent_benchmark_preserves_failure_taxonomy_and_intervals() -> None:
    root = Path(__file__).parents[2]
    AgentBenchmarkWorkflow(root).run(development=True)

    confidence = json.loads((root / "reports/benchmark/agents/confidence_intervals.json").read_text(encoding="utf-8"))
    assert confidence["metrics"]["completion"]["confidence_interval_95"][0] > 0.0
    failures = json.loads((root / "reports/benchmark/agents/failure_taxonomy.json").read_text(encoding="utf-8"))
    assert len(failures["failures"]) == 7
    assert all(row["preserved"] is True for row in failures["failures"])


def test_agent_benchmark_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = AgentBenchmarkWorkflow(root).run(development=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = AgentBenchmarkWorkflow(root).run(development=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
