import json
import tarfile
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.r2_release_reproduction_workflow import (
    R2ReleaseReproductionError,
    R2ReleaseReproductionWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_r2_release_replays_only_registered_public_source_in_clean_worktree(tmp_path: Path) -> None:
    output = tmp_path / "r2-replay"
    workflow = R2ReleaseReproductionWorkflow(_root(), output_root=output)

    receipt = workflow.run(strict=True)

    assert receipt["status"] == "PASS_R2_SOFTWARE_REPLAY"
    assert receipt["software_replay"] is True
    assert receipt["scientific_reproduction"] is False
    assert receipt["scientific_submission_ready"] is False
    assert workflow.verify()["rebuilt_protocol_figures"] == 3
    source_manifest = _json(output / "source_manifest.json")
    assert source_manifest["scope"] == "R2_PUBLIC_SOFTWARE_REPLAY_SOURCE"
    paths = {row["path"] for row in source_manifest["files"]}
    assert R2ReleaseReproductionWorkflow.REQUIRED_PUBLIC_PATHS <= paths
    assert not any(
        path.startswith(("data/", "registry/", "reports/", "release/")) for path in paths
    )
    clean_replay = _json(output / "clean_replay.json")
    assert clean_replay["source_mode"] == "temporary_public_source_only"
    assert clean_replay["nested_status"] == "PASS_R2_SOFTWARE_REPLAY"
    with tarfile.open(output / "r2_public_source.tar.gz", "r:gz") as archive:
        names = set(archive.getnames())
    assert "source/docs/figures/R2_FIGURE_SPECS.json" in names
    assert "source_manifest.json" in names


def test_r2_release_is_one_shot_and_detects_tampering(tmp_path: Path) -> None:
    output = tmp_path / "r2-replay"
    workflow = R2ReleaseReproductionWorkflow(_root(), output_root=output)
    workflow.run(strict=True)

    with pytest.raises(R2ReleaseReproductionError, match="already executed"):
        workflow.run(strict=True)
    junit = output / "junit.xml"
    junit.chmod(0o644)
    junit.write_text("tampered", encoding="utf-8")
    with pytest.raises(R2ReleaseReproductionError, match="output hash"):
        workflow.verify()
