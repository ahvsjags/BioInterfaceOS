"""Regression tests for the T250 four-source execution."""

from __future__ import annotations

import shutil
from pathlib import Path

from biointerfaceos.r4_t250_four_lab_common_target_execution import (
    R4T250FourLabCommonTargetExecutionWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t250_execution_receipt_closes_real_model_run() -> None:
    output_root = ROOT / ".tmp-t250-test"
    shutil.rmtree(output_root, ignore_errors=True)
    try:
        workflow = R4T250FourLabCommonTargetExecutionWorkflow(ROOT, output_root=output_root)
        summary = workflow.run(strict=True)
        assert (summary.observation_count, summary.target_universe_count) == (783, 7)
        assert (summary.laboratory_anchor_count, summary.measurement_batch_count) == (4, 115)
        assert summary.model_count == 3
        assert workflow.verify() == summary
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
