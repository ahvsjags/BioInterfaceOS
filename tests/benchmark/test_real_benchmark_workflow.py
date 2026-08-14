"""Tests for the real, study-held-out source-locator benchmark."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.real_benchmark_workflow import RealBenchmarkError, RealBenchmarkWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_real_benchmark_uses_three_held_out_studies(tmp_path: Path) -> None:
    workflow = RealBenchmarkWorkflow(ROOT, output_root=tmp_path / "real_benchmark")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.study_count == 3
    assert summary.laboratory_count == 3
    assert summary.item_count == 3
    assert summary.prediction_count == 3
    assert receipt["held_out_groups"] is True
    assert receipt["raw_predictions_published"] is True
    assert receipt["independent_validation"] is False
    assert receipt["scientific_submission_ready"] is False


def test_real_benchmark_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RealBenchmarkWorkflow(ROOT, output_root=tmp_path / "real_benchmark")

    with pytest.raises(RealBenchmarkError, match="requires --strict"):
        workflow.run()


def test_real_benchmark_rejects_insufficient_independent_studies(tmp_path: Path) -> None:
    registry = json.loads((ROOT / "data/empirical/R2_BENCHMARK_SOURCE_REGISTRY.json").read_text(encoding="utf-8"))
    registry["sources"].pop()
    registry_path = tmp_path / "insufficient_studies.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = RealBenchmarkWorkflow(
        ROOT,
        registry_path=registry_path,
        output_root=tmp_path / "real_benchmark",
    )

    with pytest.raises(RealBenchmarkError, match="at least three sources"):
        workflow.run(strict=True)
