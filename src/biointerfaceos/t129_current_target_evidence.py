"""Consolidate all current T129 target-screening receipts fail-closed.

The component receipts document different candidate tranches.  This workflow
binds them into one current-state decision without treating a source-mapped,
single-laboratory exposure as a cross-study predictive target.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class T129CurrentTargetEvidenceError(RuntimeError):
    """Raised when the current T129 evidence boundary is weakened or stale."""


@dataclass(frozen=True)
class T129CurrentTargetEvidenceSummary:
    """Compact accounting for the consolidated no-target decision."""

    candidate_source_count: int
    candidate_laboratory_count: int
    verified_source_asset_count: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise T129CurrentTargetEvidenceError(f"{label} must be an object")
    return dict(value)


class T129CurrentTargetEvidenceWorkflow:
    """Verify all current T129 source tranches without allowing target promotion."""

    AUDIT_ID = "bioif-r2-t129-current-target-evidence-v1.3.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    OUTPUT_RELATIVE = "reports/review_round_2/t129_current_target_evidence/v1.3.0"
    RECEIPTS = {
        "initial_admission": (
            "reports/review_round_2/cc0_target_admission/v1.0.0/target_admission_receipt.json",
            "T129 initial admission receipt",
        ),
        "expansion_discovery": (
            "reports/review_round_2/cc0_target_discovery/v1.0.0/target_discovery_receipt.json",
            "T129 expansion discovery receipt",
        ),
        "pxd030327_unit_map": (
            "reports/review_round_2/cc0_pxd030327_unit_map/v1.0.0/unit_map_correction_receipt.json",
            "T129 PXD030327 unit-map receipt",
        ),
        "pxd017052_source_data": (
            "reports/review_round_2/pxd017052_source_data/v1.0.0/pxd017052_source_data_receipt.json",
            "T131 PXD017052 source-data receipt",
        ),
        "pxd017052_complete_attachments": (
            "reports/review_round_2/pxd017052_complete_attachments/v1.0.0/complete_attachment_receipt.json",
            "T132 PXD017052 complete-attachment receipt",
        ),
        "cc0_rescreen": (
            "reports/review_round_2/cc0_target_rescreen/v1.0.0/target_rescreen_receipt.json",
            "T138 bounded CC0 rescreen receipt",
        ),
    }
    REQUIRED_FALSE = (
        "model_fitted",
        "paired_ablations_run",
        "external_ood_evaluated",
        "negative_controls_run",
        "independent_validation",
        "scientific_submission_ready",
    )

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: str, label: str) -> Path:
        path = (self.root / relative).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise T129CurrentTargetEvidenceError(f"{label} is missing or outside the repository")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise T129CurrentTargetEvidenceError(f"cannot parse {label}") from exc

    @staticmethod
    def _require(condition: bool, label: str) -> None:
        if not condition:
            raise T129CurrentTargetEvidenceError(f"current T129 evidence no longer supports {label}")

    def _sources(self) -> dict[str, tuple[str, dict[str, Any], str]]:
        sources: dict[str, tuple[str, dict[str, Any], str]] = {}
        for key, (relative, label) in self.RECEIPTS.items():
            path = self._path(relative, label)
            sources[key] = (relative, self._json(path, label), _sha256(path))
        return sources

    def _validate_sources(self, sources: dict[str, tuple[str, dict[str, Any], str]]) -> None:
        initial = sources["initial_admission"][1]
        discovery = sources["expansion_discovery"][1]
        pxd030327 = sources["pxd030327_unit_map"][1]
        pxd017052 = sources["pxd017052_source_data"][1]
        pxd017052_complete = sources["pxd017052_complete_attachments"][1]
        rescreen = sources["cc0_rescreen"][1]
        self._require(
            initial.get("audit_id") == "bioif-r2-cc0-target-admission-v1.0.0"
            and initial.get("status") == "BLOCKED_NO_CC0_COMMON_TARGET"
            and initial.get("candidate_source_count") == 2
            and initial.get("candidate_laboratory_count") == 2
            and initial.get("source_condition_count") == 9
            and initial.get("admissible_target_count") == 0
            and initial.get("target_status") == "NOT_FROZEN"
            and initial.get("model_use") == "PROHIBITED",
            "initial CC0 admission tranche",
        )
        self._require(
            discovery.get("audit_id") == "bioif-r2-cc0-target-discovery-v1.0.0"
            and discovery.get("status") == "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES"
            and discovery.get("candidate_source_count") == 2
            and discovery.get("candidate_laboratory_count") == 1
            and discovery.get("screened_asset_count") == 7
            and discovery.get("admissible_target_count") == 0
            and discovery.get("target_status") == "NOT_FROZEN"
            and discovery.get("model_use") == "PROHIBITED",
            "CC0 expansion discovery tranche",
        )
        self._require(
            pxd030327.get("audit_id") == "bioif-r2-cc0-pxd030327-unit-map-v1.0.0"
            and pxd030327.get("status") == "VERIFIED_SINGLE_LAB_UNIT_MAP_NOT_ADMITTED"
            and pxd030327.get("unexcluded_unit_count") == 636
            and pxd030327.get("unique_matrix_run_count") == 819
            and pxd030327.get("unmapped_matrix_column_count") == 183
            and pxd030327.get("admission") == "NOT_ADMITTED"
            and pxd030327.get("model_use") == "PROHIBITED",
            "PXD030327 source-mapped single-laboratory tranche",
        )
        self._require(
            pxd017052.get("audit_id") == "bioif-r2-pxd017052-source-data-v1.0.0"
            and pxd017052.get("status") == "VERIFIED_PUBLIC_ASSETS_INCOMPLETE_SOURCE_UNIT_TO_PARTICLE_MAP"
            and pxd017052.get("official_asset_count") == 4
            and pxd017052.get("result_unit_count") == 9
            and pxd017052.get("pride_raw_unit_count") == 9
            and pxd017052.get("result_to_raw_match_count") == 9
            and pxd017052.get("explicit_raw_to_particle_map_count") == 0
            and pxd017052.get("material_record_count") == 3
            and pxd017052.get("admission") == "NOT_ADMITTED"
            and pxd017052.get("cc0_cohort_status") == "UNCHANGED"
            and pxd017052.get("ccby_candidate_cohort_status") == "NOT_CREATED_INCOMPLETE_MAP"
            and pxd017052.get("model_use") == "PROHIBITED",
            "PXD017052 public source-data tranche",
        )
        self._require(
            pxd017052_complete.get("audit_id") == "bioif-r2-pxd017052-complete-attachments-v1.0.0"
            and pxd017052_complete.get("status") == "VERIFIED_COMPLETE_UNIT_TO_PARTICLE_MAP_SINGLE_LAB_CCBY"
            and pxd017052_complete.get("extension_asset_count") == 8
            and pxd017052_complete.get("explicit_unit_to_particle_map_count") == 9
            and pxd017052_complete.get("admission") == "NOT_ADMITTED_PENDING_CCBY_AMENDMENT_AND_SECOND_LAB"
            and pxd017052_complete.get("cc0_cohort_status") == "UNCHANGED"
            and pxd017052_complete.get("model_use") == "PROHIBITED",
            "PXD017052 complete CC-BY source-map correction",
        )
        self._require(
            rescreen.get("audit_id") == "bioif-r2-cc0-target-rescreen-v1.0.0"
            and rescreen.get("status") == "BLOCKED_CC0_RESCREEN_NO_NEW_ADMISSIBLE_TARGET"
            and rescreen.get("candidate_source_count") == 2
            and rescreen.get("disclosed_laboratory_count") == 0
            and rescreen.get("screened_asset_count") == 7
            and rescreen.get("admissible_target_count") == 0
            and rescreen.get("target_status") == "NOT_FROZEN"
            and rescreen.get("model_use") == "PROHIBITED",
            "bounded CC0 rescreen tranche",
        )
        self._require(
            all(source[1].get(field) is False for source in sources.values() for field in self.REQUIRED_FALSE),
            "no-model and no-submission boundary",
        )

    def run(self, *, strict: bool = False) -> T129CurrentTargetEvidenceSummary:
        """Write an immutable, current consolidated T129 no-target receipt."""
        if not strict:
            raise T129CurrentTargetEvidenceError("T129 current evidence audit requires --strict")
        if self.output_root.exists():
            raise T129CurrentTargetEvidenceError("T129 current evidence audit already executed")
        sources = self._sources()
        self._validate_sources(sources)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET",
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "source_receipts": {key: {"path": value[0], "sha256": value[2]} for key, value in sources.items()},
            "candidate_source_count": 8,
            "candidate_laboratory_count": 5,
            "verified_source_asset_count": 31,
            "source_condition_count": 18,
            "source_mapped_single_lab_unit_count": 636,
            "source_mapped_unique_matrix_run_count": 819,
            "unmapped_matrix_column_count": 183,
            "complete_ccby_source_unit_route_count": 1,
            "rescreened_nonadmitted_source_count": 2,
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "blocked_reasons": [
                "No current source tranche supplies a shared endpoint together with a "
                "source-matched numeric material or size covariate for every admitted unit.",
                "PXD030327 verifies a single-laboratory run map and a source-defined numeric "
                "protein-to-nanoparticle exposure, not a numeric material or size covariate; "
                "categorical NP labels remain prohibited identity features.",
                "T132 verifies the eight remaining PXD017052 publisher assets and a complete "
                "nine-unit-to-SPION map, but this CC-BY single-laboratory route remains outside "
                "the frozen CC0 cohort pending an explicit amendment and lacks a cross-study "
                "endpoint.",
                "The candidate outputs remain author-specific and heterogeneous, so they cannot "
                "be concatenated before a shared preprocessing and analysis-unit contract is "
                "frozen across independent laboratories.",
                "The bounded PXD019524/PXD046988 rescreen adds seven checksum-recorded small "
                "assets, but their categorical source labels do not establish numeric material "
                "or size covariates, an independent laboratory, or a shared endpoint.",
            ],
            "next_required_evidence": [
                "Acquire at least two independent reusable sources with identically defined "
                "protein-corona endpoints and unit-level numeric material or size covariates.",
                "For PXD017052 specifically, decide any explicit CC-BY cohort amendment without "
                "weakening the CC0 public-release boundary, then obtain a second independent "
                "laboratory with the same frozen endpoint.",
                "Freeze the common preprocessing rule, biological-unit manifest, feature policy, "
                "study-held-out split and negative controls in T121 Amendment v1.0.1 before any "
                "T123 model run.",
            ],
            **{field: False for field in self.REQUIRED_FALSE},
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "current_target_evidence_report.json"
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "current_target_evidence_report_sha256": _sha256(report_path),
            "candidate_source_count": report["candidate_source_count"],
            "candidate_laboratory_count": report["candidate_laboratory_count"],
            "verified_source_asset_count": report["verified_source_asset_count"],
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            **{field: False for field in self.REQUIRED_FALSE},
        }
        receipt_path = self.output_root / "current_target_evidence_receipt.json"
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return T129CurrentTargetEvidenceSummary(8, 5, 31, receipt_path)

    def verify(self) -> T129CurrentTargetEvidenceSummary:
        """Verify all source hashes and the current no-target receipt."""
        report_path = self.output_root / "current_target_evidence_report.json"
        receipt_path = self.output_root / "current_target_evidence_receipt.json"
        report = self._json(report_path, "T129 current target evidence report")
        receipt = self._json(receipt_path, "T129 current target evidence receipt")
        required_counts = {
            "candidate_source_count": 8,
            "candidate_laboratory_count": 5,
            "verified_source_asset_count": 31,
            "admissible_target_count": 0,
        }
        self._require(
            report.get("audit_id") == self.AUDIT_ID
            and receipt.get("audit_id") == self.AUDIT_ID
            and report.get("status") == "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET"
            and receipt.get("status") == report.get("status")
            and receipt.get("current_target_evidence_report_sha256") == _sha256(report_path)
            and report.get("target_status") == "NOT_FROZEN"
            and receipt.get("target_status") == "NOT_FROZEN"
            and report.get("model_use") == "PROHIBITED"
            and receipt.get("model_use") == "PROHIBITED"
            and all(report.get(key) == value and receipt.get(key) == value for key, value in required_counts.items())
            and all(report.get(field) is False and receipt.get(field) is False for field in self.REQUIRED_FALSE),
            "current T129 target evidence receipt",
        )
        sources = self._sources()
        self._validate_sources(sources)
        expected_sources = {key: {"path": value[0], "sha256": value[2]} for key, value in sources.items()}
        self._require(
            report.get("source_receipts") == expected_sources,
            "current T129 source receipt hashes",
        )
        self._require(
            report.get("source_condition_count") == 18
            and report.get("complete_ccby_source_unit_route_count") == 1
            and report.get("rescreened_nonadmitted_source_count") == 2,
            "current T129 source accounting",
        )
        return T129CurrentTargetEvidenceSummary(8, 5, 31, receipt_path)
