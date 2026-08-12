import json
from pathlib import Path

import pytest

from biointerfaceos.m5_workflow import M5Error, M5Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m5_g3_gate_uses_constrained_kinetic_fallback(tmp_path: Path) -> None:
    summary = M5Workflow(_root(), output_root=tmp_path / "m5").run()

    assert summary.trajectories == 3
    assert summary.train_trajectories == 2
    assert summary.validation_trajectories == 1
    assert summary.model_kind == "discrete_kinetics"
    assert summary.sufficiency_passed is False
    assert summary.validation_rmse >= 0.0
    assert summary.resumed == 0

    sufficiency = json.loads((tmp_path / "m5" / "sufficiency_gate.json").read_text())
    assert sufficiency["high_capacity_neural_ode"] == "WAIVED"
    assert sufficiency["fallback_used"] is True
    constraints = json.loads((tmp_path / "m5" / "trajectory_constraints.json").read_text())
    assert constraints["all_prediction_simplex_valid"] is True
    leave_study_out = json.loads((tmp_path / "m5" / "leave_study_out.json").read_text())
    assert leave_study_out["folds_count"] == 2
    toy = json.loads((tmp_path / "m5" / "toy_recovery.json").read_text())
    assert toy["status"] == "PASSED"


def test_m5_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = M5Workflow(_root(), output_root=tmp_path / "m5")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_m5_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(M5Error, match="--fixture is required"):
        M5Workflow(_root(), output_root=tmp_path / "m5").run(fixture=False)
