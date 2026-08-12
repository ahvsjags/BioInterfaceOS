"""Prepare and audit the R2 external reproduction and editorial acceptance gate."""

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


class R2AcceptanceError(RuntimeError):
    """Raised when an R2 acceptance path loses an external-evidence boundary."""


@dataclass(frozen=True)
class R2AcceptanceSummary:
    """Non-result accounting for the final R2 acceptance readiness audit."""

    status: str
    prerequisite_blocker_count: int
    external_reproduction_verified: bool
    editorial_rereview_verified: bool
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise R2AcceptanceError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise R2AcceptanceError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, minimum: int) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R2AcceptanceError(f"{label} has too few entries")
    items = [_string(item, label) for item in value]
    if len(items) != len(set(items)):
        raise R2AcceptanceError(f"{label} contains duplicates")
    return items


class R2AcceptanceWorkflow:
    """Emit a blocked receipt until external reproduction and editorial review exist."""

    AUDIT_ID = "bioif-r2-acceptance-readiness-v1.4.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    PROTOCOL_DECLARED_AT = "2026-08-12T00:00:00+00:00"
    PROTOCOL_RELATIVE = "docs/data/R2_EXTERNAL_REPRODUCTION_AND_EDITORIAL_PROTOCOL.json"
    PORTFOLIO_RELATIVE = "reports/review_round_2/manuscript_portfolio/v1.4.0/portfolio_receipt.json"
    T123_COMPATIBILITY_RELATIVE = (
        "reports/review_round_2/real_model_compatibility/v1.1.0/compatibility_receipt.json"
    )
    T123_RESULT_PROFILE_RELATIVE = (
        "reports/review_round_2/real_proteomics_result_profile/v1.0.0/result_profile_receipt.json"
    )
    T129_ADMISSION_RELATIVE = (
        "reports/review_round_2/cc0_target_admission/v1.0.0/target_admission_receipt.json"
    )
    T129_DISCOVERY_RELATIVE = (
        "reports/review_round_2/cc0_target_discovery/v1.0.0/target_discovery_receipt.json"
    )
    T129_CURRENT_TARGET_EVIDENCE_RELATIVE = (
        "reports/review_round_2/t129_current_target_evidence/v1.2.0/"
        "current_target_evidence_receipt.json"
    )
    T131_SOURCE_DATA_RELATIVE = (
        "reports/review_round_2/pxd017052_source_data/v1.0.0/"
        "pxd017052_source_data_receipt.json"
    )
    T124_RELATIVE = "reports/review_round_2/independent_evaluation/v1.0.0/readiness_receipt.json"
    TASKS_RELATIVE = "TASKS.tsv"
    OUTPUT_RELATIVE = "reports/review_round_2/r2_acceptance/v1.4.0"
    REQUIRED_PROTOCOL_FIELDS = {
        "schema_version",
        "protocol_id",
        "declared_at",
        "status",
        "external_reproduction_requirements",
        "editorial_rereview_requirements",
        "required_external_receipt_fields",
        "required_editorial_report_fields",
        "prohibited_actions",
    }
    REQUIRED_EXTERNAL_REQUIREMENTS = {
        "team_must_not_include_authors",
        "conflict_disclosure_required",
        "independent_checkout_and_environment_required",
        "source_data_must_be_reacquired_or_attested",
        "reproduce_declared_analysis_required",
        "deviation_ledger_required",
        "scope_and_result_report_required",
    }
    REQUIRED_EDITORIAL_REQUIREMENTS = {
        "reviewer_must_not_be_author",
        "conflict_disclosure_required",
        "every_r2_finding_must_be_mapped",
        "critical_findings_must_be_zero_for_acceptance",
        "downgrade_or_evidence_required_for_each_finding",
        "signed_editorial_report_required",
    }
    REQUIRED_EXTERNAL_RECEIPT_FIELDS = {
        "team_identity_and_affiliation",
        "conflict_disclosure",
        "checkout_commit",
        "environment_digest",
        "source_data_attestation",
        "commands_and_scope",
        "deviation_ledger",
        "result_summary",
        "signed_attestation",
    }
    REQUIRED_EDITORIAL_REPORT_FIELDS = {
        "reviewer_identity_and_affiliation",
        "conflict_disclosure",
        "r2_finding_matrix",
        "critical_finding_count",
        "manuscript_dispositions",
        "signed_attestation",
    }
    REQUIRED_PROHIBITED_ACTIONS = {
        "author_team_self_certification_as_external_reproduction",
        "fixture_substitution_for_empirical_reproduction",
        "unlogged_deviation",
        "critical_finding_omission",
        "submission_ready_before_external_receipts",
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: Any, label: str) -> Path:
        path = (self.root / _string(relative, label)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R2AcceptanceError(f"{label} is missing or outside the repository")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R2AcceptanceError(f"cannot parse {label}") from exc

    @staticmethod
    def _true_mapping(value: Any, expected: set[str], label: str) -> None:
        mapping = _mapping(value, label)
        if set(mapping) != expected or any(item is not True for item in mapping.values()):
            raise R2AcceptanceError(f"{label} is incomplete or weakens a required safeguard")

    def _protocol(self) -> tuple[dict[str, Any], Path]:
        path = self._path(self.PROTOCOL_RELATIVE, "R2 external acceptance protocol")
        protocol = self._json(path, "R2 external acceptance protocol")
        if set(protocol) != self.REQUIRED_PROTOCOL_FIELDS or protocol.get("schema_version") != 1:
            raise R2AcceptanceError("R2 external acceptance protocol schema is invalid")
        if (
            protocol.get("protocol_id")
            != "bioif-r2-external-reproduction-editorial-protocol-v1.0.0"
            or protocol.get("declared_at") != self.PROTOCOL_DECLARED_AT
            or protocol.get("status") != "PROTOCOL_ONLY_PENDING_T123_T124_T126_T127"
        ):
            raise R2AcceptanceError("R2 external acceptance protocol identity is invalid")
        self._true_mapping(
            protocol["external_reproduction_requirements"],
            self.REQUIRED_EXTERNAL_REQUIREMENTS,
            "external reproduction requirements",
        )
        self._true_mapping(
            protocol["editorial_rereview_requirements"],
            self.REQUIRED_EDITORIAL_REQUIREMENTS,
            "editorial re-review requirements",
        )
        if (
            set(
                _string_list(
                    protocol["required_external_receipt_fields"],
                    "external receipt fields",
                    minimum=9,
                )
            )
            != self.REQUIRED_EXTERNAL_RECEIPT_FIELDS
        ):
            raise R2AcceptanceError("external reproduction receipt fields are incomplete")
        if (
            set(
                _string_list(
                    protocol["required_editorial_report_fields"],
                    "editorial report fields",
                    minimum=6,
                )
            )
            != self.REQUIRED_EDITORIAL_REPORT_FIELDS
        ):
            raise R2AcceptanceError("editorial re-review report fields are incomplete")
        if (
            set(_string_list(protocol["prohibited_actions"], "prohibited actions", minimum=5))
            != self.REQUIRED_PROHIBITED_ACTIONS
        ):
            raise R2AcceptanceError("external acceptance prohibitions are incomplete")
        return protocol, path

    def _task_statuses(self) -> dict[str, str]:
        path = self._path(self.TASKS_RELATIVE, "R2 task ledger")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise R2AcceptanceError("cannot read R2 task ledger") from exc
        statuses: dict[str, str] = {}
        for line in lines[1:]:
            columns = line.split("\t")
            if len(columns) > 4 and columns[0] in {
                "T123",
                "T124",
                "T126",
                "T127",
                "T128",
                "T129",
            }:
                statuses[columns[0]] = columns[4]
        if set(statuses) != {"T123", "T124", "T126", "T127", "T128", "T129"}:
            raise R2AcceptanceError("R2 task ledger is missing final acceptance tasks")
        return statuses

    def _prerequisites(self) -> tuple[dict[str, Any], list[str]]:
        portfolio_path = self._path(self.PORTFOLIO_RELATIVE, "R2 manuscript portfolio receipt")
        compatibility_path = self._path(
            self.T123_COMPATIBILITY_RELATIVE, "T123 compatibility receipt"
        )
        result_profile_path = self._path(
            self.T123_RESULT_PROFILE_RELATIVE, "T123 result-profile receipt"
        )
        t129_admission_path = self._path(self.T129_ADMISSION_RELATIVE, "T129 admission receipt")
        t129_discovery_path = self._path(self.T129_DISCOVERY_RELATIVE, "T129 discovery receipt")
        t129_current_target_evidence_path = self._path(
            self.T129_CURRENT_TARGET_EVIDENCE_RELATIVE,
            "T129 current target-evidence receipt",
        )
        t131_source_data_path = self._path(
            self.T131_SOURCE_DATA_RELATIVE,
            "T131 PXD017052 source-data receipt",
        )
        t124_path = self._path(self.T124_RELATIVE, "T124 readiness receipt")
        portfolio = self._json(portfolio_path, "R2 manuscript portfolio receipt")
        compatibility = self._json(compatibility_path, "T123 compatibility receipt")
        result_profile = self._json(result_profile_path, "T123 result-profile receipt")
        t129_admission = self._json(t129_admission_path, "T129 admission receipt")
        t129_discovery = self._json(t129_discovery_path, "T129 discovery receipt")
        t129_current_target_evidence = self._json(
            t129_current_target_evidence_path,
            "T129 current target-evidence receipt",
        )
        t131_source_data = self._json(t131_source_data_path, "T131 PXD017052 source-data receipt")
        t124 = self._json(t124_path, "T124 readiness receipt")
        statuses = self._task_statuses()
        blockers: list[str] = []
        if (
            compatibility.get("compatible_target_count") != 1
            or compatibility.get("model_fitted") is not True
        ):
            blockers.append("T123 compatible target and frozen real-model output are unavailable")
        if (
            result_profile.get("compatible_cross_study_target_count") != 1
            or result_profile.get("target_status") != "FROZEN"
        ):
            blockers.append("T123 current result-profile evidence has no frozen compatible target")
        if (
            t129_admission.get("status") != "BLOCKED_NO_CC0_COMMON_TARGET"
            or t129_admission.get("admissible_target_count") != 0
            or t129_admission.get("target_status") != "NOT_FROZEN"
            or t129_admission.get("model_use") != "PROHIBITED"
            or t129_discovery.get("status")
            != "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES"
            or t129_discovery.get("admissible_target_count") != 0
            or t129_discovery.get("target_status") != "NOT_FROZEN"
            or t129_discovery.get("model_use") != "PROHIBITED"
            or t129_current_target_evidence.get("status")
            != "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET"
            or t129_current_target_evidence.get("candidate_source_count") != 6
            or t129_current_target_evidence.get("candidate_laboratory_count") != 5
            or t129_current_target_evidence.get("verified_source_asset_count") != 24
            or t129_current_target_evidence.get("admissible_target_count") != 0
            or t129_current_target_evidence.get("target_status") != "NOT_FROZEN"
            or t129_current_target_evidence.get("model_use") != "PROHIBITED"
            or t129_current_target_evidence.get("model_fitted") is not False
        ):
            raise R2AcceptanceError("T129 current target-evidence receipt is invalid")
        if (
            t131_source_data.get("status")
            != "VERIFIED_PUBLIC_ASSETS_INCOMPLETE_SOURCE_UNIT_TO_PARTICLE_MAP"
            or t131_source_data.get("official_asset_count") != 4
            or t131_source_data.get("result_to_raw_match_count") != 9
            or t131_source_data.get("explicit_raw_to_particle_map_count") != 0
            or t131_source_data.get("admission") != "NOT_ADMITTED"
            or t131_source_data.get("model_use") != "PROHIBITED"
        ):
            raise R2AcceptanceError("T131 source-data receipt is invalid")
        blockers.append(
            "T129 current CC0 synthesis has not admitted a cross-laboratory numeric-material target"
        )
        if t124.get("external_evaluator_receipt_verified") is not True:
            blockers.append("T124 independent evaluator receipt is unavailable")
        if portfolio.get("status") != "READY_FOR_R2_RESULTS_MANUSCRIPTS":
            blockers.append("T126/T127 manuscript portfolio remains protocol-only")
        for task_id in ("T126", "T127"):
            if statuses[task_id] != "DONE":
                blockers.append(f"{task_id} is not complete")
        if statuses["T128"] != "READY":
            blockers.append("T128 cannot start external acceptance from its current task state")
        if statuses["T129"] != "DONE":
            blockers.append("T129 target-admission work is not complete")
        return (
            {
                "portfolio_receipt_sha256": _sha256(portfolio_path),
                "t123_compatibility_receipt_sha256": _sha256(compatibility_path),
                "t123_result_profile_receipt_sha256": _sha256(result_profile_path),
                "t129_admission_receipt_sha256": _sha256(t129_admission_path),
                "t129_discovery_receipt_sha256": _sha256(t129_discovery_path),
                "t129_current_target_evidence_receipt_sha256": _sha256(
                    t129_current_target_evidence_path
                ),
                "t131_source_data_receipt_sha256": _sha256(t131_source_data_path),
                "t124_readiness_receipt_sha256": _sha256(t124_path),
                "task_statuses": statuses,
            },
            blockers,
        )

    def run(self, *, strict: bool = False) -> R2AcceptanceSummary:
        """Write one immutable acceptance-readiness receipt without external claims."""
        if not strict:
            raise R2AcceptanceError("T128 requires --strict")
        if self.output_root.exists():
            raise R2AcceptanceError("R2 acceptance readiness audit already executed")
        protocol, protocol_path = self._protocol()
        prerequisites, blockers = self._prerequisites()
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(protocol_path),
            "status": "BLOCKED_R2_EXTERNAL_EVIDENCE_REQUIRED",
            **metadata_for(EvidenceClass.DEVELOPMENT_OBSERVATION),
            "prerequisite_state": prerequisites,
            "blocking_reasons": blockers,
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "external_reproduction_receipt_present": False,
            "editorial_report_present": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "acceptance_readiness_report.json"
        receipt_path = self.output_root / "acceptance_readiness_receipt.json"
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "acceptance_readiness_report_sha256": _sha256(report_path),
            "prerequisite_blocker_count": len(blockers),
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "external_reproduction_receipt_present": False,
            "editorial_report_present": False,
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return R2AcceptanceSummary(
            status=report["status"],
            prerequisite_blocker_count=len(blockers),
            external_reproduction_verified=False,
            editorial_rereview_verified=False,
            receipt_path=receipt_path,
        )

    def verify(self) -> R2AcceptanceSummary:
        """Verify the immutable blocked receipt without simulating external actors."""
        report_path = self.output_root / "acceptance_readiness_report.json"
        receipt_path = self.output_root / "acceptance_readiness_receipt.json"
        report = self._json(report_path, "R2 acceptance readiness report")
        receipt = self._json(receipt_path, "R2 acceptance readiness receipt")
        try:
            evidence_class, claim_level = require_metadata(report, "R2 acceptance readiness")
        except EvidenceSemanticsError as exc:
            raise R2AcceptanceError("R2 acceptance readiness receipt is invalid") from exc
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != "BLOCKED_R2_EXTERNAL_EVIDENCE_REQUIRED"
            or receipt.get("status") != report.get("status")
            or receipt.get("acceptance_readiness_report_sha256") != _sha256(report_path)
            or evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise R2AcceptanceError("R2 acceptance readiness receipt is invalid")
        if (
            not isinstance(receipt.get("prerequisite_blocker_count"), int)
            or receipt["prerequisite_blocker_count"] < 1
        ):
            raise R2AcceptanceError("R2 acceptance readiness blocker accounting is invalid")
        for field in (
            "external_reproduction_verified",
            "editorial_rereview_verified",
            "external_reproduction_receipt_present",
            "editorial_report_present",
            "scientific_submission_ready",
        ):
            if report.get(field) is not False or receipt.get(field) is not False:
                raise R2AcceptanceError(
                    "R2 acceptance readiness contains a fabricated external result"
                )
        return R2AcceptanceSummary(
            status="BLOCKED_R2_EXTERNAL_EVIDENCE_REQUIRED",
            prerequisite_blocker_count=int(receipt["prerequisite_blocker_count"]),
            external_reproduction_verified=False,
            editorial_rereview_verified=False,
            receipt_path=receipt_path,
        )
