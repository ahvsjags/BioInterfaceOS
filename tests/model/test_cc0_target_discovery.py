"""Tests for the strict T129 CC0 target-discovery expansion workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.cc0_target_discovery import (
    CC0TargetDiscoveryError,
    CC0TargetDiscoveryWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_audit_records_expansion_without_promoting_a_target(tmp_path: Path) -> None:
    workflow = CC0TargetDiscoveryWorkflow(ROOT, output_root=tmp_path / "discovery")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.candidate_source_count == 2
    assert summary.candidate_laboratory_count == 1
    assert summary.screened_asset_count == 7
    assert receipt["status"] == "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES"
    assert receipt["target_status"] == "NOT_FROZEN"
    assert receipt["model_fitted"] is False


def test_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = CC0TargetDiscoveryWorkflow(ROOT, output_root=tmp_path / "discovery")

    with pytest.raises(CC0TargetDiscoveryError, match="requires --strict"):
        workflow.run()


def test_audit_rejects_silent_candidate_promotion(tmp_path: Path) -> None:
    registry = json.loads((ROOT / "docs/data/R2_T129_CC0_TARGET_DISCOVERY_REGISTRY.json").read_text(encoding="utf-8"))
    registry["candidates"][0]["numeric_covariate_map_status"] = "SOURCE_MATCHED"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = CC0TargetDiscoveryWorkflow(
        ROOT,
        registry_path=registry_path,
        output_root=tmp_path / "discovery",
    )

    with pytest.raises(CC0TargetDiscoveryError, match="silently promotes a target"):
        workflow.run(strict=True)


def test_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = CC0TargetDiscoveryWorkflow(ROOT, output_root=tmp_path / "discovery")
    workflow.run(strict=True)
    decision = tmp_path / "discovery" / "target_discovery_decision.json"
    decision.chmod(0o600)
    decision.write_text('{"model_fitted":true}\n', encoding="utf-8")

    with pytest.raises(CC0TargetDiscoveryError, match="receipt is invalid"):
        workflow.verify()
