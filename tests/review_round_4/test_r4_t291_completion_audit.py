import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "review_round_4" / "R4_T291_FULL_OBJECTIVE_COMPLETION_AUDIT_20260815.json"


def test_t291_keeps_external_gates_open_until_real_receipts_exist():
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    assert audit["status"] == "INCOMPLETE_EXTERNAL_GATES_OPEN"
    assert audit["scientific_submission_ready"] is False
    assert audit["scores"]["models_ood_uncertainty"] == 89
    assert audit["scores"]["descriptive_mean"] == 47.125
    assert audit["gate_state"]["verified_lockbox_receipt_count"] == 0
    assert audit["gate_state"]["verified_no_author_reproduction_count"] == 0
    assert audit["gate_state"]["verified_distinct_adoption_receipt_count"] == 0
    assert audit["gate_state"]["doi_archive_verified"] is False
    assert len(audit["missing_external_artifacts"]) == 5
