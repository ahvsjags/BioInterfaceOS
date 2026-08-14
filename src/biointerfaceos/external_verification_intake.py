"""Preflight external R2 evaluation, reproduction and editorial records.

The preflight checks supplied file bytes and declared safeguards.  It never
verifies a real-world identity or signature, promotes a scientific conclusion,
or changes the project's acceptance status.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    require_metadata,
)


class ExternalVerificationIntakeError(RuntimeError):
    """Raised when an external verification package cannot enter audit."""


@dataclass(frozen=True)
class ExternalVerificationIntakeSummary:
    """Non-promoting structural result for the three required external records."""

    status: str
    intake_id: str
    document_count: int
    finding_count: int
    declared_open_critical_finding_count: int


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalVerificationIntakeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalVerificationIntakeError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, minimum: int) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise ExternalVerificationIntakeError(f"{label} has too few entries")
    items = [_string(item, label) for item in value]
    if len(items) != len(set(items)):
        raise ExternalVerificationIntakeError(f"{label} contains duplicates")
    return items


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _checksum(value: Any, label: str) -> str:
    checksum = _string(value, label)
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise ExternalVerificationIntakeError(f"{label} must be a lowercase SHA-256")
    return checksum


def _hex(value: Any, label: str, *, length: int) -> str:
    digest = _string(value, label)
    if len(digest) != length or any(character not in "0123456789abcdef" for character in digest):
        raise ExternalVerificationIntakeError(f"{label} must be a lowercase hexadecimal digest")
    return digest


class ExternalVerificationIntakeWorkflow:
    """Validate future external receipts without converting them into acceptance."""

    STATUS = "STRUCTURALLY_COMPLETE_REQUIRES_IDENTITY_AND_SCOPE_AUDIT"
    EVALUATOR = "independent_evaluator_receipt"
    REPRODUCTION = "external_reproduction_receipt"
    EDITORIAL = "editorial_rereview_report"
    DOCUMENT_TYPES = {EVALUATOR, REPRODUCTION, EDITORIAL}
    FINDING_IDS = tuple(f"R2-{number:02d}" for number in range(1, 10))
    CRITICAL_FINDING_IDS = frozenset({"R2-01", "R2-02", "R2-03"})
    REQUIRED_BUNDLE = {
        "schema_version",
        "submission_state",
        "intake_id",
        "submitted_at",
        "evidence_class",
        "allowed_claim_level",
        "identity_and_scope_audit_pending",
        "scientific_submission_ready",
        "documents",
    }
    REQUIRED_DOCUMENT = {"document_type", "relative_path", "sha256", "role_not_author_declared"}
    REQUIRED_EVALUATOR = {
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
    REQUIRED_EVALUATOR_PERSON = {"identity", "institution", "conflict_disclosure"}
    REQUIRED_FROZEN_BUNDLE = {
        "git_commit",
        "environment_lock_sha256",
        "target_registry_sha256",
        "split_manifest_sha256",
        "model_configuration_sha256",
        "prediction_archive_sha256",
        "threshold_ledger_sha256",
    }
    REQUIRED_ATTESTATION = {"signed_attestation", "signature_fingerprint"}
    REQUIRED_REPRODUCTION = {
        "schema_version",
        "report_id",
        "protocol_id",
        "reproduction_team",
        "checkout_commit",
        "environment_digest",
        "source_data_attestation",
        "commands_and_scope",
        "deviation_ledger",
        "result_summary",
        "attestation",
        "raw_protected_values_included",
    }
    REQUIRED_REPRODUCTION_TEAM = {
        "identity",
        "institution",
        "conflict_disclosure",
        "author_team_membership",
    }
    REQUIRED_SOURCE_ATTESTATION = {"method", "statement"}
    REQUIRED_DEVIATION = {"deviation_id", "severity", "detail"}
    REQUIRED_RESULT_SUMMARY = {"scope", "outcome", "aggregate_only"}
    REQUIRED_EDITORIAL = {
        "schema_version",
        "report_id",
        "protocol_id",
        "reviewer",
        "r2_finding_matrix",
        "critical_finding_count",
        "manuscript_dispositions",
        "attestation",
    }
    REQUIRED_EDITOR = {
        "identity",
        "institution",
        "conflict_disclosure",
        "author_team_membership",
    }
    REQUIRED_FINDING = {"finding_id", "disposition", "evidence_or_downgrade_reference"}
    FINDING_DISPOSITIONS = frozenset({"EVIDENCE_LINKED", "EXPLICIT_DOWNGRADE", "OPEN_BLOCKER"})

    def __init__(self, bundle_path: Path, documents_root: Path) -> None:
        self.bundle_path = bundle_path.resolve(strict=False)
        self.documents_root = documents_root.resolve(strict=False)

    @staticmethod
    def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
        result = _mapping(value, label)
        if set(result) != expected:
            raise ExternalVerificationIntakeError(f"{label} fields are incomplete or unexpected")
        return result

    @staticmethod
    def _timestamp(value: Any) -> str:
        submitted_at = _string(value, "submitted_at")
        try:
            parsed = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ExternalVerificationIntakeError("submitted_at must be an RFC3339 timestamp") from exc
        if parsed.tzinfo is None:
            raise ExternalVerificationIntakeError("submitted_at must include a timezone")
        return submitted_at

    def _document_path(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise ExternalVerificationIntakeError(f"{label} must use a relative POSIX path")
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or not pure_path.parts or ".." in pure_path.parts:
            raise ExternalVerificationIntakeError(f"{label} escapes the declared documents root")
        path = (self.documents_root / Path(*pure_path.parts)).resolve(strict=False)
        if not path.is_relative_to(self.documents_root) or not path.is_file():
            raise ExternalVerificationIntakeError(f"{label} is missing or outside the declared documents root")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExternalVerificationIntakeError(f"cannot parse {label}") from exc

    @staticmethod
    def _nonempty_mapping(value: Any, label: str) -> dict[str, Any]:
        result = _mapping(value, label)
        if not result:
            raise ExternalVerificationIntakeError(f"{label} must not be empty")
        return result

    @classmethod
    def _person(cls, value: Any, expected: set[str], label: str) -> None:
        person = cls._exact_keys(value, expected, label)
        for field in {"identity", "institution", "conflict_disclosure"}:
            _string(person[field], f"{label} {field}")
        if "author_team_membership" in expected and person["author_team_membership"] is not False:
            raise ExternalVerificationIntakeError(f"{label} declares author-team membership")

    @classmethod
    def _attestation(cls, value: Any, label: str) -> None:
        attestation = cls._exact_keys(value, cls.REQUIRED_ATTESTATION, label)
        _string(attestation["signed_attestation"], f"{label} signed attestation")
        _string(attestation["signature_fingerprint"], f"{label} signature fingerprint")

    @classmethod
    def _evaluator_receipt(cls, value: dict[str, Any]) -> None:
        receipt = cls._exact_keys(value, cls.REQUIRED_EVALUATOR, "independent evaluator receipt")
        if receipt["schema_version"] != 1:
            raise ExternalVerificationIntakeError("evaluator receipt schema version is invalid")
        _string(receipt["evaluation_id"], "evaluator receipt id")
        if receipt["protocol_id"] != "bioif-r2-independent-evaluation-protocol-v1.0.0":
            raise ExternalVerificationIntakeError("evaluator receipt protocol id is invalid")
        cls._person(receipt["evaluator"], cls.REQUIRED_EVALUATOR_PERSON, "evaluator")
        frozen_bundle = cls._exact_keys(receipt["frozen_bundle"], cls.REQUIRED_FROZEN_BUNDLE, "evaluator frozen bundle")
        _hex(frozen_bundle["git_commit"], "evaluator checkout commit", length=40)
        for field in cls.REQUIRED_FROZEN_BUNDLE - {"git_commit"}:
            _checksum(frozen_bundle[field], f"evaluator frozen bundle {field}")
        cls._attestation(receipt["attestation"], "evaluator attestation")
        cls._nonempty_mapping(receipt["aggregate_metrics"], "aggregate metrics")
        cls._nonempty_mapping(receipt["threshold_statuses"], "threshold statuses")
        _checksum(receipt["environment_digest"], "evaluator environment digest")
        if (
            receipt["raw_values_included"] is not False
            or receipt["author_team_accessed_protected_observations"] is not False
            or receipt["post_freeze_tuning"] is not False
        ):
            raise ExternalVerificationIntakeError("evaluator receipt weakens protected-data safeguards")

    @classmethod
    def _reproduction_receipt(cls, value: dict[str, Any]) -> None:
        receipt = cls._exact_keys(value, cls.REQUIRED_REPRODUCTION, "external reproduction receipt")
        if receipt["schema_version"] != 1:
            raise ExternalVerificationIntakeError("reproduction receipt schema version is invalid")
        _string(receipt["report_id"], "reproduction report id")
        if receipt["protocol_id"] != "bioif-r2-external-reproduction-editorial-protocol-v1.0.0":
            raise ExternalVerificationIntakeError("reproduction receipt protocol id is invalid")
        cls._person(receipt["reproduction_team"], cls.REQUIRED_REPRODUCTION_TEAM, "team")
        _hex(receipt["checkout_commit"], "reproduction checkout commit", length=40)
        _checksum(receipt["environment_digest"], "reproduction environment digest")
        source_attestation = cls._exact_keys(
            receipt["source_data_attestation"],
            cls.REQUIRED_SOURCE_ATTESTATION,
            "source-data attestation",
        )
        if _string(source_attestation["method"], "source-data attestation method") not in {
            "REACQUIRED",
            "ATTESTED",
        }:
            raise ExternalVerificationIntakeError("source-data attestation method is invalid")
        _string(source_attestation["statement"], "source-data attestation statement")
        _string_list(receipt["commands_and_scope"], "commands and scope", minimum=1)
        deviations = receipt["deviation_ledger"]
        if not isinstance(deviations, list) or not deviations:
            raise ExternalVerificationIntakeError("deviation ledger must not be empty")
        for value in deviations:
            deviation = cls._exact_keys(value, cls.REQUIRED_DEVIATION, "deviation record")
            for field in cls.REQUIRED_DEVIATION:
                _string(deviation[field], f"deviation {field}")
        summary = cls._exact_keys(receipt["result_summary"], cls.REQUIRED_RESULT_SUMMARY, "reproduction result summary")
        _string(summary["scope"], "reproduction result scope")
        _string(summary["outcome"], "reproduction result outcome")
        if summary["aggregate_only"] is not True or receipt["raw_protected_values_included"] is not False:
            raise ExternalVerificationIntakeError("reproduction receipt includes protected raw values")
        cls._attestation(receipt["attestation"], "reproduction attestation")

    @classmethod
    def _editorial_report(cls, value: dict[str, Any]) -> int:
        report = cls._exact_keys(value, cls.REQUIRED_EDITORIAL, "editorial re-review report")
        if report["schema_version"] != 1:
            raise ExternalVerificationIntakeError("editorial report schema version is invalid")
        _string(report["report_id"], "editorial report id")
        if report["protocol_id"] != "bioif-r2-external-reproduction-editorial-protocol-v1.0.0":
            raise ExternalVerificationIntakeError("editorial report protocol id is invalid")
        cls._person(report["reviewer"], cls.REQUIRED_EDITOR, "editorial reviewer")
        findings = report["r2_finding_matrix"]
        if not isinstance(findings, list) or len(findings) != len(cls.FINDING_IDS):
            raise ExternalVerificationIntakeError("editorial finding matrix has the wrong size")
        dispositions: dict[str, str] = {}
        for value in findings:
            finding = cls._exact_keys(value, cls.REQUIRED_FINDING, "editorial finding")
            finding_id = _string(finding["finding_id"], "editorial finding id")
            disposition = _string(finding["disposition"], f"{finding_id} disposition")
            _string(
                finding["evidence_or_downgrade_reference"],
                f"{finding_id} evidence or downgrade reference",
            )
            if finding_id in dispositions or disposition not in cls.FINDING_DISPOSITIONS:
                raise ExternalVerificationIntakeError("editorial finding matrix is invalid")
            dispositions[finding_id] = disposition
        if tuple(dispositions) != cls.FINDING_IDS:
            raise ExternalVerificationIntakeError("editorial finding matrix does not cover R2-01 through R2-09")
        critical_count = report["critical_finding_count"]
        if isinstance(critical_count, bool) or not isinstance(critical_count, int) or critical_count < 0:
            raise ExternalVerificationIntakeError("critical finding count is invalid")
        expected_critical_count = sum(
            dispositions[finding_id] == "OPEN_BLOCKER" for finding_id in cls.CRITICAL_FINDING_IDS
        )
        if critical_count != expected_critical_count:
            raise ExternalVerificationIntakeError("critical finding count does not match the finding matrix")
        _string_list(report["manuscript_dispositions"], "manuscript dispositions", minimum=1)
        cls._attestation(report["attestation"], "editorial attestation")
        return int(critical_count)

    def _bundle(self) -> dict[str, Any]:
        if not self.bundle_path.is_file():
            raise ExternalVerificationIntakeError("external verification bundle is missing")
        if not self.documents_root.is_dir():
            raise ExternalVerificationIntakeError("external verification documents root is missing")
        bundle = self._json(self.bundle_path, "external verification bundle")
        bundle = self._exact_keys(bundle, self.REQUIRED_BUNDLE, "external verification bundle")
        if bundle["schema_version"] != 1:
            raise ExternalVerificationIntakeError("external verification bundle schema version is invalid")
        if bundle["submission_state"] != "SUBMITTED_FOR_PREFLIGHT":
            raise ExternalVerificationIntakeError("external verification bundle is not submitted")
        if bundle["identity_and_scope_audit_pending"] is not True or bundle["scientific_submission_ready"] is not False:
            raise ExternalVerificationIntakeError("external verification bundle attempts acceptance")
        _string(bundle["intake_id"], "external verification intake id")
        self._timestamp(bundle["submitted_at"])
        try:
            evidence_class, claim_level = require_metadata(bundle, "external verification bundle")
        except EvidenceSemanticsError as exc:
            raise ExternalVerificationIntakeError("external verification bundle metadata is invalid") from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise ExternalVerificationIntakeError("external verification bundle claim level is invalid")
        documents = bundle["documents"]
        if not isinstance(documents, list) or len(documents) != len(self.DOCUMENT_TYPES):
            raise ExternalVerificationIntakeError("external verification bundle document count is invalid")
        parsed: dict[str, dict[str, Any]] = {}
        for value in documents:
            document = self._exact_keys(value, self.REQUIRED_DOCUMENT, "external verification document")
            document_type = _string(document["document_type"], "external verification document type")
            if document_type not in self.DOCUMENT_TYPES or document_type in parsed:
                raise ExternalVerificationIntakeError("external verification document types are invalid")
            if document["role_not_author_declared"] is not True:
                raise ExternalVerificationIntakeError(f"{document_type} does not declare a non-author role")
            document_path = self._document_path(
                _string(document["relative_path"], f"{document_type} path"),
                f"{document_type} path",
            )
            expected_checksum = _checksum(document["sha256"], f"{document_type} checksum")
            if _sha256(document_path) != expected_checksum:
                raise ExternalVerificationIntakeError(f"{document_type} checksum does not match bytes")
            parsed[document_type] = self._json(document_path, document_type)
        if set(parsed) != self.DOCUMENT_TYPES:
            raise ExternalVerificationIntakeError("external verification documents are incomplete")
        return {"bundle": bundle, "documents": parsed}

    def run(self, *, strict: bool = False) -> ExternalVerificationIntakeSummary:
        """Check a supplied verification bundle without promoting its claims."""
        if not strict:
            raise ExternalVerificationIntakeError("external verification preflight requires --strict")
        parsed = self._bundle()
        documents = parsed["documents"]
        self._evaluator_receipt(documents[self.EVALUATOR])
        self._reproduction_receipt(documents[self.REPRODUCTION])
        critical_count = self._editorial_report(documents[self.EDITORIAL])
        return ExternalVerificationIntakeSummary(
            status=self.STATUS,
            intake_id=_string(parsed["bundle"]["intake_id"], "external verification intake id"),
            document_count=len(documents),
            finding_count=len(self.FINDING_IDS),
            declared_open_critical_finding_count=critical_count,
        )
