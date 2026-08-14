"""Tests for the external source-intake preflight without using real observations."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from biointerfaceos.external_source_intake import (
    ExternalSourceIntakeError,
    ExternalSourceIntakeWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_structural_submission(tmp_path: Path) -> tuple[Path, Path]:
    assets_root = tmp_path / "assets"
    (assets_root / "source-a").mkdir(parents=True)
    (assets_root / "source-b").mkdir(parents=True)
    payload_a = b"synthetic structural source A\n"
    payload_b = b"synthetic structural source B\n"
    (assets_root / "source-a" / "result.tsv").write_bytes(payload_a)
    (assets_root / "source-b" / "result.tsv").write_bytes(payload_b)
    checksum_a = _sha256(payload_a)
    checksum_b = _sha256(payload_b)

    def source(
        source_id: str,
        laboratory: str,
        asset_path: str,
        checksum: str,
        covariate: float,
    ) -> dict[str, object]:
        asset_id = f"{source_id}-result"
        return {
            "source_id": source_id,
            "source_accession_or_doi": f"10.0000/{source_id}",
            "official_repository_or_publisher_locator": f"https://example.org/{source_id}",
            "source_license": "CC0-1.0",
            "laboratory_affiliation": laboratory,
            "human_biofluid": "human plasma",
            "assay_and_acquisition_context": "declared external assay context",
            "author_scale_segregated": True,
            "source_assets": [{"asset_id": asset_id, "relative_path": asset_path, "sha256": checksum}],
            "analysis_units": [
                {
                    "analysis_unit_id": f"{source_id}-unit-1",
                    "source_file_or_result_id": asset_id,
                    "material_identity": "declared material identity",
                    "numeric_material_or_size_covariate": {
                        "name": "declared material size",
                        "value": covariate,
                        "unit": "nm",
                    },
                    "biological_role": "source-declared sample role",
                    "replicate_role": "source-declared replicate role",
                    "shared_endpoint_value": 1.0,
                    "endpoint_unit_or_scale": "shared normalized endpoint",
                    "shared_preprocessing_version": "external-preprocessing-v1",
                    "source_asset_checksum": checksum,
                }
            ],
        }

    manifest = {
        "schema_version": 1,
        "submission_state": "SUBMITTED_FOR_PREFLIGHT",
        "intake_id": "synthetic-structural-preflight",
        "submitted_at": "2026-08-13T00:00:00+00:00",
        "evidence_class": "DEVELOPMENT_OBSERVATION",
        "allowed_claim_level": "EXPLORATORY",
        "target_admission_requested": False,
        "source_records": [
            source("source-a", "Independent Lab A", "source-a/result.tsv", checksum_a, 50.0),
            source("source-b", "Independent Lab B", "source-b/result.tsv", checksum_b, 80.0),
        ],
    }
    manifest_path = tmp_path / "submission.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, assets_root


def test_external_source_intake_requires_two_hashed_source_packages(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)

    summary = ExternalSourceIntakeWorkflow(manifest_path, assets_root).run(strict=True)

    assert summary.status == "STRUCTURALLY_COMPLETE_REQUIRES_SOURCE_AUDIT"
    assert summary.source_count == 2
    assert summary.laboratory_count == 2
    assert summary.source_asset_count == 2
    assert summary.analysis_unit_count == 2


def test_external_source_intake_rejects_missing_strict_mode(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)

    with pytest.raises(ExternalSourceIntakeError, match="requires --strict"):
        ExternalSourceIntakeWorkflow(manifest_path, assets_root).run()


def test_external_source_intake_rejects_checksum_mutation(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)
    (assets_root / "source-a" / "result.tsv").write_bytes(b"mutated bytes\n")

    with pytest.raises(ExternalSourceIntakeError, match="checksum does not match"):
        ExternalSourceIntakeWorkflow(manifest_path, assets_root).run(strict=True)


def test_external_source_intake_rejects_one_laboratory(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_records"][1]["laboratory_affiliation"] = "Independent Lab A"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ExternalSourceIntakeError, match="fewer than two laboratories"):
        ExternalSourceIntakeWorkflow(manifest_path, assets_root).run(strict=True)


def test_external_source_intake_rejects_reused_asset_across_laboratories(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_asset = manifest["source_records"][0]["source_assets"][0]
    second_source = manifest["source_records"][1]
    second_source["source_assets"][0]["relative_path"] = first_asset["relative_path"]
    second_source["source_assets"][0]["sha256"] = first_asset["sha256"]
    second_source["analysis_units"][0]["source_asset_checksum"] = first_asset["sha256"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ExternalSourceIntakeError, match="reuses one source asset"):
        ExternalSourceIntakeWorkflow(manifest_path, assets_root).run(strict=True)


def test_external_source_intake_rejects_asset_path_escape(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_records"][0]["source_assets"][0]["relative_path"] = "../escape.tsv"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ExternalSourceIntakeError, match="escapes the declared assets root"):
        ExternalSourceIntakeWorkflow(manifest_path, assets_root).run(strict=True)


def test_external_source_intake_rejects_unfilled_template(tmp_path: Path) -> None:
    assets_root = tmp_path / "assets"
    assets_root.mkdir()
    template = ROOT / "docs/data/R2_EXTERNAL_SOURCE_INTAKE_TEMPLATE.json"

    with pytest.raises(ExternalSourceIntakeError, match="not a submitted preflight package"):
        ExternalSourceIntakeWorkflow(template, assets_root).run(strict=True)


def test_external_source_intake_cli_preserves_non_promoting_status(tmp_path: Path) -> None:
    manifest_path, assets_root = _write_structural_submission(tmp_path)
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "biointerfaceos",
            "data",
            "preflight-external-source-intake",
            "--manifest",
            str(manifest_path),
            "--assets-root",
            str(assets_root),
            "--strict",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "status=STRUCTURALLY_COMPLETE_REQUIRES_SOURCE_AUDIT" in result.stdout
    assert "target_admitted=false" in result.stdout
    assert "model_fitted=false" in result.stdout
