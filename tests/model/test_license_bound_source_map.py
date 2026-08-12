"""Regression tests for the strict T130 licence/source-map boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.license_bound_source_map import (
    LicenseBoundSourceMapError,
    LicenseBoundSourceMapWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_audit_preserves_cc0_boundary_and_analysis_only_map(tmp_path: Path) -> None:
    workflow = LicenseBoundSourceMapWorkflow(ROOT, output_root=tmp_path / "source-maps")

    summary = workflow.run(strict=True)
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))

    assert summary.route_count == 3
    assert summary.independent_laboratory_count == 3
    assert summary.analysis_only_complete_map_count == 1
    assert receipt["status"] == "BLOCKED_NO_PUBLIC_CROSS_STUDY_NUMERIC_MATERIAL_TARGET"
    assert receipt["public_redistributable_complete_map_count"] == 0
    assert receipt["target_status"] == "NOT_FROZEN"
    assert workflow.verify() == summary


def test_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = LicenseBoundSourceMapWorkflow(ROOT, output_root=tmp_path / "source-maps")

    with pytest.raises(LicenseBoundSourceMapError, match="requires --strict"):
        workflow.run()


def test_audit_rejects_license_tampering(tmp_path: Path) -> None:
    registry = json.loads(
        (ROOT / "docs/data/R2_T130_LICENSE_BOUND_SOURCE_MAP_REGISTRY.json").read_text(
            encoding="utf-8"
        )
    )
    registry["routes"][0]["mapping_evidence"]["license_id"] = "CC0-1.0"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = LicenseBoundSourceMapWorkflow(
        ROOT,
        registry_path=registry_path,
        output_root=tmp_path / "source-maps",
    )

    with pytest.raises(LicenseBoundSourceMapError, match="licence classification"):
        workflow.run(strict=True)


def test_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = LicenseBoundSourceMapWorkflow(ROOT, output_root=tmp_path / "source-maps")
    summary = workflow.run(strict=True)
    summary.receipt_path.chmod(0o600)
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    receipt["model_use"] = "ALLOWED"
    summary.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(LicenseBoundSourceMapError, match="receipt is invalid"):
        workflow.verify()
