import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "review_round_4" / "R4_T295_NON_DOI_PHASE_ACCEPTANCE_AUDIT_20260815.json"


def test_t295_accepts_author_side_phase_but_not_strong_q1_gate():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    assert audit["author_side_phase_accepted"] is True
    assert audit["strong_q1_accepted"] is False
    assert audit["doi_and_github_deferred_by_user"] is True
    assert audit["full_review_round_4_tests"]["passed"] == 105
    assert audit["full_review_round_4_tests"]["failed"] == 0
    assert audit["gate_state"]["verified_lockbox_receipt_count"] == 0
    assert audit["gate_state"]["verified_no_author_reproduction_count"] == 0
    assert audit["gate_state"]["verified_distinct_adoption_receipt_count"] == 0
    assert audit["gate_state"]["scientific_submission_ready"] is False
