import json
from pathlib import Path

import pytest

from biointerfaceos.uncertainty_workflow import UncertaintyError, UncertaintyWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_uncertainty_calibration_and_conservative_fallback(tmp_path: Path) -> None:
    summary = UncertaintyWorkflow(_root(), output_root=tmp_path / "uncertainty").run()

    assert summary.rows == 12
    assert summary.calibration == 6
    assert summary.validation == 6
    assert summary.selected_model == "conservative_conformal"
    assert summary.calibration_passed is False
    assert summary.coverage == 0.5
    assert summary.selective_risk_decreases is True
    assert summary.ood_abstentions == 2
    assert summary.resumed == 0

    calibration = json.loads((tmp_path / "uncertainty" / "calibration_audit.json").read_text())
    assert {item["domain"] for item in calibration["domain_calibration"]} == {
        "DOMAIN_A",
        "DOMAIN_B",
        "DOMAIN_C_OOD",
    }


def test_uncertainty_selective_risk_and_ood_policy(tmp_path: Path) -> None:
    UncertaintyWorkflow(_root(), output_root=tmp_path / "uncertainty").run()

    selective = json.loads((tmp_path / "uncertainty" / "selective_risk.json").read_text())
    ood = json.loads((tmp_path / "uncertainty" / "ood_detection.json").read_text())
    policy = json.loads((tmp_path / "uncertainty" / "abstention_policy.json").read_text())
    risks = [record["selective_rmse"] for record in selective["curve"]]
    assert selective["risk_decreases_with_abstention"] is True
    assert risks == sorted(risks, reverse=True)
    assert ood["ood_policy_passed"] is True
    assert ood["overconfident_ood_ids"] == []
    assert policy["overconfident_ood_rejected"] is True


def test_uncertainty_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = UncertaintyWorkflow(_root(), output_root=tmp_path / "uncertainty")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(UncertaintyError, match="--fixture is required"):
        workflow.run(fixture=False)
