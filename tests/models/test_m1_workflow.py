import json
from pathlib import Path

import pytest

from biointerfaceos.m1_workflow import M1Error, M1Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m1_fit_reports_diagnostics_variance_and_toy_recovery(tmp_path: Path) -> None:
    summary = M1Workflow(_root(), output_root=tmp_path / "m1").run()

    assert summary.instances == 16
    assert summary.train == 8
    assert summary.validation == 8
    assert summary.converged is True
    assert summary.toy_recovery is True
    assert summary.validation_rmse >= 0.0
    assert summary.resumed == 0

    diagnostics = json.loads((tmp_path / "m1" / "diagnostics.json").read_text())
    assert diagnostics["converged"] is True
    assert diagnostics["identity_features_used"] is False
    variance = json.loads((tmp_path / "m1" / "variance_partition.json").read_text())
    assert set(variance["groups"]) == {"study", "protocol", "material"}
    grouped_cv = json.loads((tmp_path / "m1" / "m1_results.json").read_text())["grouped_cv"]
    assert grouped_cv["all_groups_held_out"] is True
    assert grouped_cv["folds_count"] == 4
    toy = json.loads((tmp_path / "m1" / "toy_recovery.json").read_text())
    assert toy["recovered"] is True


def test_m1_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = M1Workflow(_root(), output_root=tmp_path / "m1")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_m1_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(M1Error, match="--fixture is required"):
        M1Workflow(_root(), output_root=tmp_path / "m1").run(fixture=False)
