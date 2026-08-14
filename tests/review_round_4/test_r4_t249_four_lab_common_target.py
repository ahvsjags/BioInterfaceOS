"""Regression tests for the T249 four-source paper-data common target."""

from __future__ import annotations

from pathlib import Path

from biointerfaceos.r4_t249_four_lab_common_target import R4T249FourLabCommonTargetWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_t249_run_and_verify(tmp_path: Path) -> None:
    output_root = tmp_path / "t249"
    workflow = R4T249FourLabCommonTargetWorkflow(ROOT, output_root=output_root)
    summary = workflow.run(strict=True)
    assert (summary.source_count, summary.laboratory_anchor_count) == (4, 4)
    assert summary.common_target_count == 7
    assert summary.common_row_count == 783
    verified = workflow.verify()
    assert verified.common_row_count == summary.common_row_count
