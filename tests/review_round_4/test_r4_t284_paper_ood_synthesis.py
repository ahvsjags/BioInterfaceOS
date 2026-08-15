import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = (
    ROOT / "reports" / "review_round_4" / "t284_paper_ood_synthesis" / "v1.0.0" / "t284_paper_ood_synthesis_report.json"
)
RECEIPT = (
    ROOT
    / "reports"
    / "review_round_4"
    / "t284_paper_ood_synthesis"
    / "v1.0.0"
    / "t284_paper_ood_synthesis_receipt.json"
)


def test_t284_keeps_route_heterogeneity_and_external_gates_explicit():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert report["route_count"] == 9
    assert report["positive_effect_count"] == 3
    assert report["negative_effect_count"] == 3
    assert report["near_zero_effect_count"] == 3
    assert report["pooling_prohibited"] is True
    assert report["independent_validation"] is False
    assert report["external_scientific_reproduction"] is False
    assert report["scientific_submission_ready"] is False
    assert receipt["report_sha256"]
    assert receipt["route_count"] == 9
