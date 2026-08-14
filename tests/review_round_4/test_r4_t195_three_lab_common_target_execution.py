"""Regression tests for the strict T192 common-target execution."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from biointerfaceos.r4_t195_three_lab_common_target_execution import (
    R4T195ThreeLabCommonTargetExecutionWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def _output_root(name: str) -> Path:
    path = ROOT / "reports/review_round_4" / name
    shutil.rmtree(path, ignore_errors=True)
    return path


def test_t195_common_target_execution_verifies_and_closes_outputs() -> None:
    output_root = _output_root(".t195_test_execution")
    try:
        workflow = R4T195ThreeLabCommonTargetExecutionWorkflow(ROOT, output_root=output_root)

        summary = workflow.run(strict=True)

        assert summary.observation_count == 809
        assert summary.target_universe_count == 9
        assert summary.laboratory_anchor_count == 3
        assert summary.measurement_batch_count == 85
        assert summary.model_count == 3
        assert workflow.verify() == summary

        report = json.loads((output_root / "t195_three_lab_execution_report.json").read_text(encoding="utf-8"))
        assert report["target_universe"]["source"] == ("R4_T192_THREE_LAB_COMMON_TARGET_REGISTRY")
        assert report["target_universe"]["count"] == 9
        assert report["scientific_submission_ready"] is False
    finally:
        shutil.rmtree(output_root, ignore_errors=True)


def test_t195_ledger_contains_only_frozen_common_targets() -> None:
    output_root = _output_root(".t195_test_ledger")
    try:
        workflow = R4T195ThreeLabCommonTargetExecutionWorkflow(ROOT, output_root=output_root)
        workflow.run(strict=True)

        with (output_root / "source_local_prefrozen_target_ledger.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))

        assert len(rows) == 809
        assert {row["canonical_accession"] for row in rows} == {
            "P04004",
            "P04264",
            "P05556",
            "P06396",
            "P07996",
            "P26038",
            "P60174",
            "Q04695",
            "Q9HDC9",
        }
        assert all(row["cross_source_scale_use"] == "PROHIBITED" for row in rows)
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
