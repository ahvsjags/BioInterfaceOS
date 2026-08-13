"""Regression tests for the full-text core-facility portability execution."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from biointerfaceos.r4_t194_fulltext_core_facility_execution import (
    R4T194FulltextCoreFacilityExecutionWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def _repo_test_output(name: str) -> Path:
    path = ROOT / "reports/review_round_4" / name
    if path.exists():
        shutil.rmtree(path)
    return path


def test_t194_fulltext_execution_verifies_and_closes_outputs() -> None:
    output_root = _repo_test_output(".t194_test_execution")
    try:
        workflow = R4T194FulltextCoreFacilityExecutionWorkflow(ROOT, output_root=output_root)
        summary = workflow.run(strict=True)
        assert summary.observation_count == 707
        assert summary.target_universe_count == 99
        assert summary.core_facility_count == 12
        assert summary.measurement_batch_count == 12
        assert summary.model_count == 3
        assert workflow.verify() == summary
        report = json.loads(
            (output_root / "t194_fulltext_core_facility_execution_report.json").read_text()
        )
        assert report["source_semantics"]["biological_unit_count"] == 1
        assert report["scientific_submission_ready"] is False
        assert len(report["model_results"]) == 36
        assert report["core_cluster_bootstrap"]["SEQUENCE_RIDGE_FULL"]["cluster_count"] == 12
    finally:
        shutil.rmtree(output_root, ignore_errors=True)


def test_t194_ledger_is_row_traceable_and_marks_common_aliquot() -> None:
    output_root = _repo_test_output(".t194_test_ledger")
    try:
        workflow = R4T194FulltextCoreFacilityExecutionWorkflow(ROOT, output_root=output_root)
        workflow.run(strict=True)
        path = output_root / "fulltext_core_prefrozen_target_ledger.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 707
        assert all(row["prefrozen_target_universe_member"] == "true" for row in rows)
        assert all(row["cross_source_scale_use"] == "PROHIBITED" for row in rows)
        assert all(row["biological_unit_id"] == "PMC9633814:COMMON_POOLED_HUMAN_PLASMA_ALIQUOT" for row in rows)
        assert len({row["laboratory_anchor"] for row in rows}) == 12
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
