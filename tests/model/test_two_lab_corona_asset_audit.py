"""Regression tests for the non-admitting first-party asset audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.two_lab_corona_asset_audit import (
    TwoLabCoronaAssetAuditError,
    TwoLabCoronaAssetAuditWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_asset_audit_records_page_metadata_without_promoting_files(tmp_path: Path) -> None:
    workflow = TwoLabCoronaAssetAuditWorkflow(ROOT, output_root=tmp_path / "assets")

    summary = workflow.run(strict=True)

    assert summary.asset_count == 5
    assert summary.source_count == 2
    assert summary.byte_verified_count == 0
    assert summary.redistributable_count == 0
    assert (
        summary.status
        == "BLOCKED_FIRST_PARTY_BYTES_LICENCE_UNIT_MAP_AND_SHARED_ENDPOINT_REQUIRED"
    )
    assert workflow.verify() == summary


def test_asset_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = TwoLabCoronaAssetAuditWorkflow(ROOT, output_root=tmp_path / "assets")

    with pytest.raises(TwoLabCoronaAssetAuditError, match="requires --strict"):
        workflow.run()


def test_asset_audit_rejects_byte_promotion(tmp_path: Path) -> None:
    registry = json.loads(
        (ROOT / "docs/data/R2_T140_SUPPLEMENT_ASSET_AUDIT_REGISTRY.json").read_text(
            encoding="utf-8"
        )
    )
    registry["assets"][0]["byte_verified"] = True
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = TwoLabCoronaAssetAuditWorkflow(
        ROOT, registry_path=registry_path, output_root=tmp_path / "assets"
    )

    with pytest.raises(TwoLabCoronaAssetAuditError, match="silently promoted"):
        workflow.run(strict=True)


def test_asset_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = TwoLabCoronaAssetAuditWorkflow(ROOT, output_root=tmp_path / "assets")
    workflow.run(strict=True)
    report_path = tmp_path / "assets" / "asset_audit_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["model_use"] = "ALLOWED"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(TwoLabCoronaAssetAuditError, match="receipt is invalid"):
        workflow.verify()
