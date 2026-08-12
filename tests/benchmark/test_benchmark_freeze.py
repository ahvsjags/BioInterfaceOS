import json
from pathlib import Path

import pytest

from biointerfaceos.benchmark_freeze import BenchmarkFreezeError, BenchmarkFreezeWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_benchmark_freeze_is_versioned_separated_and_resumable(tmp_path: Path) -> None:
    workflow = BenchmarkFreezeWorkflow(_root(), output_root=tmp_path / "release")
    first = workflow.run()

    assert first.release_id == "biointerfacebench-dev-v1.0.0"
    assert first.instances == 16
    assert first.train == 8
    assert first.validation == 8
    assert first.graders == 3
    assert first.baselines == 5
    assert first.representations == 4
    assert first.public_hidden_separated is True
    assert first.negative_controls_clean is True
    assert first.resumed == 0

    manifest = json.loads((tmp_path / "release" / "release_manifest.json").read_text())
    card = (tmp_path / "release" / "benchmark_card.md").read_text()
    assert manifest.get("immutable", True)
    assert manifest["target_values_exposed"] is False
    assert "hidden_target_sha256" not in json.dumps(manifest)
    assert "target values remain inaccessible" in card

    second = workflow.run()
    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()


def test_benchmark_freeze_rejects_input_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/benchmark/freeze_dev_fixture.json").read_text())
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(BenchmarkFreezeError, match="checksum differs"):
        BenchmarkFreezeWorkflow(
            _root(), fixture_path=fixture_path, output_root=tmp_path / "release"
        ).run()


def test_benchmark_freeze_never_overwrites_a_release(tmp_path: Path) -> None:
    workflow = BenchmarkFreezeWorkflow(_root(), output_root=tmp_path / "release")
    workflow.run()
    path = tmp_path / "release" / "benchmark_card.md"
    path.write_text("mutated", encoding="utf-8")
    with pytest.raises(BenchmarkFreezeError, match="immutable release artifact differs"):
        workflow.run()
