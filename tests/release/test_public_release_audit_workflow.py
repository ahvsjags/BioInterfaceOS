from pathlib import Path

import pytest

from biointerfaceos.public_release_audit_workflow import (
    PublicReleaseAuditError,
    PublicReleaseAuditWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_strict_public_release_audit_tracks_all_repository_assets(tmp_path: Path) -> None:
    workflow = PublicReleaseAuditWorkflow(_root(), output_root=tmp_path / "public-audit")
    report = workflow.run(strict=True)

    assert report["status"] == "PASS_PUBLIC_RELEASE_AUDIT"
    assert report["asset_count"] > 0
    assert report["redistribution_counts"]["PUBLIC"] > 0
    assert report["redistribution_counts"]["EXCLUDED"] > 0
    assert report["historical_fixture_bundle_publicly_released"] is False
    assert report["scientific_submission_ready"] is False
    assert workflow.verify()["status"] == "PASS_PUBLIC_RELEASE_AUDIT"


def test_public_release_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = PublicReleaseAuditWorkflow(_root(), output_root=tmp_path / "public-audit")
    with pytest.raises(PublicReleaseAuditError, match="--strict"):
        workflow.run()
