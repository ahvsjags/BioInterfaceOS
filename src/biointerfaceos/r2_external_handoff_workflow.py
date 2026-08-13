"""Freeze the R2 external-evidence handoff boundary without simulating external work."""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    metadata_for,
    require_metadata,
)


class R2ExternalHandoffError(RuntimeError):
    """Raised when the external-evidence handoff package weakens an R2 gate."""


@dataclass(frozen=True)
class R2ExternalHandoffSummary:
    """Accounting for the source and external-evaluation handoff package."""

    status: str
    source_intake_field_count: int
    analysis_unit_field_count: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise R2ExternalHandoffError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise R2ExternalHandoffError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, minimum: int) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R2ExternalHandoffError(f"{label} has too few entries")
    items = [_string(item, label) for item in value]
    if len(items) != len(set(items)):
        raise R2ExternalHandoffError(f"{label} contains duplicates")
    return items


class R2ExternalHandoffWorkflow:
    """Audit a no-results package for external source and evaluator intake."""

    AUDIT_ID = "bioif-r2-external-evidence-handoff-v1.3.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    HANDOFF_RELATIVE = "docs/data/R2_EXTERNAL_EVIDENCE_HANDOFF.json"
    OUTPUT_RELATIVE = "reports/review_round_2/external_evidence_handoff/v1.3.0"
    REFERENCES = {
        "analysis_plan": (
            "docs/data/R2_EMPIRICAL_ANALYSIS_PLAN.md",
            "T121 empirical analysis plan",
        ),
        "t129_current_target_evidence": (
            "reports/review_round_2/t129_current_target_evidence/v1.2.0/"
            "current_target_evidence_receipt.json",
            "T129 current target-evidence receipt",
        ),
        "ccby_amendment_decision": (
            "docs/data/R2_T129_CCBY_COHORT_AMENDMENT_DECISION.md",
            "T129 CC-BY cohort-amendment decision",
        ),
        "independent_evaluation_protocol": (
            "docs/data/R2_INDEPENDENT_EVALUATION_PROTOCOL.json",
            "T124 independent-evaluation protocol",
        ),
        "external_acceptance_protocol": (
            "docs/data/R2_EXTERNAL_REPRODUCTION_AND_EDITORIAL_PROTOCOL.json",
            "T128 external acceptance protocol",
        ),
        "external_source_intake_template": (
            "docs/data/R2_EXTERNAL_SOURCE_INTAKE_TEMPLATE.json",
            "T135 external source-intake preflight template",
        ),
        "external_verification_bundle_template": (
            "docs/data/R2_EXTERNAL_VERIFICATION_BUNDLE_TEMPLATE.json",
            "T136 external verification preflight template",
        ),
        "portfolio": (
            "reports/review_round_2/manuscript_portfolio/v1.5.0/portfolio_receipt.json",
            "R2 manuscript portfolio receipt",
        ),
        "protocol_figures": (
            "reports/review_round_2/submission_figures/v1.2.0/generation_receipt.json",
            "R2 protocol-figure receipt",
        ),
        "public_release": (
            "reports/review_round_2/public_release_audit/v1.2.8/audit_receipt.json",
            "R2 public-release receipt",
        ),
    }
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "package_id",
        "declared_at",
        "status",
        "evidence_class",
        "allowed_claim_level",
        "current_state",
        "cohort_routing",
        "source_intake",
        "target_freeze",
        "independent_evaluation_handoff",
        "external_reproduction_and_editorial_handoff",
        "handoff_order",
        "prohibited_actions",
    }
    REQUIRED_CURRENT_STATE = {
        "admitted_cross_lab_target_count": 0,
        "model_use": "PROHIBITED",
        "independent_evaluator_receipt_verified": False,
        "external_reproduction_verified": False,
        "editorial_rereview_verified": False,
        "scientific_submission_ready": False,
    }
    REQUIRED_COHORT_ROUTING = {
        "active_route": "CC0_ONLY",
        "ccby_route_requires_explicit_owner_amendment": True,
        "ccby_route_may_not_merge_with_cc0": True,
        "ccby_route_may_not_authorize_model_fitting": True,
    }
    REQUIRED_SOURCE_IDENTITY_FIELDS = {
        "source_accession_or_doi",
        "official_repository_or_publisher_locator",
        "source_license",
        "laboratory_affiliation",
        "human_biofluid",
        "assay_and_acquisition_context",
    }
    REQUIRED_ANALYSIS_UNIT_FIELDS = {
        "analysis_unit_id",
        "source_file_or_result_id",
        "material_identity",
        "numeric_material_or_size_covariate",
        "covariate_unit",
        "biological_role",
        "replicate_role",
        "shared_endpoint_value",
        "endpoint_unit_or_scale",
        "shared_preprocessing_version",
        "source_asset_checksum",
    }
    REQUIRED_SOURCE_RULES = {
        "minimum_independent_laboratories": 2,
        "shared_endpoint_required": True,
        "source_matched_numeric_covariate_required": True,
        "author_quantification_scales_must_not_be_concatenated": True,
        "unresolved_source_labels_must_not_be_inferred": True,
    }
    REQUIRED_TARGET_FREEZE = {
        "t121_amendment_required_before_model": True,
        "frozen_items": {
            "analysis_unit_manifest",
            "endpoint_definition_and_preprocessing",
            "allowed_covariates_and_units",
            "study_held_out_split",
            "paired_configurations_and_seeds",
            "negative_controls",
            "analysis_code_hash",
        },
    }
    REQUIRED_EVALUATOR = {
        "activation_requires_frozen_real_model_bundle": True,
        "protected_values_must_remain_outside_repository": True,
        "aggregate_only_signed_receipt_required": True,
        "author_team_may_not_access_protected_values": True,
        "author_team_may_not_tune_after_freeze": True,
    }
    REQUIRED_REPRODUCTION = {
        "activation_requires_t123_t124_t126_t127": True,
        "independent_checkout_and_environment_required": True,
        "source_reacquisition_or_attestation_required": True,
        "deviation_ledger_required": True,
        "editorial_finding_matrix_and_signature_required": True,
    }
    REQUIRED_HANDOFF_ORDER = [
        "source_intake_and_license_gate",
        "cross_laboratory_target_admission",
        "t121_amendment_and_real_model_freeze",
        "independent_protected_data_evaluation",
        "external_scientific_reproduction",
        "editorial_rereview_and_r2_acceptance",
    ]
    REQUIRED_PROHIBITED_ACTIONS = {
        "fixture_substitution",
        "source_label_or_path_feature_inference",
        "cross_study_author_scale_concatenation",
        "model_fitting_before_t121_amendment",
        "author_team_self_certification_as_external_evaluator",
        "author_team_self_certification_as_external_reproducer_or_editor",
        "raw_protected_value_export",
        "submission_ready_claim_before_external_receipts",
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: str, label: str) -> Path:
        path = (self.root / relative).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R2ExternalHandoffError(f"{label} is missing or outside the repository")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R2ExternalHandoffError(f"cannot parse {label}") from exc

    @staticmethod
    def _exact_mapping(value: Any, expected: dict[str, Any], label: str) -> None:
        if _mapping(value, label) != expected:
            raise R2ExternalHandoffError(f"{label} is incomplete or weakens an R2 gate")

    @staticmethod
    def _exact_set(value: Any, expected: set[str], label: str) -> list[str]:
        items = _string_list(value, label, minimum=len(expected))
        if set(items) != expected:
            raise R2ExternalHandoffError(f"{label} is incomplete or weakens an R2 gate")
        return items

    def _package(self) -> tuple[dict[str, Any], Path]:
        path = self._path(self.HANDOFF_RELATIVE, "R2 external-evidence handoff package")
        package = self._json(path, "R2 external-evidence handoff package")
        if set(package) != self.REQUIRED_TOP_LEVEL or package.get("schema_version") != 1:
            raise R2ExternalHandoffError("R2 external-evidence handoff package schema is invalid")
        if (
            package.get("package_id") != "bioif-r2-external-evidence-handoff-v1.0.0"
            or package.get("declared_at") != self.AUDITED_AT
            or package.get("status") != "READY_FOR_EXTERNAL_SOURCE_INTAKE"
        ):
            raise R2ExternalHandoffError("R2 external-evidence handoff package identity is invalid")
        try:
            evidence_class, claim_level = require_metadata(package, "R2 external-evidence handoff")
        except EvidenceSemanticsError as exc:
            raise R2ExternalHandoffError(
                "R2 external-evidence handoff metadata is invalid"
            ) from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise R2ExternalHandoffError("R2 external-evidence handoff claim level is invalid")
        self._exact_mapping(package["current_state"], self.REQUIRED_CURRENT_STATE, "current state")
        self._exact_mapping(
            package["cohort_routing"], self.REQUIRED_COHORT_ROUTING, "cohort routing"
        )
        source_intake = _mapping(package["source_intake"], "source intake")
        if set(source_intake) != {
            "mandatory_identity_fields",
            "mandatory_analysis_unit_fields",
            "cross_study_acceptance_rules",
        }:
            raise R2ExternalHandoffError("source intake schema is invalid")
        self._exact_set(
            source_intake["mandatory_identity_fields"],
            self.REQUIRED_SOURCE_IDENTITY_FIELDS,
            "source identity fields",
        )
        self._exact_set(
            source_intake["mandatory_analysis_unit_fields"],
            self.REQUIRED_ANALYSIS_UNIT_FIELDS,
            "analysis-unit fields",
        )
        self._exact_mapping(
            source_intake["cross_study_acceptance_rules"],
            self.REQUIRED_SOURCE_RULES,
            "cross-study acceptance rules",
        )
        target_freeze = _mapping(package["target_freeze"], "target freeze")
        if set(target_freeze) != {"t121_amendment_required_before_model", "frozen_items"}:
            raise R2ExternalHandoffError("target-freeze schema is invalid")
        if target_freeze["t121_amendment_required_before_model"] is not True:
            raise R2ExternalHandoffError("target freeze weakens the T121 amendment gate")
        self._exact_set(
            target_freeze["frozen_items"],
            self.REQUIRED_TARGET_FREEZE["frozen_items"],
            "frozen items",
        )
        self._exact_mapping(
            package["independent_evaluation_handoff"],
            self.REQUIRED_EVALUATOR,
            "independent-evaluation handoff",
        )
        self._exact_mapping(
            package["external_reproduction_and_editorial_handoff"],
            self.REQUIRED_REPRODUCTION,
            "external-reproduction and editorial handoff",
        )
        if package["handoff_order"] != self.REQUIRED_HANDOFF_ORDER:
            raise R2ExternalHandoffError("handoff order is invalid")
        self._exact_set(
            package["prohibited_actions"],
            self.REQUIRED_PROHIBITED_ACTIONS,
            "prohibited actions",
        )
        return package, path

    def _sources(self) -> dict[str, dict[str, str]]:
        return {
            key: {"path": relative, "sha256": _sha256(self._path(relative, label))}
            for key, (relative, label) in self.REFERENCES.items()
        }

    def _validate_current_state(self) -> None:
        target_path = self._path(*self.REFERENCES["t129_current_target_evidence"])
        target = self._json(target_path, "T129 current target-evidence receipt")
        if (
            target.get("status") != "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET"
            or target.get("admissible_target_count") != 0
            or target.get("target_status") != "NOT_FROZEN"
            or target.get("model_use") != "PROHIBITED"
            or target.get("model_fitted") is not False
        ):
            raise R2ExternalHandoffError(
                "T129 state no longer supports an external-intake-only pack"
            )
        portfolio_path = self._path(*self.REFERENCES["portfolio"])
        portfolio = self._json(portfolio_path, "R2 manuscript portfolio receipt")
        if (
            portfolio.get("status") != "BLOCKED_R2_MANUSCRIPTS_PENDING_T123_T124"
            or portfolio.get("scientific_submission_ready") is not False
        ):
            raise R2ExternalHandoffError("R2 manuscript portfolio state is invalid")
        figures_path = self._path(*self.REFERENCES["protocol_figures"])
        figures = self._json(figures_path, "R2 protocol-figure receipt")
        if (
            figures.get("status") != "PASS_R2_PROTOCOL_FIGURE_SUITE"
            or figures.get("empirical_values_rendered") is not False
            or figures.get("scientific_submission_ready") is not False
        ):
            raise R2ExternalHandoffError("R2 figure state is invalid")
        release_path = self._path(*self.REFERENCES["public_release"])
        release = self._json(release_path, "R2 public-release receipt")
        if (
            release.get("status") != "PASS_PUBLIC_RELEASE_AUDIT"
            or release.get("scientific_submission_ready") is not False
        ):
            raise R2ExternalHandoffError("R2 public-release state is invalid")

    def run(self, *, strict: bool = False) -> R2ExternalHandoffSummary:
        """Write one immutable audit receipt for the external-evidence handoff pack."""
        if not strict:
            raise R2ExternalHandoffError("R2 external-evidence handoff audit requires --strict")
        if self.output_root.exists():
            raise R2ExternalHandoffError("R2 external-evidence handoff audit already executed")
        package, package_path = self._package()
        self._validate_current_state()
        sources = self._sources()
        source_intake = _mapping(package["source_intake"], "source intake")
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": package["status"],
            **metadata_for(EvidenceClass.DEVELOPMENT_OBSERVATION),
            "handoff_package_path": self.HANDOFF_RELATIVE,
            "handoff_package_sha256": _sha256(package_path),
            "source_receipts": sources,
            "source_intake_field_count": len(source_intake["mandatory_identity_fields"]),
            "analysis_unit_field_count": len(source_intake["mandatory_analysis_unit_fields"]),
            "admitted_cross_lab_target_count": 0,
            "model_use": "PROHIBITED",
            "external_source_received": False,
            "independent_evaluator_receipt_verified": False,
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "external_evidence_handoff_report.json"
        receipt_path = self.output_root / "external_evidence_handoff_receipt.json"
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "external_evidence_handoff_report_sha256": _sha256(report_path),
            "source_intake_field_count": report["source_intake_field_count"],
            "analysis_unit_field_count": report["analysis_unit_field_count"],
            "external_source_received": False,
            "independent_evaluator_receipt_verified": False,
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return R2ExternalHandoffSummary(
            status=report["status"],
            source_intake_field_count=report["source_intake_field_count"],
            analysis_unit_field_count=report["analysis_unit_field_count"],
            receipt_path=receipt_path,
        )

    def verify(self) -> R2ExternalHandoffSummary:
        """Verify the immutable handoff receipt without creating an external result."""
        report_path = self.output_root / "external_evidence_handoff_report.json"
        receipt_path = self.output_root / "external_evidence_handoff_receipt.json"
        report = self._json(report_path, "R2 external-evidence handoff report")
        receipt = self._json(receipt_path, "R2 external-evidence handoff receipt")
        try:
            evidence_class, claim_level = require_metadata(report, "R2 external-evidence handoff")
        except EvidenceSemanticsError as exc:
            raise R2ExternalHandoffError("R2 external-evidence handoff receipt is invalid") from exc
        expected_flags = {
            "external_source_received": False,
            "independent_evaluator_receipt_verified": False,
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "scientific_submission_ready": False,
        }
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != "READY_FOR_EXTERNAL_SOURCE_INTAKE"
            or receipt.get("status") != report.get("status")
            or receipt.get("external_evidence_handoff_report_sha256") != _sha256(report_path)
            or evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
            or report.get("source_intake_field_count") != len(self.REQUIRED_SOURCE_IDENTITY_FIELDS)
            or report.get("analysis_unit_field_count") != len(self.REQUIRED_ANALYSIS_UNIT_FIELDS)
            or receipt.get("source_intake_field_count") != report.get("source_intake_field_count")
            or receipt.get("analysis_unit_field_count") != report.get("analysis_unit_field_count")
            or any(
                report.get(key) is not value or receipt.get(key) is not value
                for key, value in expected_flags.items()
            )
        ):
            raise R2ExternalHandoffError("R2 external-evidence handoff receipt is invalid")
        if report.get("handoff_package_sha256") != _sha256(
            self._path(self.HANDOFF_RELATIVE, "R2 external-evidence handoff package")
        ):
            raise R2ExternalHandoffError("R2 external-evidence handoff package hash is stale")
        sources = _mapping(report.get("source_receipts"), "R2 external-evidence source receipts")
        if sources != self._sources():
            raise R2ExternalHandoffError("R2 external-evidence source receipt inventory is stale")
        return R2ExternalHandoffSummary(
            status=report["status"],
            source_intake_field_count=report["source_intake_field_count"],
            analysis_unit_field_count=report["analysis_unit_field_count"],
            receipt_path=receipt_path,
        )
