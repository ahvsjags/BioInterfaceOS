import json
from pathlib import Path

import pytest

from biointerfaceos.paper_a_workflow import PaperAError, PaperAWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_paper_a_generates_evidence_linked_draft_and_resumes(tmp_path: Path) -> None:
    workflow = PaperAWorkflow(_root(), output_root=tmp_path / "paper_a")
    first = workflow.run()
    assert first.release_id == "biointerfacebench-dev-v1.0.0"
    assert first.instances == 16
    assert first.families == 8
    assert first.train == 8
    assert first.validation == 8
    assert first.claims == 8
    assert first.tables == 6
    assert first.figures == 5
    assert first.evidence_inputs == 18
    assert first.style_passed is True
    assert first.resumed == 0

    manuscript = (tmp_path / "paper_a" / "paper_a.md").read_text()
    claims = json.loads((tmp_path / "paper_a" / "claim_matrix.json").read_text())
    manifest = json.loads((tmp_path / "paper_a" / "paper_a_manifest.json").read_text())
    figures = json.loads((tmp_path / "paper_a" / "figure_manifest.json").read_text())
    audit = json.loads((tmp_path / "paper_a" / "style_audit.json").read_text())
    assert "BioInterfaceBench" in manuscript
    assert "hidden_target_sha256" not in manuscript.lower()
    assert "no locked target values" in manuscript.lower()
    assert "independent studies" not in manuscript.lower()
    assert claims["claims"][0]["claim_id"] == "E1"
    assert claims["evidence_class"] == "FIXTURE_TEST"
    assert claims["allowed_claim_level"] == "CONTRACT_TEST"
    assert manifest["evidence_class"] == "FIXTURE_TEST"
    assert figures["allowed_claim_level"] == "CONTRACT_TEST"
    assert len(claims["claims"]) == 8
    assert audit["status"] == "PASS"
    assert audit["observed"]["over_40_word_sentences"] == 0

    second = workflow.run()
    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()


def test_paper_a_rejects_input_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/manuscripts/paper_a_fixture.json").read_text())
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(PaperAError, match="checksum differs"):
        PaperAWorkflow(_root(), fixture_path=fixture_path, output_root=tmp_path / "paper_a").run()


def test_paper_a_rejects_tampered_artifact(tmp_path: Path) -> None:
    workflow = PaperAWorkflow(_root(), output_root=tmp_path / "paper_a")
    workflow.run()
    path = tmp_path / "paper_a" / "paper_a.md"
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(PaperAError, match="immutable Paper A artifact differs"):
        workflow.run()
