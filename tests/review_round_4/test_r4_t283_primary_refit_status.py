import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "data" / "R4_T283_POST_T282_PRIMARY_REFIT_STATUS_20260815.json"


def test_t283_records_t282_primary_refit_and_keeps_external_gates_closed():
    payload = json.loads(STATUS.read_text(encoding="utf-8"))

    assert payload["primary_route"]["task_id"] == "T195"
    assert payload["t282"]["raw_observations"] == 809
    assert payload["t282"]["collapsed_observations"] == 644
    assert payload["t282"]["collapsed_groups"] == 165
    assert payload["t282"]["cross_environment_artifact_hashes_match"] is True
    assert payload["scorecard"]["data_compatibility_and_sample_foundation"] >= 90
    assert payload["scorecard"]["statistical_analysis_design"] >= 90
    assert payload["scorecard"]["statistical_execution_and_effective_sample"] >= 90
    assert payload["all_module_90_acceptance"]["verified_lockbox_receipt_count"] == 0
    assert payload["all_module_90_acceptance"]["verified_no_author_reproduction_count"] == 0
    assert payload["all_module_90_acceptance"]["verified_distinct_adoption_receipt_count"] == 0
    assert payload["all_module_90_acceptance"]["doi_archive_verified"] is False
    assert payload["all_module_90_acceptance"]["scientific_submission_ready"] is False
