import json
from pathlib import Path

import pytest

from biointerfaceos.paper_b_workflow import PaperBError, PaperBWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_paper_b_generates_method_draft_and_resumes(tmp_path: Path) -> None:
    workflow = PaperBWorkflow(_root(), output_root=tmp_path / "paper_b")
    first = workflow.run()
    assert first.release_id == "bioif-data-model-dev-v1.0.0"
    assert first.data_layers == 2
    assert first.model_layers == 2
    assert first.ablations == 5
    assert first.ood_rows == 12
    assert first.claims == 8
    assert first.tables == 6
    assert first.figures == 5
    assert first.evidence_inputs == 15
    assert first.style_passed is True
    assert first.resumed == 0

    manuscript = (tmp_path / "paper_b" / "paper_b.md").read_text()
    claims = json.loads((tmp_path / "paper_b" / "claim_matrix.json").read_text())
    audit = json.loads((tmp_path / "paper_b" / "style_audit.json").read_text())
    assert "paired module ablations" in manuscript
    assert "causal decomposition" in manuscript
    assert "protected test values" in manuscript
    assert len(claims["claims"]) == 8
    assert claims["claims"][0]["claim_id"] == "M1"
    assert audit["status"] == "PASS"
    assert audit["observed"]["over_40_word_sentences"] == 0

    second = workflow.run()
    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()


def test_paper_b_rejects_input_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/manuscripts/paper_b_fixture.json").read_text())
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(PaperBError, match="checksum differs"):
        PaperBWorkflow(_root(), fixture_path=fixture_path, output_root=tmp_path / "paper_b").run()


def test_paper_b_rejects_tampered_artifact(tmp_path: Path) -> None:
    workflow = PaperBWorkflow(_root(), output_root=tmp_path / "paper_b")
    workflow.run()
    path = tmp_path / "paper_b" / "paper_b.md"
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(PaperBError, match="immutable Paper B artifact differs"):
        workflow.run()
