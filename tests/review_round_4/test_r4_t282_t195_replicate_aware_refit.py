"""Regression tests for the T282 replicate-aware T195 primary route."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from biointerfaceos.r4_t282_t195_replicate_aware_refit import (
    R4T282T195ReplicateAwareRefitWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t282_collapses_replicates_before_primary_route_execution() -> None:
    output_root = ROOT / "reports/review_round_4/.t282_test_execution"
    shutil.rmtree(output_root, ignore_errors=True)
    try:
        workflow = R4T282T195ReplicateAwareRefitWorkflow(ROOT, output_root=output_root)
        summary = workflow.run(strict=True)
        assert summary.observation_count == 644
        assert summary.target_universe_count == 9
        assert summary.laboratory_anchor_count == 3
        assert summary.measurement_batch_count == 85
        assert workflow.verify() == summary

        with (output_root / "technical_replicate_collapse_trace.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            trace = list(csv.DictReader(stream))
        assert len(trace) == 165
        receipt = json.loads(
            (output_root / "t282_t195_replicate_aware_refit_receipt.json").read_text(encoding="utf-8")
        )
        assert receipt["raw_observation_count"] == 809
        assert receipt["collapsed_group_count"] == 165
        assert receipt["scientific_submission_ready"] is False
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
