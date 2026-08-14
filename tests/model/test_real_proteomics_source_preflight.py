"""Tests for the strict T123 real proteomics source preflight."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.real_proteomics_source_preflight import (
    RealProteomicsSourcePreflightError,
    RealProteomicsSourcePreflightWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_preflight_records_sources_without_promoting_a_target(tmp_path: Path) -> None:
    workflow = RealProteomicsSourcePreflightWorkflow(ROOT, output_root=tmp_path / "preflight")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.source_count == 3
    assert summary.source_defined_unit_count == 30
    assert receipt["status"] == "READY_FOR_STAGED_RAW_ACQUISITION_NOT_A_MODEL_TARGET"
    assert receipt["target_status"] == "NOT_FROZEN"
    assert receipt["model_fitted"] is False


def test_preflight_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RealProteomicsSourcePreflightWorkflow(ROOT, output_root=tmp_path / "preflight")

    with pytest.raises(RealProteomicsSourcePreflightError, match="requires --strict"):
        workflow.run()


def test_preflight_rejects_target_promotion_in_registry(tmp_path: Path) -> None:
    registry = json.loads((ROOT / "docs/data/R2_T123_PROTEOMICS_SOURCE_PREFLIGHT.json").read_text(encoding="utf-8"))
    registry["preprocessing_contract"]["model_use"] = "ALLOWED"
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = RealProteomicsSourcePreflightWorkflow(ROOT, registry_path=path, output_root=tmp_path / "preflight")

    with pytest.raises(RealProteomicsSourcePreflightError, match="silently promotes"):
        workflow.run(strict=True)


def test_preflight_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = RealProteomicsSourcePreflightWorkflow(ROOT, output_root=tmp_path / "preflight")
    workflow.run(strict=True)
    decision = tmp_path / "preflight" / "source_preflight_decision.json"
    decision.chmod(0o600)
    decision.write_text('{"model_fitted":true}\n', encoding="utf-8")

    with pytest.raises(RealProteomicsSourcePreflightError, match="receipt is invalid"):
        workflow.verify()
