import json
from pathlib import Path

from biointerfaceos.functional_axes_workflow import FunctionalAxesWorkflow


def test_functional_axes_compares_alternatives_and_emits_uncertainty() -> None:
    root = Path(__file__).parents[2]
    summary = FunctionalAxesWorkflow(root).run(fixture=True)

    assert summary.samples == 4
    assert summary.modules == 2
    assert summary.alternatives == 3
    assert summary.candidate_axes == 2
    assert summary.bootstrap_stability == 0.93
    assert summary.leave_study_stability == 0.90
    assert summary.random_control_stability == 0.22
    assert summary.uncertainty_records == 2
    assert summary.selected_model == "log_ratio"
    assert summary.lockbox_clean is True

    candidates = json.loads((root / "reports/omics/functional_axes/candidate_axes.json").read_text(encoding="utf-8"))
    assert all(row["status"] == "EXPLORATORY_CANDIDATE" for row in candidates["axes"])
    enrichment = json.loads(
        (root / "reports/omics/functional_axes/pathway_enrichment.json").read_text(encoding="utf-8")
    )
    assert enrichment["causal_claim"] is False


def test_functional_axes_random_controls_and_stability_are_recorded() -> None:
    root = Path(__file__).parents[2]
    FunctionalAxesWorkflow(root).run(fixture=True)

    stability = json.loads((root / "reports/omics/functional_axes/stability_report.json").read_text(encoding="utf-8"))
    assert stability["random_control_passed"] is True
    assert stability["bootstrap_replicates"] == 8
    assert len(stability["leave_study_folds"]) == 2
    lockbox = json.loads((root / "reports/omics/functional_axes/lockbox_scan.json").read_text(encoding="utf-8"))
    assert lockbox["clean"] is True
    assert lockbox["locked_payload_opened"] is False


def test_functional_axes_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = FunctionalAxesWorkflow(root).run(fixture=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = FunctionalAxesWorkflow(root).run(fixture=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
