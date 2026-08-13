"""Regression tests for the leakage-controlled T193 execution."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
    R4T193ThreeLabPrefrozenExecutionWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def _repo_test_output(name: str) -> Path:
    path = ROOT / "reports/review_round_4" / name
    if path.exists():
        shutil.rmtree(path)
    return path


def test_t193_prefrozen_execution_verifies_and_closes_outputs() -> None:
    output_root = _repo_test_output(".t193_test_execution")
    try:
        workflow = R4T193ThreeLabPrefrozenExecutionWorkflow(ROOT, output_root=output_root)

        summary = workflow.run(strict=True)

        assert summary.observation_count == 1495
        assert summary.target_universe_count == 99
        assert summary.laboratory_anchor_count == 3
        assert summary.measurement_batch_count == 85
        assert summary.model_count == 3
        assert workflow.verify() == summary

        report = json.loads((output_root / "t193_three_lab_execution_report.json").read_text())
        assert report["target_universe"]["selection_after_outer_split"] is False
        assert report["scientific_submission_ready"] is False
        assert len(report["model_results"]) == 9
    finally:
        shutil.rmtree(output_root, ignore_errors=True)


def test_t193_prefrozen_ledger_is_row_traceable_and_flags_ambiguity() -> None:
    output_root = _repo_test_output(".t193_test_ledger")
    try:
        workflow = R4T193ThreeLabPrefrozenExecutionWorkflow(ROOT, output_root=output_root)
        workflow.run(strict=True)

        path = output_root / "source_local_prefrozen_target_ledger.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))

        assert len(rows) == 1495
        assert all(row["prefrozen_target_universe_member"] == "true" for row in rows)
        assert all(row["cross_source_scale_use"] == "PROHIBITED" for row in rows)
        assert any(row["multi_accession_group_flag"] == "true" for row in rows)
        assert {row["laboratory_anchor"] for row in rows} == {
            "Dalian University of Technology, China",
            "University College Dublin / Conway Institute",
            "University of Edinburgh-led controlled human exposure study",
        }
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
