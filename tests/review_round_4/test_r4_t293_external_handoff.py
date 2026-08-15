from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "docs" / "external" / "R4_T286_CURRENT_EXTERNAL_HANDOFF_20260815.md"
TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "independent-reproduction.yml"
SELF_SERVICE = ROOT / "docs" / "external" / "R4_T293_SELF_SERVICE_EXTERNAL_REPRODUCTION_20260815.md"


def test_t293_external_handoff_uses_current_preflight_pointer_and_preserves_gate_boundary():
    handoff = HANDOFF.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")
    self_service = SELF_SERVICE.read_text(encoding="utf-8")

    assert "aebbcdca8d88a432080227501f8821716ee788e6" in handoff
    assert "57f3435" not in handoff
    assert "aebbcdca8d88a432080227501f8821716ee788e6" in template
    assert "verified_no_author_reproduction_count=0" in handoff
    assert "scientific_submission_ready=false" in handoff
    assert "independently reacquire" in self_service
    assert "author-controlled KAUST replay" in self_service
    assert "signed aggregate receipt" in self_service
