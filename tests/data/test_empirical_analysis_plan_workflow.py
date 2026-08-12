"""Tests for the outcome-free T121 empirical analysis-plan gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.empirical_analysis_plan_workflow import (
    EmpiricalAnalysisPlanError,
    EmpiricalAnalysisPlanWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_analysis_plan_freezes_rules_without_outcome_analysis(tmp_path: Path) -> None:
    workflow = EmpiricalAnalysisPlanWorkflow(ROOT, output_root=tmp_path / "analysis_plan")

    summary = workflow.run(strict=True)
    frozen_plan = workflow.verify()

    assert summary.estimand_count == 2
    assert summary.available_development_estimands == 1
    assert summary.unavailable_held_out_estimands == 1
    assert frozen_plan["scope"] == "DEVELOPMENT_ONLY"
    assert frozen_plan["split_manifest"]["held_out_source_ids"] == []
    assert frozen_plan["model_selection"]["inner_selection"] == "NESTED_GROUP_CV"


def test_analysis_plan_requires_strict_mode(tmp_path: Path) -> None:
    workflow = EmpiricalAnalysisPlanWorkflow(ROOT, output_root=tmp_path / "analysis_plan")

    with pytest.raises(EmpiricalAnalysisPlanError, match="requires --strict"):
        workflow.run()


def test_analysis_plan_rejects_outcome_or_performance_fields(tmp_path: Path) -> None:
    plan = json.loads((ROOT / "data/empirical/R2_ANALYSIS_PLAN.json").read_text(encoding="utf-8"))
    plan["mean"] = 0.0
    plan_path = tmp_path / "outcome_bearing_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    workflow = EmpiricalAnalysisPlanWorkflow(
        ROOT,
        plan_path=plan_path,
        output_root=tmp_path / "analysis_plan",
    )

    with pytest.raises(EmpiricalAnalysisPlanError, match="contains an outcome"):
        workflow.run(strict=True)
