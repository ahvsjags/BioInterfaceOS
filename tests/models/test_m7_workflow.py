import json
from pathlib import Path

import pytest

from biointerfaceos.m7_workflow import M7Error, M7Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m7_enforces_domains_budget_and_ood_fallback(tmp_path: Path) -> None:
    summary = M7Workflow(_root(), output_root=tmp_path / "m7").run()

    assert summary.rows == 16
    assert summary.train == 8
    assert summary.validation == 8
    assert summary.domain_definitions == 2
    assert summary.selected_model == "hierarchical_erm"
    assert summary.leakage_passed is True
    assert summary.ood_rmse >= 0.0
    assert summary.resumed == 0

    comparison = json.loads((tmp_path / "m7" / "model_comparison.json").read_text())
    assert comparison["identical_tuning_budget"] is True
    assert comparison["fallback_used"] is True
    audit = json.loads((tmp_path / "m7" / "domain_audit.json").read_text())
    assert audit["label_leakage_passed"] is True
    assert audit["validation_domains_unseen_in_train"] is True


def test_m7_reports_two_domain_definitions_and_ood_metrics(tmp_path: Path) -> None:
    M7Workflow(_root(), output_root=tmp_path / "m7").run()

    audit = json.loads((tmp_path / "m7" / "domain_audit.json").read_text())
    ood = json.loads((tmp_path / "m7" / "ood_evaluation.json").read_text())
    assert {item["field"] for item in audit["definitions"]} == {
        "study_domain",
        "protocol_domain",
    }
    assert ood["held_out_domain_count"] == 2
    assert "hierarchical_erm_rmse" in ood
    assert "best_alternative_rmse" in ood


def test_m7_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = M7Workflow(_root(), output_root=tmp_path / "m7")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(M7Error, match="--fixture is required"):
        workflow.run(fixture=False)
