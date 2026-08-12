import json
from pathlib import Path

import pytest

from biointerfaceos.multimodal_workflow import MultimodalError, MultimodalWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_multimodal_masks_missingness_and_blocks_leakage(tmp_path: Path) -> None:
    summary = MultimodalWorkflow(_root(), output_root=tmp_path / "multimodal").run()

    assert summary.rows == 12
    assert summary.train == 8
    assert summary.validation == 4
    assert summary.modalities == 5
    assert summary.selected_model == "material_protocol_masked"
    assert summary.leakage_passed is True
    assert summary.missingness_masked is True
    assert summary.resumed == 0

    leakage = json.loads((tmp_path / "multimodal" / "leakage_audit.json").read_text())
    missingness = json.loads((tmp_path / "multimodal" / "missingness_audit.json").read_text())
    assert leakage["source_identity_leakage_passed"] is True
    assert leakage["outcome_text_leakage_passed"] is True
    assert missingness["all_missingness_masked"] is True


def test_multimodal_compares_fusion_and_ood_persistence(tmp_path: Path) -> None:
    MultimodalWorkflow(_root(), output_root=tmp_path / "multimodal").run()

    comparison = json.loads((tmp_path / "multimodal" / "model_comparison.json").read_text())
    ood = json.loads((tmp_path / "multimodal" / "ood_evaluation.json").read_text())
    assert len(comparison["models"]) == 7
    assert "single_text" in comparison["models"]
    assert "fusion" in comparison["models"]
    assert comparison["fusion_gain_persists_ood"] is False
    assert ood["gain_persists"] is False


def test_multimodal_resume_is_deterministic_and_requires_fixture(tmp_path: Path) -> None:
    workflow = MultimodalWorkflow(_root(), output_root=tmp_path / "multimodal")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before
    with pytest.raises(MultimodalError, match="--fixture is required"):
        workflow.run(fixture=False)
