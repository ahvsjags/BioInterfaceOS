import json
from pathlib import Path

import pytest

from biointerfaceos.paper_c_prelock_workflow import PaperCPrelockError, PaperCPrelockWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_paper_c_prelock_freezes_candidates_and_resumes(tmp_path: Path) -> None:
    workflow = PaperCPrelockWorkflow(_root(), output_root=tmp_path / "paper_c_prelock")
    first = workflow.run()
    assert first.candidate_count == 5
    assert first.strong_candidates == 2
    assert first.analyses == 5
    assert first.predictions == 5
    assert first.claims == 8
    assert first.tables == 6
    assert first.figures == 5
    assert first.evidence_inputs == 8
    assert first.style_passed is True
    assert first.lockbox_accessed is False
    assert first.resumed == 0

    manuscript = (tmp_path / "paper_c_prelock" / "paper_c_prelock.md").read_text()
    predictions = json.loads((tmp_path / "paper_c_prelock" / "prediction_table.json").read_text())
    audit = json.loads((tmp_path / "paper_c_prelock" / "style_audit.json").read_text())
    assert "PREDICTED_BEFORE_LOCKBOX" in json.dumps(predictions)
    assert "protected payloads" in manuscript
    assert "universal biological laws" in manuscript
    assert audit["status"] == "PASS"
    assert audit["observed"]["over_40_word_sentences"] == 0

    second = workflow.run()
    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()


def test_paper_c_prelock_rejects_input_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads(
        (_root() / "tests/fixtures/manuscripts/paper_c_prelock_fixture.json").read_text()
    )
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(PaperCPrelockError, match="checksum differs"):
        PaperCPrelockWorkflow(
            _root(), fixture_path=fixture_path, output_root=tmp_path / "paper_c_prelock"
        ).run()


def test_paper_c_prelock_rejects_tampered_artifact(tmp_path: Path) -> None:
    workflow = PaperCPrelockWorkflow(_root(), output_root=tmp_path / "paper_c_prelock")
    workflow.run()
    path = tmp_path / "paper_c_prelock" / "paper_c_prelock.md"
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(PaperCPrelockError, match="immutable Paper C artifact differs"):
        workflow.run()
