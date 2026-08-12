import json
from pathlib import Path

import pytest

from biointerfaceos.m3_workflow import M3Error, M3Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m3_fit_audits_pairs_controls_and_associational_status(tmp_path: Path) -> None:
    summary = M3Workflow(_root(), output_root=tmp_path / "m3").run()

    assert summary.pairs == 16
    assert summary.train == 8
    assert summary.validation == 8
    assert summary.identification_status == "ASSOCIATIONAL_ONLY"
    assert summary.direct_rmse >= 0.0
    assert summary.mediated_rmse >= 0.0
    assert summary.resumed == 0

    pairing = json.loads((tmp_path / "m3" / "pairing_audit.json").read_text())
    assert pairing["unique_pair_ids"] == 16
    assert pairing["cross_split_pairs"] == 0
    identification = json.loads((tmp_path / "m3" / "identification_audit.json").read_text())
    assert identification["status"] == "ASSOCIATIONAL_ONLY"
    assert identification["causal_claim_permitted"] is False
    comparison = json.loads((tmp_path / "m3" / "m3_comparison.json").read_text())
    assert comparison["random_mediator"]["metrics"]["instances"] == 8
    uncertainty = json.loads((tmp_path / "m3" / "uncertainty_propagation.json").read_text())
    assert uncertainty["propagation"] == "quadrature"


def test_m3_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = M3Workflow(_root(), output_root=tmp_path / "m3")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_m3_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(M3Error, match="--fixture is required"):
        M3Workflow(_root(), output_root=tmp_path / "m3").run(fixture=False)
