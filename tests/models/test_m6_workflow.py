import json
from pathlib import Path

import pytest

from biointerfaceos.m6_workflow import M6Error, M6Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m6_audits_identification_and_downgrades_language(tmp_path: Path) -> None:
    summary = M6Workflow(_root(), output_root=tmp_path / "m6").run()

    assert summary.rows == 12
    assert summary.train == 8
    assert summary.validation == 4
    assert summary.overlap_passed is True
    assert summary.causal_claim_permitted is False
    assert summary.validation_rmse >= 0.0
    assert summary.resumed == 0

    estimands = json.loads((tmp_path / "m6" / "estimand_card.json").read_text())
    assert estimands["causal_ate"]["status"] == "NONIDENTIFIED"
    language = json.loads((tmp_path / "m6" / "language_policy.json").read_text())
    assert language["allowed_label"] == "PREDICTIVE_ASSOCIATIONAL_ONLY"
    assert language["causal_claim_permitted"] is False


def test_m6_writes_alternative_dags_and_sensitivity(tmp_path: Path) -> None:
    M6Workflow(_root(), output_root=tmp_path / "m6").run()

    dags = json.loads((tmp_path / "m6" / "alternative_dags.json").read_text())
    sensitivity = json.loads((tmp_path / "m6" / "confounding_sensitivity.json").read_text())
    assert len(dags["cards"]) == 3
    assert len(sensitivity["bias_strengths"]) == 4
    assert all(card["identification"] == "NONIDENTIFIED" for card in dags["cards"])


def test_m6_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = M6Workflow(_root(), output_root=tmp_path / "m6")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(M6Error, match="--fixture is required"):
        workflow.run(fixture=False)
