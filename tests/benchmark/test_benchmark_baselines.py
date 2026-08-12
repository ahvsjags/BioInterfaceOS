import json
from pathlib import Path

import pytest

from biointerfaceos.benchmark_baselines import (
    BenchmarkBaselineError,
    BenchmarkBaselineWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_simple_baselines_run_with_grouped_metrics_and_intervals(tmp_path: Path) -> None:
    summary = BenchmarkBaselineWorkflow(_root(), output_root=tmp_path / "baselines").run()

    assert summary.baselines == 5
    assert summary.successful == 5
    assert summary.validation_instances == 8
    assert summary.best_rmse >= 0.0
    assert summary.resumed == 0

    results = json.loads((tmp_path / "baselines" / "baseline_results.json").read_text())
    assert results["target_values_exposed"] is False
    assert {row["baseline"] for row in results["baselines"]} == {
        "mean",
        "family_mean",
        "knn",
        "linear",
        "mixed_effect",
    }
    for baseline in results["baselines"]:
        assert baseline["seed"] == 17
        assert len(baseline["family_metrics"]) == 8
        assert (
            baseline["primary_ood_confidence_interval"][0]
            <= baseline["primary_ood_confidence_interval"][1]
        )
        assert baseline["missingness"]["missingness_indicator_used"] is True

    audit = json.loads((tmp_path / "baselines" / "feature_audit.json").read_text())
    assert audit["identifier_features_excluded"] is True
    assert "evidence_locator" in audit["excluded_fields"]


def test_simple_baselines_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = BenchmarkBaselineWorkflow(_root(), output_root=tmp_path / "baselines")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_simple_baselines_require_group(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkBaselineError, match="--group simple is required"):
        BenchmarkBaselineWorkflow(_root(), output_root=tmp_path / "baselines").run(
            group="representation"
        )
