"""Regression tests for the three-laboratory common-target admission audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.r4_three_lab_common_target_audit import (
    R4ThreeLabCommonTargetAuditError,
    R4ThreeLabCommonTargetAuditWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/data/R4_T178_THREE_LAB_COMMON_TARGET_ADMISSION.json"


def test_three_lab_common_target_audit_runs_and_verifies(tmp_path: Path) -> None:
    workflow = R4ThreeLabCommonTargetAuditWorkflow(ROOT, output_root=tmp_path / "audit")

    summary = workflow.run(strict=True)

    assert summary.source_count == 3
    assert summary.laboratory_anchor_count == 3
    assert summary.common_target_count == 99
    assert summary.common_rank_observation_count == 2724
    assert summary.selected_source_row_count == 3431
    assert summary.measurement_batch_count == 47
    assert summary.source_cell_count == 20469
    assert workflow.verify() == summary


def test_three_lab_common_target_audit_rejects_tampered_map_declaration(tmp_path: Path) -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["sources"][0]["source_cell_map"]["sha256"] = "0" * 64
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = R4ThreeLabCommonTargetAuditWorkflow(ROOT, registry_path=registry_path, output_root=tmp_path / "audit")

    with pytest.raises(R4ThreeLabCommonTargetAuditError, match="source-cell map checksum differs"):
        workflow.run(strict=True)
