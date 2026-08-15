import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF = ROOT / "docs" / "data" / "R4_T286_CURRENT_EXTERNAL_HANDOFF_20260815.json"


def test_t286_points_external_participants_to_current_immutable_candidate():
    payload = json.loads(HANDOFF.read_text(encoding="utf-8"))

    assert payload["protocol_id"] == "bioif-r4-t286-external-gate-handoff-v1.0.0"
    assert payload["fixed_release"]["tag"] == "v0.1.3-r10.57"
    assert payload["fixed_release"]["tag_target"] == "3557fac2019e57fd8968cdcf55b106750eafa750"
    assert payload["fixed_release"]["source_commit"] == "0d4467a"
    assert payload["fixed_release"]["manifest_sha256"] == (
        "a3b6b7c90eb4964e8bef0649d04b819e19ff12f7b2a3da31ea510330f1919d0e"
    )
    assert payload["fixed_release"]["manifest_path"].endswith("r10.57/release_manifest.json")
    assert payload["fixed_release"]["clean_room_helper"].endswith("r10_57.sh")
    assert payload["receipt_template"].endswith("R4_T286_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE_20260815.json")
    assert "preflight-r4-t286-external-receipts" in payload["receipt_preflight_command"]
    assert payload["required_external_receipts"]["protected_lockbox_evaluator"] == 1
    assert payload["required_external_receipts"]["no_author_scientific_reproduction"] == 1
    assert payload["required_external_receipts"]["distinct_external_user_adoption"] == 2
    assert payload["gate_state"]["verified_lockbox_receipt_count"] == 0
    assert payload["gate_state"]["verified_no_author_reproduction_count"] == 0
    assert payload["gate_state"]["verified_distinct_adoption_receipt_count"] == 0
    assert payload["gate_state"]["doi_archive_verified"] is False
    assert payload["gate_state"]["scientific_submission_ready"] is False
