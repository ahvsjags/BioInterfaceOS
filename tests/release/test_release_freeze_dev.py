import json
from pathlib import Path

import pytest

from biointerfaceos.release_freeze_dev import (
    DevelopmentReleaseFreezeError,
    DevelopmentReleaseFreezeWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_development_release_freeze_is_immutable_and_resumable(tmp_path: Path) -> None:
    workflow = DevelopmentReleaseFreezeWorkflow(_root(), output_root=tmp_path / "release")
    first = workflow.run()
    assert first.release_id == "bioif-data-model-dev-v1.0.0"
    assert first.input_count == 11
    assert first.data_layers == 2
    assert first.model_layers == 2
    assert first.thresholds == 6
    assert first.license_layers_separated is True
    assert first.negative_controls_clean is True
    assert first.resumed == 0

    manifest = json.loads((tmp_path / "release" / "release_manifest.json").read_text())
    card = (tmp_path / "release" / "data_model_card.md").read_text()
    assert manifest["immutable"] is True
    assert manifest["target_values_exposed"] is False
    assert manifest["license_layers"]["locked_targets"] == "not_included_locked_targets"
    assert "hidden_target" not in json.dumps(manifest)
    assert "analysis-only" in card

    second = workflow.run()
    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()


def test_development_release_freeze_rejects_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/release/freeze_dev_fixture.json").read_text())
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(DevelopmentReleaseFreezeError, match="checksum differs"):
        DevelopmentReleaseFreezeWorkflow(
            _root(), fixture_path=fixture_path, output_root=tmp_path / "release"
        ).run()


def test_development_release_freeze_rejects_tampered_artifact(tmp_path: Path) -> None:
    workflow = DevelopmentReleaseFreezeWorkflow(_root(), output_root=tmp_path / "release")
    workflow.run()
    path = tmp_path / "release" / "data_model_card.md"
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(DevelopmentReleaseFreezeError, match="immutable artifact differs"):
        workflow.run()
