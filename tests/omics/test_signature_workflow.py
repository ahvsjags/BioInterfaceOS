import json
from pathlib import Path

import pytest

from biointerfaceos.signature_workflow import SignatureWorkflow, SignatureWorkflowError


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_signature_workflow_separates_families_and_audits_stability(tmp_path: Path) -> None:
    summary = SignatureWorkflow(_root(), output_root=tmp_path / "signatures").run()

    assert summary.studies == 3
    assert summary.samples == 12
    assert summary.signatures == 3
    assert summary.scores == 36
    assert 0 <= summary.stable_folds <= summary.total_folds == 9

    registry = json.loads((tmp_path / "signatures" / "signature_registry.json").read_text(encoding="utf-8"))
    assert {row["family"] for row in registry["signatures"]} == {"predefined", "data_driven"}
    leakage = json.loads((tmp_path / "signatures" / "leakage_audit.json").read_text(encoding="utf-8"))
    assert leakage["feature_selection_uses_outcome_labels"] is False
    assert leakage["status"] == "PASSED"


def test_signature_workflow_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = SignatureWorkflow(_root(), output_root=tmp_path / "signatures")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_signature_workflow_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(SignatureWorkflowError, match="--fixture is required"):
        SignatureWorkflow(_root(), output_root=tmp_path / "signatures").run(fixture=False)
