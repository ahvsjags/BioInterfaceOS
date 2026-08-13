"""Regression tests for the bounded two-laboratory source-pair screen."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.two_lab_corona_pair_rescreen import (
    TwoLabCoronaPairRescreenError,
    TwoLabCoronaPairRescreenWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_pair_rescreen_records_two_labs_without_target_promotion(tmp_path: Path) -> None:
    workflow = TwoLabCoronaPairRescreenWorkflow(ROOT, output_root=tmp_path / "pair")

    summary = workflow.run(strict=True)

    assert summary.candidate_source_count == 2
    assert summary.independent_laboratory_count == 2
    assert summary.candidate_size_count == 2
    assert (
        summary.status == "BLOCKED_PAIR_ASSET_LICENCE_UNIT_MAP_AND_SHARED_ENDPOINT_AUDIT_REQUIRED"
    )
    assert workflow.verify() == summary


def test_pair_rescreen_requires_strict_mode(tmp_path: Path) -> None:
    workflow = TwoLabCoronaPairRescreenWorkflow(ROOT, output_root=tmp_path / "pair")

    with pytest.raises(TwoLabCoronaPairRescreenError, match="requires --strict"):
        workflow.run()


def test_pair_rescreen_rejects_candidate_promotion(tmp_path: Path) -> None:
    registry = json.loads(
        (ROOT / "docs/data/R2_T129_TWO_LAB_CORONA_PAIR_REGISTRY.json").read_text(encoding="utf-8")
    )
    registry["candidates"][0]["admission"] = "ADMITTED"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = TwoLabCoronaPairRescreenWorkflow(
        ROOT,
        registry_path=registry_path,
        output_root=tmp_path / "pair",
    )

    with pytest.raises(TwoLabCoronaPairRescreenError, match="silently promoted"):
        workflow.run(strict=True)


def test_pair_rescreen_rejects_weakened_policy(tmp_path: Path) -> None:
    registry = json.loads(
        (ROOT / "docs/data/R2_T129_TWO_LAB_CORONA_PAIR_REGISTRY.json").read_text(encoding="utf-8")
    )
    registry["source_policy"]["cc0_cohort_unchanged"] = False
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = TwoLabCoronaPairRescreenWorkflow(
        ROOT,
        registry_path=registry_path,
        output_root=tmp_path / "pair",
    )

    with pytest.raises(TwoLabCoronaPairRescreenError, match="policy is weakened"):
        workflow.run(strict=True)


def test_pair_rescreen_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = TwoLabCoronaPairRescreenWorkflow(ROOT, output_root=tmp_path / "pair")
    workflow.run(strict=True)
    report_path = tmp_path / "pair" / "pair_rescreen_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["model_use"] = "ALLOWED"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(TwoLabCoronaPairRescreenError, match="receipt is invalid"):
        workflow.verify()
