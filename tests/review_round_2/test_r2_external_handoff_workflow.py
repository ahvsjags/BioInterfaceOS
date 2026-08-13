"""Regression tests for the R2 external-evidence handoff boundary."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from biointerfaceos.r2_external_handoff_workflow import (
    R2ExternalHandoffError,
    R2ExternalHandoffWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_r2_external_handoff_audit_is_intake_only(tmp_path: Path) -> None:
    workflow = R2ExternalHandoffWorkflow(ROOT, output_root=tmp_path / "handoff")

    summary = workflow.run(strict=True)

    assert summary.status == "READY_FOR_EXTERNAL_SOURCE_INTAKE"
    assert summary.source_intake_field_count == 6
    assert summary.analysis_unit_field_count == 11
    assert {
        "external_source_intake_template",
        "external_verification_bundle_template",
    } <= set(R2ExternalHandoffWorkflow.REFERENCES)
    assert workflow.verify() == summary


def test_r2_external_handoff_requires_strict_mode(tmp_path: Path) -> None:
    workflow = R2ExternalHandoffWorkflow(ROOT, output_root=tmp_path / "handoff")

    with pytest.raises(R2ExternalHandoffError, match="requires --strict"):
        workflow.run()


def test_r2_external_handoff_rejects_weakened_source_intake(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    required = [
        R2ExternalHandoffWorkflow.HANDOFF_RELATIVE,
        *[relative for relative, _ in R2ExternalHandoffWorkflow.REFERENCES.values()],
    ]
    for relative in required:
        source = ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    package_path = root / R2ExternalHandoffWorkflow.HANDOFF_RELATIVE
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["source_intake"]["mandatory_identity_fields"].remove("laboratory_affiliation")
    package_path.write_text(json.dumps(package), encoding="utf-8")

    workflow = R2ExternalHandoffWorkflow(root, output_root=root / "handoff")

    with pytest.raises(R2ExternalHandoffError, match="source identity fields"):
        workflow.run(strict=True)


def test_r2_external_handoff_rejects_fabricated_external_result(tmp_path: Path) -> None:
    output_root = tmp_path / "handoff"
    workflow = R2ExternalHandoffWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    receipt_path = output_root / "external_evidence_handoff_receipt.json"
    receipt_path.chmod(0o600)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["external_reproduction_verified"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(R2ExternalHandoffError, match="receipt is invalid"):
        workflow.verify()
