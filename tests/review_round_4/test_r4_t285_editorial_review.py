import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs" / "review_round_4" / "R4_T285_POST_T284_MULTI_AGENT_EDITORIAL_REVIEW_20260815.json"


def test_t285_role_panel_keeps_model_score_and_hard_gates_evidence_bound():
    payload = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert payload["panel_type"] == "evidence_bound_role_panel_not_real_external_reviewers"
    assert payload["scorecard"]["data_compatibility_and_sample_foundation"] >= 90
    assert payload["scorecard"]["statistical_analysis_design"] >= 90
    assert payload["scorecard"]["statistical_execution_and_effective_sample"] >= 90
    assert payload["scorecard"]["models_ablation_ood_uncertainty"] == 88
    assert payload["t284_effect_summary"]["positive_effect_count"] == 3
    assert payload["t284_effect_summary"]["negative_effect_count"] == 3
    assert payload["t284_effect_summary"]["near_zero_effect_count"] == 3
    assert payload["hard_gates"]["verified_lockbox_receipt_count"] == 0
    assert payload["hard_gates"]["verified_no_author_reproduction_count"] == 0
    assert payload["hard_gates"]["verified_distinct_adoption_receipt_count"] == 0
    assert payload["hard_gates"]["doi_archive_verified"] is False
    assert payload["hard_gates"]["scientific_submission_ready"] is False
