import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = (
    ROOT
    / "reports"
    / "review_round_4"
    / "t290_paper_ood_uncertainty"
    / "v1.0.0"
    / "t290_paper_ood_uncertainty_report.json"
)


def test_t290_records_route_native_estimands_and_external_boundaries():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    routes = {row["route_id"]: row for row in report["routes"]}

    assert report["route_count"] == 6
    assert report["supported_positive_count"] == 3
    assert report["supported_negative_count"] == 2
    assert report["indeterminate_count"] == 1
    assert report["pooling_prohibited"] is True
    assert report["independent_validation"] is False
    assert report["external_scientific_reproduction"] is False
    assert report["scientific_submission_ready"] is False
    assert routes["T203_PMC10257194"]["metric_name"] == "mean_batch_spearman"
    assert routes["T203_PMC10257194"]["cluster_unit"] == "measurement_batch_id"
    assert routes["T209_MANCHESTER"]["metric_name"] == "subject_equal_mean_spearman"
    assert routes["T209_MANCHESTER"]["cluster_unit"] == "biological_unit_id"
    assert routes["T181_PXD017052"]["metric_name"] == "subject_equal_mean_spearman"
    assert all(row["bootstrap_resamples"] == 2000 for row in routes.values())
    assert all(row["source_predictions_sha256"] for row in routes.values())
