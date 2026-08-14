"""Regression tests for the T192 redistributable three-laboratory target audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.r4_t192_three_lab_common_target import (
    R4T192ThreeLabCommonTargetError,
    R4T192ThreeLabCommonTargetWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t192_three_lab_common_target_runs_and_verifies(tmp_path: Path) -> None:
    workflow = R4T192ThreeLabCommonTargetWorkflow(ROOT, output_root=tmp_path / "audit")

    summary = workflow.run(strict=True)

    assert summary.source_count == 3
    assert summary.laboratory_anchor_count == 3
    assert summary.common_target_count == 9
    assert summary.common_row_count == 809
    assert summary.source_cell_count == 2486
    assert summary.rank_eligible_cell_count == 1495
    assert summary.source_batch_counts == {
        "EDINBURGH_DS7545_HUMAN_PLASMA_NANOOMICS": 49,
        "PXD060795_DALIAN_PLA_MICRO_NANOPLASTIC_HUMAN_PLASMA_CORONA": 6,
        "PXD064962_UCD_EVENT": 30,
    }
    assert workflow.verify() == summary


def test_t192_rejects_tampered_protocol_hash(tmp_path: Path) -> None:
    registry = ROOT / "docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json"
    text = registry.read_text(encoding="utf-8").replace(
        "d1fa58c85324c6c9062cf5e6185a74c7814f8b567e66453d41a10c9d9c03a968", "0" * 64
    )
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(text, encoding="utf-8")
    workflow = R4T192ThreeLabCommonTargetWorkflow(ROOT, registry_path=registry_copy, output_root=tmp_path / "audit")

    with pytest.raises(R4T192ThreeLabCommonTargetError, match="T192 protocol checksum differs"):
        workflow.run(strict=True)
