import json
from pathlib import Path

import pytest

from biointerfaceos.benchmark_representations import (
    BenchmarkRepresentationError,
    BenchmarkRepresentationWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_representation_baselines_report_coverage_and_full_split_metrics(tmp_path: Path) -> None:
    summary = BenchmarkRepresentationWorkflow(_root(), output_root=tmp_path / "representations").run()

    assert summary.baselines == 4
    assert summary.successful == 4
    assert summary.validation_instances == 8
    assert summary.best_rmse >= 0.0
    assert summary.resumed == 0

    results = json.loads((tmp_path / "representations" / "representation_results.json").read_text())
    assert results["target_values_exposed"] is False
    assert {row["baseline"] for row in results["baselines"]} == {
        "descriptor",
        "fingerprint",
        "text",
        "polymer_embedding",
    }
    for baseline in results["baselines"]:
        assert baseline["coverage"]["full_split_primary"] is True
        assert baseline["coverage"]["missingness_indicator_used"] is True
        assert len(baseline["family_metrics"]) == 8

    coverage = json.loads((tmp_path / "representations" / "coverage_audit.json").read_text())
    assert coverage["complete_case_not_primary"] is True
    assert coverage["structure_missing_fraction"] > 0.0
    assert coverage["baselines"]["text"]["validation_coverage"] == 1.0
    assert coverage["baselines"]["descriptor"]["validation_coverage"] < 1.0


def test_representation_baselines_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = BenchmarkRepresentationWorkflow(_root(), output_root=tmp_path / "representations")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_representation_baselines_require_group(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkRepresentationError, match="--group representation is required"):
        BenchmarkRepresentationWorkflow(_root(), output_root=tmp_path / "representations").run(group="simple")
