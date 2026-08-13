"""Regression tests for the bounded, fail-closed T129 CC0 rescreen."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.cc0_target_rescreen import (
    CC0TargetRescreenError,
    CC0TargetRescreenWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_rescreen_records_small_official_assets_without_target_promotion(tmp_path: Path) -> None:
    workflow = CC0TargetRescreenWorkflow(ROOT, output_root=tmp_path / "rescreen")

    summary = workflow.run(strict=True)

    assert summary.candidate_source_count == 2
    assert summary.disclosed_laboratory_count == 0
    assert summary.screened_asset_count == 7
    assert workflow.verify() == summary


def test_rescreen_requires_strict_mode(tmp_path: Path) -> None:
    workflow = CC0TargetRescreenWorkflow(ROOT, output_root=tmp_path / "rescreen")

    with pytest.raises(CC0TargetRescreenError, match="requires --strict"):
        workflow.run()


def test_rescreen_rejects_numeric_covariate_promotion(tmp_path: Path) -> None:
    registry = json.loads(
        (ROOT / "docs/data/R2_T129_CC0_RESCREEN_REGISTRY.json").read_text(encoding="utf-8")
    )
    registry["candidates"][0]["numeric_covariate_map_status"] = "SOURCE_MATCHED_NUMERIC"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = CC0TargetRescreenWorkflow(
        ROOT,
        registry_path=registry_path,
        output_root=tmp_path / "rescreen",
    )

    with pytest.raises(CC0TargetRescreenError, match="silently promotes a target"):
        workflow.run(strict=True)


def test_rescreen_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = CC0TargetRescreenWorkflow(ROOT, output_root=tmp_path / "rescreen")
    summary = workflow.run(strict=True)
    summary.receipt_path.chmod(0o600)
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    receipt["model_use"] = "ALLOWED"
    summary.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(CC0TargetRescreenError, match="receipt is invalid"):
        workflow.verify()
