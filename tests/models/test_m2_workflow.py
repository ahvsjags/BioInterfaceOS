import json
from pathlib import Path

import pytest

from biointerfaceos.m2_workflow import M2Error, M2Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m2_fit_reports_ood_calibration_importance_and_id_audit(tmp_path: Path) -> None:
    summary = M2Workflow(_root(), output_root=tmp_path / "m2").run()

    assert summary.instances == 16
    assert summary.train == 8
    assert summary.validation == 8
    assert summary.model_kind == "regularized_polynomial_fallback"
    assert summary.validation_rmse >= 0.0
    assert summary.resumed == 0

    results = json.loads((tmp_path / "m2" / "m2_results.json").read_text())
    assert results["target_values_exposed"] is False
    assert results["validation_metrics"]["instances"] == 8
    assert len(results["group_metrics"]) == 1
    audit = json.loads((tmp_path / "m2" / "feature_audit.json").read_text())
    assert audit["identifier_features_used"] is False
    assert audit["validation_used_for_tuning"] is False
    importance = json.loads((tmp_path / "m2" / "feature_importance.json").read_text())
    assert len(importance["features"]) == 4
    calibration = json.loads((tmp_path / "m2" / "calibration.json").read_text())
    assert calibration["uncertainty_source"] == "train_residual_sd"


def test_m2_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = M2Workflow(_root(), output_root=tmp_path / "m2")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_m2_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(M2Error, match="--fixture is required"):
        M2Workflow(_root(), output_root=tmp_path / "m2").run(fixture=False)
