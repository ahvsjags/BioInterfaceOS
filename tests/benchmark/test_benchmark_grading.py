import json
from pathlib import Path

import pytest

from biointerfaceos.benchmark_grading import BenchmarkGradeError, BenchmarkGradingWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_grader_scores_perfect_wrong_and_abstain_controls(tmp_path: Path) -> None:
    summary = BenchmarkGradingWorkflow(_root(), output_root=tmp_path / "grading").run()

    assert summary.cases == 3
    assert summary.instances == 16
    assert summary.perfect_accuracy == 1.0
    assert summary.wrong_accuracy == 0.0
    assert summary.abstain_coverage == 0.0
    assert summary.resumed == 0

    metrics = json.loads((tmp_path / "grading" / "metrics.json").read_text())
    assert metrics["cases"]["perfect"]["overall"]["calibration_error"] == 0.0
    assert metrics["cases"]["perfect"]["split_metrics"]
    assert len(metrics["cases"]["perfect"]["family_metrics"]) == 8
    assert metrics["cases"]["wrong"]["overall"]["accuracy"] == 0.0
    assert metrics["cases"]["abstain"]["overall"]["coverage"] == 0.0
    assert metrics["cases"]["abstain"]["overall"]["abstained"] == 16
    scores = json.loads((tmp_path / "grading" / "instance_scores.json").read_text())
    assert scores["target_values_exposed"] is False
    assert all("target" not in row for case in scores["cases"] for row in case["scores"])


def test_grader_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = BenchmarkGradingWorkflow(_root(), output_root=tmp_path / "grading")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_grader_rejects_invalid_case_and_requires_fixture(tmp_path: Path) -> None:
    fixture_path = tmp_path / "bad_grading_fixture.json"
    fixture = json.loads((_root() / "tests/fixtures/benchmark/grading_fixture.json").read_text())
    fixture["cases"][0]["mode"] = "leaked-target"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(BenchmarkGradeError, match="unknown grading case mode"):
        BenchmarkGradingWorkflow(_root(), fixture_path=fixture_path, output_root=tmp_path / "bad").run()
    with pytest.raises(BenchmarkGradeError, match="--fixture is required"):
        BenchmarkGradingWorkflow(_root(), output_root=tmp_path / "grading").run(fixture=False)
