import json
from pathlib import Path

from biointerfaceos.mediation_workflow import MediationWorkflow


def test_mediation_workflow_preserves_estimands_and_downgrades_language(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = MediationWorkflow(root, output_root=tmp_path / "mediation")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.rows == 12
    assert first.development_rows == 8
    assert first.replication_rows == 4
    assert first.study_clusters == 4
    assert first.estimands == 4
    assert first.alternative_mediators == 2
    assert first.dag_scenarios == 3
    assert first.cluster_bootstrap_records == 64
    assert first.replication_attempted is True
    assert first.replication_passed is True
    assert first.causal_claim_permitted is False
    assert first.language_status == "ASSOCIATION_ONLY"
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False
    assert receipt["causal_claim_permitted"] is False


def test_mediation_outputs_include_clustered_uncertainty_and_controls(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = MediationWorkflow(root, output_root=tmp_path / "mediation")
    workflow.run(fixture=True)

    uncertainty = json.loads(
        (tmp_path / "mediation" / "cluster_uncertainty.json").read_text(encoding="utf-8")
    )
    controls = json.loads(
        (tmp_path / "mediation" / "mediator_controls.json").read_text(encoding="utf-8")
    )
    language = json.loads(
        (tmp_path / "mediation" / "language_gate.json").read_text(encoding="utf-8")
    )
    assert uncertainty["cluster_field"] == "study_id"
    assert uncertainty["cluster_resampling"] is True
    assert uncertainty["primary"]["replicates"] == 32
    assert controls["random_control_not_used_for_selection"] is True
    assert language["status"] == "ASSOCIATION_ONLY"
    assert "causes" in language["blocked_wording"]
