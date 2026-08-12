import json
from pathlib import Path

from biointerfaceos.reproducibility_agent_workflow import ReproducibilityWorkflow


def test_reproducibility_rebuild_and_lockbox_gates_pass() -> None:
    root = Path(__file__).parents[2]
    summary = ReproducibilityWorkflow(root).run(fixture=True)

    assert summary.release_verified is True
    assert summary.rebuild_clean is True
    assert summary.hash_match is True
    assert summary.lockbox_activation_blocked is True
    assert summary.training_methods_exposed is False
    assert summary.selected_pipeline == "reproducibility_agent"
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert receipt["target_values_exposed"] is False


def test_reproducibility_keeps_evaluator_metadata_only() -> None:
    root = Path(__file__).parents[2]
    ReproducibilityWorkflow(root).run(fixture=True)

    activation = json.loads(
        (root / "reports/agents/reproducibility/lockbox_activation_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert activation["active"] is False
    assert activation["reason"] == "SIGNED_FREEZE_REQUIRED"
    capabilities = json.loads(
        (root / "reports/agents/reproducibility/evaluator_capabilities.json").read_text(
            encoding="utf-8"
        )
    )
    assert capabilities["training_methods_exposed"] is False
    assert "train" not in capabilities["capabilities"]


def test_reproducibility_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = ReproducibilityWorkflow(root).run(fixture=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = ReproducibilityWorkflow(root).run(fixture=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
