"""Prepare and audit the R2 external-evaluator handoff without touching protected data."""

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


class IndependentEvaluationError(RuntimeError):
    """Raised when an external-evaluation handoff crosses a hard R2 boundary."""


@dataclass(frozen=True)
class IndependentEvaluationSummary:
    """Compact, non-result summary of one immutable readiness audit."""

    status: str
    compatible_target_count: int
    evaluator_receipt_verified: bool
    blocking_reason_count: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise IndependentEvaluationError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IndependentEvaluationError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IndependentEvaluationError(f"{label} must be an integer >= {minimum}")
    return int(value)


class IndependentEvaluationWorkflow:
    """Emit a fail-closed T124 readiness receipt, never a surrogate evaluation."""

    AUDIT_ID = "bioif-r2-independent-evaluation-readiness-v1.0.0"
    AUDITED_AT = "2026-08-12T00:00:00+00:00"
    PROTOCOL_RELATIVE = "docs/data/R2_INDEPENDENT_EVALUATION_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_2/independent_evaluation/v1.0.0"
    REQUIRED_PROTOCOL_FIELDS = {
        "protocol_id",
        "declared_at",
        "status",
        "t123_gate",
        "independence_requirements",
        "protected_data_requirements",
        "frozen_bundle_requirements",
        "result_receipt_requirements",
        "external_receipt_schema_path",
        "prohibited_actions",
    }
    REQUIRED_INDEPENDENCE = {
        "external_evaluator_required",
        "evaluator_must_not_be_author",
        "evaluator_conflict_disclosure_required",
        "author_team_access_to_protected_observations",
        "author_team_may_tune_after_freeze",
    }
    REQUIRED_PROTECTED_DATA = {
        "data_must_remain_outside_repository",
        "raw_values_must_not_enter_receipt",
        "aggregate_metrics_only",
        "evaluator_environment_separate_from_author_environment",
    }
    REQUIRED_FROZEN_BUNDLE = {
        "git_commit",
        "environment_lock_sha256",
        "target_registry_sha256",
        "split_manifest_sha256",
        "model_configuration_sha256",
        "prediction_archive_sha256",
        "threshold_ledger_sha256",
    }
    REQUIRED_RESULT_RECEIPT = {
        "evaluator_identity_and_affiliation",
        "conflict_disclosure",
        "signed_attestation",
        "frozen_bundle_hashes",
        "aggregate_metrics",
        "threshold_statuses",
        "environment_digest",
        "raw_values_included",
        "author_team_accessed_protected_observations",
        "post_freeze_tuning",
    }
    REQUIRED_PROHIBITED_ACTIONS = frozenset(
        {
            "author_access_to_protected_observations",
            "post_freeze_training",
            "post_freeze_tuning",
            "post_freeze_threshold_change",
            "raw_value_export_to_repository",
            "fixture_substitution",
        }
    )
    READY_COMPATIBILITY_STATUS = "READY_FOR_FROZEN_REAL_MODEL_EVALUATION"

    def __init__(
        self,
        root: Path,
        *,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: Any, label: str) -> Path:
        path = (self.root / _string(relative, label)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise IndependentEvaluationError(f"{label} must be a repository file")
        if "data/locked_test" in path.as_posix():
            raise IndependentEvaluationError(f"{label} must not enter the protected-data namespace")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IndependentEvaluationError(f"cannot load {label}") from exc

    @staticmethod
    def _require_exact_true_fields(
        value: Any,
        required: set[str],
        label: str,
    ) -> dict[str, bool]:
        mapping = _mapping(value, label)
        if set(mapping) != required or any(item is not True for item in mapping.values()):
            raise IndependentEvaluationError(f"{label} is incomplete or weakens a required boundary")
        return {key: True for key in required}

    def _protocol(self) -> tuple[dict[str, Any], Path]:
        path = self._path(self.PROTOCOL_RELATIVE, "T124 protocol")
        protocol = self._json(path, "T124 protocol")
        if protocol.get("schema_version") != 1 or not self.REQUIRED_PROTOCOL_FIELDS.issubset(protocol):
            raise IndependentEvaluationError("T124 protocol schema is invalid")
        if (
            protocol.get("protocol_id") != "bioif-r2-independent-evaluation-protocol-v1.0.0"
            or protocol.get("declared_at") != self.AUDITED_AT
            or protocol.get("status") != "PROTOCOL_ONLY_PENDING_T123"
        ):
            raise IndependentEvaluationError("T124 protocol identity or state is invalid")
        try:
            evidence_class, claim_level = require_metadata(protocol, "T124 protocol")
        except EvidenceSemanticsError as exc:
            raise IndependentEvaluationError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise IndependentEvaluationError("T124 protocol must remain exploratory before a receipt")
        independence = _mapping(protocol["independence_requirements"], "independence requirements")
        if (
            set(independence) != self.REQUIRED_INDEPENDENCE
            or independence.get("external_evaluator_required") is not True
            or independence.get("evaluator_must_not_be_author") is not True
            or independence.get("evaluator_conflict_disclosure_required") is not True
            or independence.get("author_team_access_to_protected_observations") is not False
            or independence.get("author_team_may_tune_after_freeze") is not False
        ):
            raise IndependentEvaluationError("author access or tuning is not forbidden")
        self._require_exact_true_fields(
            protocol["protected_data_requirements"],
            self.REQUIRED_PROTECTED_DATA,
            "protected-data requirements",
        )
        frozen_bundle = protocol["frozen_bundle_requirements"]
        if not isinstance(frozen_bundle, list) or set(frozen_bundle) != self.REQUIRED_FROZEN_BUNDLE:
            raise IndependentEvaluationError("frozen-bundle requirements are incomplete")
        result_receipt = protocol["result_receipt_requirements"]
        if not isinstance(result_receipt, list) or set(result_receipt) != self.REQUIRED_RESULT_RECEIPT:
            raise IndependentEvaluationError("result-receipt requirements are incomplete")
        receipt_schema_path = self._path(protocol["external_receipt_schema_path"], "external evaluator receipt schema")
        receipt_schema = self._json(receipt_schema_path, "external evaluator receipt schema")
        required_receipt_fields = {
            "schema_version",
            "evaluation_id",
            "protocol_id",
            "evaluator",
            "frozen_bundle",
            "attestation",
            "aggregate_metrics",
            "threshold_statuses",
            "environment_digest",
            "raw_values_included",
            "author_team_accessed_protected_observations",
            "post_freeze_tuning",
        }
        if (
            receipt_schema.get("type") != "object"
            or receipt_schema.get("additionalProperties") is not False
            or set(receipt_schema.get("required", [])) != required_receipt_fields
            or not required_receipt_fields.issubset(receipt_schema.get("properties", {}))
        ):
            raise IndependentEvaluationError("external evaluator receipt schema is unsafe")
        prohibited = protocol["prohibited_actions"]
        if not isinstance(prohibited, list) or set(prohibited) != self.REQUIRED_PROHIBITED_ACTIONS:
            raise IndependentEvaluationError("prohibited actions are incomplete")
        return protocol, path

    def _t123_state(self, protocol: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
        gate = _mapping(protocol["t123_gate"], "T123 gate")
        required = {"decision_path", "receipt_path", "required_status", "required_false_fields"}
        if set(gate) != required or gate.get("required_status") != self.READY_COMPATIBILITY_STATUS:
            raise IndependentEvaluationError("T123 gate definition is invalid")
        false_fields = gate["required_false_fields"]
        if not isinstance(false_fields, list) or set(false_fields) != {
            "model_fitted",
            "paired_ablations_run",
            "external_ood_evaluated",
            "negative_controls_run",
        }:
            raise IndependentEvaluationError("T123 gate must enumerate current unavailable outputs")
        decision_path = self._path(gate["decision_path"], "T123 compatibility decision")
        receipt_path = self._path(gate["receipt_path"], "T123 compatibility receipt")
        decision = self._json(decision_path, "T123 compatibility decision")
        receipt = self._json(receipt_path, "T123 compatibility receipt")
        if receipt.get("compatibility_decision_sha256") != _sha256(decision_path):
            raise IndependentEvaluationError("T123 compatibility receipt does not bind its decision")
        compatible_target_count = _integer(receipt.get("compatible_target_count"), "T123 compatible target count")
        if decision.get("status") != receipt.get("status"):
            raise IndependentEvaluationError("T123 decision and receipt statuses differ")
        reasons: list[str] = []
        if decision.get("status") != gate["required_status"]:
            reasons.append("T123 compatibility decision is not ready for frozen real-model evaluation")
        if compatible_target_count < 1:
            reasons.append("T123 has no admitted compatible cross-study target")
        for field in false_fields:
            if receipt.get(field) is not True:
                reasons.append(f"T123 has not produced {field}")
        observed = {
            "decision_path": str(decision_path.relative_to(self.root)),
            "decision_sha256": _sha256(decision_path),
            "receipt_path": str(receipt_path.relative_to(self.root)),
            "receipt_sha256": _sha256(receipt_path),
            "status": _string(receipt.get("status"), "T123 receipt status"),
            "compatible_target_count": compatible_target_count,
            "model_fitted": receipt.get("model_fitted"),
            "paired_ablations_run": receipt.get("paired_ablations_run"),
            "external_ood_evaluated": receipt.get("external_ood_evaluated"),
            "negative_controls_run": receipt.get("negative_controls_run"),
        }
        return observed, reasons

    def run(self, *, strict: bool = False) -> IndependentEvaluationSummary:
        """Write one readiness receipt; this command never evaluates protected values."""
        if not strict:
            raise IndependentEvaluationError("T124 requires --strict")
        if self.output_root.exists():
            raise IndependentEvaluationError("independent-evaluation readiness audit already executed")
        protocol, protocol_path = self._protocol()
        t123, reasons = self._t123_state(protocol)
        status = "READY_FOR_EXTERNAL_EVALUATOR_FREEZE" if not reasons else "BLOCKED_T123_COMPATIBLE_TARGET_REQUIRED"
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(protocol_path),
            "status": status,
            **metadata_for(EvidenceClass.DEVELOPMENT_OBSERVATION),
            "t123_observed_state": t123,
            "blocking_reasons": reasons,
            "external_evaluator_receipt_verified": False,
            "protected_observations_accessed": False,
            "author_team_accessed_protected_observations": False,
            "raw_values_written": False,
            "aggregate_metrics_written": False,
            "scientific_submission_ready": False,
        }
        report_bytes = _canonical(report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": status,
            "readiness_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "compatible_target_count": t123["compatible_target_count"],
            "blocking_reason_count": len(reasons),
            "external_evaluator_receipt_verified": False,
            "protected_observations_accessed": False,
            "author_team_accessed_protected_observations": False,
            "raw_values_written": False,
            "aggregate_metrics_written": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "readiness_report.json"
        receipt_path = self.output_root / "readiness_receipt.json"
        report_path.write_bytes(report_bytes)
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return IndependentEvaluationSummary(
            status=status,
            compatible_target_count=t123["compatible_target_count"],
            evaluator_receipt_verified=False,
            blocking_reason_count=len(reasons),
            receipt_path=receipt_path,
        )

    def verify(self) -> IndependentEvaluationSummary:
        """Verify the readiness receipt and its no-results boundary."""
        report_path = self.output_root / "readiness_report.json"
        receipt_path = self.output_root / "readiness_receipt.json"
        report = self._json(report_path, "independent-evaluation readiness report")
        receipt = self._json(receipt_path, "independent-evaluation readiness receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != receipt.get("status")
            or receipt.get("readiness_report_sha256") != _sha256(report_path)
            or report.get("evidence_class") != EvidenceClass.DEVELOPMENT_OBSERVATION.value
            or report.get("allowed_claim_level") != AllowedClaimLevel.EXPLORATORY.value
        ):
            raise IndependentEvaluationError("independent-evaluation readiness receipt is invalid")
        required_false = (
            "external_evaluator_receipt_verified",
            "protected_observations_accessed",
            "author_team_accessed_protected_observations",
            "raw_values_written",
            "aggregate_metrics_written",
            "scientific_submission_ready",
        )
        if any(report.get(field) is not False for field in required_false) or any(
            receipt.get(field) is not False for field in required_false
        ):
            raise IndependentEvaluationError("readiness receipt contains an evaluation result")
        compatible_target_count = _integer(receipt.get("compatible_target_count"), "receipt compatible target count")
        blocking_reason_count = _integer(receipt.get("blocking_reason_count"), "receipt blocking reason count")
        if report["status"] == "BLOCKED_T123_COMPATIBLE_TARGET_REQUIRED" and (
            compatible_target_count != 0 or blocking_reason_count < 1
        ):
            raise IndependentEvaluationError("blocked readiness accounting is invalid")
        return IndependentEvaluationSummary(
            status=_string(report["status"], "readiness status"),
            compatible_target_count=compatible_target_count,
            evaluator_receipt_verified=False,
            blocking_reason_count=blocking_reason_count,
            receipt_path=receipt_path,
        )
