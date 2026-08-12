import json
from pathlib import Path

import pytest

from biointerfaceos.benchmark_instances import BenchmarkBuildError, BenchmarkInstanceWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_benchmark_build_validates_families_and_target_isolation(tmp_path: Path) -> None:
    summary = BenchmarkInstanceWorkflow(_root(), output_root=tmp_path / "instances").run()

    assert summary.instances == 16
    assert summary.families == 8
    assert summary.primary_families == 8
    assert summary.pilot_families == 0
    assert summary.train == 8
    assert summary.validation == 8
    assert summary.resumed == 0

    public = json.loads((tmp_path / "instances" / "public_instances.json").read_text())
    hidden = json.loads((tmp_path / "instances" / "hidden_target_registry.json").read_text())
    assert public["target_values_exposed"] is False
    assert hidden["target_values_exposed"] is False
    assert len(public["instances"]) == len(hidden["targets"]) == 16
    assert all("hidden_target_sha256" not in row for row in public["instances"])
    assert all("target" not in json.dumps(row).lower() for row in public["instances"])


def test_benchmark_build_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = BenchmarkInstanceWorkflow(_root(), output_root=tmp_path / "instances")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_benchmark_build_requires_dev_fixture(tmp_path: Path) -> None:
    workflow = BenchmarkInstanceWorkflow(_root(), output_root=tmp_path / "instances")
    with pytest.raises(BenchmarkBuildError, match="--dev is required"):
        workflow.run(dev=False)
    with pytest.raises(BenchmarkBuildError, match="--fixture is required"):
        workflow.run(fixture=False)
