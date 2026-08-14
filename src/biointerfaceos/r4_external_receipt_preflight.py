"""Preflight R4 external receipts without accepting scientific claims.

The verifier checks bytes, schema, declared safeguards and required result
fields.  It deliberately cannot authenticate a real-world identity or prove
independence; those remain editorial checks performed after a real submission.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


class R4ExternalReceiptPreflightError(RuntimeError):
    """Raised when an R4 external receipt bundle is structurally invalid."""


@dataclass(frozen=True)
class R4ExternalReceiptPreflightSummary:
    """Structural summary that never promotes external evidence."""

    status: str
    bundle_id: str
    document_count: int
    non_author_declared_count: int
    receipt_path: Path


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise R4ExternalReceiptPreflightError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise R4ExternalReceiptPreflightError(f"{label} must be a non-empty string")
    return value.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any, label: str, *, length: int = 64) -> str:
    result = _string(value, label)
    if len(result) != length or any(character not in "0123456789abcdef" for character in result):
        raise R4ExternalReceiptPreflightError(f"{label} must be lowercase hexadecimal")
    return result


def _string_list(value: Any, label: str, *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R4ExternalReceiptPreflightError(f"{label} must contain at least {minimum} item(s)")
    return [_string(item, label) for item in value]


class R4ExternalReceiptPreflightWorkflow:
    """Validate a submitted R4 receipt bundle without accepting it."""

    PROTOCOL_ID = "bioif-r4-external-evaluator-and-reproduction-v1.0.0"
    FIXED_RELEASE = {
        "repository": "https://github.com/ahvsjags/BioInterfaceOS",
        "tag": "v0.1.3-r10.26",
        "manifest_path": "release/empirical_candidate_v0.1.3-r10.26/release_manifest.json",
    }
    STATUS = "STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW"
    DOCUMENT_TYPES = (
        "independent_evaluator_receipt",
        "external_reproduction_receipt",
        "external_user_adoption_receipt_01",
        "external_user_adoption_receipt_02",
    )
    BUNDLE_FIELDS = {
        "schema_version",
        "submission_state",
        "bundle_id",
        "submitted_at",
        "evidence_class",
        "allowed_claim_level",
        "identity_and_scope_audit_pending",
        "scientific_submission_ready",
        "fixed_release",
        "documents",
    }
    DOCUMENT_FIELDS = {"document_type", "relative_path", "sha256", "role_not_author_declared"}
    PERSON_FIELDS = {
        "identity",
        "institution",
        "contact",
        "conflict_disclosure",
        "author_team_membership",
    }
    ATTESTATION_FIELDS = {"signed_attestation", "signature_fingerprint", "signed_at"}

    def __init__(
        self,
        bundle_path: Path,
        documents_root: Path,
        receipt_out: Path,
        repository_root: Path | None = None,
    ) -> None:
        self.bundle_path = bundle_path.resolve(strict=False)
        self.documents_root = documents_root.resolve(strict=False)
        self.receipt_out = receipt_out.resolve(strict=False)
        self.repository_root = (
            repository_root.resolve(strict=False) if repository_root is not None else None
        )

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4ExternalReceiptPreflightError(f"cannot parse {label}") from exc
        return _mapping(value, label)

    @staticmethod
    def _exact(value: Any, expected: set[str], label: str) -> dict[str, Any]:
        result = _mapping(value, label)
        if set(result) != expected:
            raise R4ExternalReceiptPreflightError(f"{label} fields are incomplete or unexpected")
        return result

    @staticmethod
    def _timestamp(value: Any, label: str) -> str:
        text = _string(value, label)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise R4ExternalReceiptPreflightError(f"{label} must be RFC3339") from exc
        if parsed.tzinfo is None:
            raise R4ExternalReceiptPreflightError(f"{label} must include a timezone")
        return text

    @classmethod
    def _fixed_release(cls, value: Any) -> dict[str, str]:
        fixed = _mapping(value, "fixed release")
        expected_fields = set(cls.FIXED_RELEASE) | {
            "commit",
            "source_commit",
            "manifest_sha256",
        }
        if set(fixed) != expected_fields:
            raise R4ExternalReceiptPreflightError(
                "fixed release fields are incomplete or unexpected"
            )
        for key, expected in cls.FIXED_RELEASE.items():
            if fixed[key] != expected:
                raise R4ExternalReceiptPreflightError(
                    "bundle is not bound to the current immutable r10.26 release"
                )
        for key in {"commit", "source_commit"}:
            _digest(fixed[key], f"fixed release {key}", length=40)
        _digest(fixed["manifest_sha256"], "fixed release manifest_sha256")
        return {key: str(item) for key, item in fixed.items()}

    @classmethod
    def _assert_fixed_checkout(
        cls, value: Any, label: str, fixed_release: Mapping[str, str]
    ) -> None:
        if value != fixed_release["commit"]:
            raise R4ExternalReceiptPreflightError(
                f"{label} checkout_commit is not the fixed r10.26 release commit"
            )

    def _assert_repository_anchor(self, fixed_release: Mapping[str, str]) -> None:
        if self.repository_root is None:
            return
        try:
            actual_commit = subprocess.check_output(
                ["git", "rev-parse", f"{fixed_release['tag']}^{{}}"],
                cwd=self.repository_root,
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise R4ExternalReceiptPreflightError(
                "repository root cannot resolve the fixed release tag"
            ) from exc
        if actual_commit != fixed_release["commit"]:
            raise R4ExternalReceiptPreflightError(
                "repository checkout does not resolve to the fixed release tag"
            )
        manifest_path = self.repository_root / Path(
            *PurePosixPath(fixed_release["manifest_path"]).parts
        )
        if not manifest_path.is_file() or _sha256(manifest_path) != fixed_release["manifest_sha256"]:
            raise R4ExternalReceiptPreflightError(
                "repository release manifest does not match the fixed release"
            )
        try:
            manifest = self._json(manifest_path, "fixed release manifest")
        except R4ExternalReceiptPreflightError:
            raise
        if manifest.get("source_commit") != fixed_release["source_commit"]:
            raise R4ExternalReceiptPreflightError(
                "fixed release manifest source_commit differs"
            )

    def _document_path(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4ExternalReceiptPreflightError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4ExternalReceiptPreflightError(f"{label} escapes documents root")
        path = (self.documents_root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.documents_root) or not path.is_file():
            raise R4ExternalReceiptPreflightError(f"{label} is missing or outside documents root")
        return path

    @classmethod
    def _person(cls, value: Any, label: str) -> dict[str, Any]:
        person = cls._exact(value, cls.PERSON_FIELDS, label)
        for field in cls.PERSON_FIELDS - {"author_team_membership"}:
            _string(person[field], f"{label} {field}")
        if person["author_team_membership"] is not False:
            raise R4ExternalReceiptPreflightError(f"{label} declares author-team membership")
        return person

    @classmethod
    def _attestation(cls, value: Any, label: str) -> None:
        attestation = cls._exact(value, cls.ATTESTATION_FIELDS, label)
        _string(attestation["signed_attestation"], f"{label} signed attestation")
        _string(attestation["signature_fingerprint"], f"{label} signature fingerprint")
        cls._timestamp(attestation["signed_at"], f"{label} signed_at")

    @classmethod
    def _failure_records(cls, value: Any, label: str) -> None:
        if not isinstance(value, list) or not value:
            raise R4ExternalReceiptPreflightError(
                f"{label} must contain failures and/or negative runs"
            )
        for index, item in enumerate(value, start=1):
            row = _mapping(item, f"{label} {index}")
            if set(row) != {"run_id", "status", "detail"}:
                raise R4ExternalReceiptPreflightError(f"{label} {index} fields are invalid")
            for field in row:
                _string(row[field], f"{label} {index} {field}")

    @classmethod
    def _deviations(cls, value: Any) -> None:
        if not isinstance(value, list) or not value:
            raise R4ExternalReceiptPreflightError("deviation_ledger must not be empty")
        for index, item in enumerate(value, start=1):
            row = _mapping(item, f"deviation_ledger {index}")
            if set(row) != {"deviation_id", "severity", "detail"}:
                raise R4ExternalReceiptPreflightError("deviation record fields are invalid")
            for field in row:
                _string(row[field], f"deviation_ledger {index} {field}")

    @classmethod
    def _frozen_bundle(cls, value: Any, label: str) -> dict[str, Any]:
        fields = {
            "checkout_commit",
            "protocol_sha256",
            "environment_digest",
            "dependency_lockfile_sha256",
            "input_manifest_sha256_or_protected_data_attestation",
        }
        frozen = cls._exact(value, fields, label)
        _digest(frozen["checkout_commit"], f"{label} checkout_commit", length=40)
        for field in {"protocol_sha256", "environment_digest", "dependency_lockfile_sha256"}:
            _digest(frozen[field], f"{label} {field}")
        _string(
            frozen["input_manifest_sha256_or_protected_data_attestation"],
            f"{label} input manifest or protected-data attestation",
        )
        return frozen

    @classmethod
    def _aggregate_results(cls, value: Any, label: str) -> None:
        required = {
            "primary_endpoint",
            "cluster_aware_uncertainty",
            "effective_counts",
            "paired_ablation",
            "negative_control",
            "model_results",
        }
        results = cls._exact(value, required, label)
        for field in required:
            if not isinstance(results[field], Mapping) or not results[field]:
                raise R4ExternalReceiptPreflightError(f"{label} {field} must be non-empty")

    @classmethod
    def _evaluator(cls, value: Any, fixed_release: Mapping[str, str]) -> None:
        fields = {
            "schema_version",
            "receipt_id",
            "protocol_id",
            "evaluator",
            "independence_safeguards",
            "frozen_bundle",
            "commands_and_scope",
            "aggregate_results",
            "failure_and_negative_runs",
            "deviation_ledger",
            "attestation",
            "raw_values_included",
            "author_accessed_protected_observations",
            "post_freeze_tuning",
            "immutable_archive_locator",
        }
        receipt = cls._exact(value, fields, "independent evaluator receipt")
        if receipt["schema_version"] != 1 or receipt["protocol_id"] != cls.PROTOCOL_ID:
            raise R4ExternalReceiptPreflightError("evaluator protocol identity is invalid")
        _string(receipt["receipt_id"], "evaluator receipt_id")
        cls._person(receipt["evaluator"], "evaluator")
        safeguards = cls._exact(
            receipt["independence_safeguards"],
            {
                "protected_input_held_by_evaluator",
                "author_row_level_access",
                "aggregate_receipt_only",
            },
            "evaluator independence safeguards",
        )
        if safeguards != {
            "protected_input_held_by_evaluator": True,
            "author_row_level_access": False,
            "aggregate_receipt_only": True,
        }:
            raise R4ExternalReceiptPreflightError("evaluator safeguards are insufficient")
        frozen = cls._frozen_bundle(receipt["frozen_bundle"], "evaluator frozen bundle")
        cls._assert_fixed_checkout(frozen["checkout_commit"], "evaluator", fixed_release)
        _string_list(receipt["commands_and_scope"], "evaluator commands_and_scope")
        cls._aggregate_results(receipt["aggregate_results"], "evaluator aggregate_results")
        cls._failure_records(
            receipt["failure_and_negative_runs"], "evaluator failure_and_negative_runs"
        )
        cls._deviations(receipt["deviation_ledger"])
        cls._attestation(receipt["attestation"], "evaluator attestation")
        if (
            receipt["raw_values_included"] is not False
            or receipt["author_accessed_protected_observations"] is not False
            or receipt["post_freeze_tuning"] is not False
        ):
            raise R4ExternalReceiptPreflightError(
                "evaluator receipt weakens protected-data safeguards"
            )
        _string(receipt["immutable_archive_locator"], "evaluator immutable archive locator")

    @classmethod
    def _reproduction(cls, value: Any, fixed_release: Mapping[str, str]) -> None:
        fields = {
            "schema_version",
            "receipt_id",
            "protocol_id",
            "reproduction_team",
            "source_data_attestation",
            "frozen_bundle",
            "commands_and_scope",
            "aggregate_results",
            "failure_and_negative_runs",
            "deviation_ledger",
            "attestation",
            "raw_values_included",
            "author_accessed_protected_observations",
            "immutable_archive_locator",
        }
        receipt = cls._exact(value, fields, "external reproduction receipt")
        if receipt["schema_version"] != 1 or receipt["protocol_id"] != cls.PROTOCOL_ID:
            raise R4ExternalReceiptPreflightError("reproduction protocol identity is invalid")
        _string(receipt["receipt_id"], "reproduction receipt_id")
        cls._person(receipt["reproduction_team"], "reproduction team")
        attestation = cls._exact(
            receipt["source_data_attestation"],
            {"method", "statement"},
            "source data attestation",
        )
        if _string(attestation["method"], "source data attestation method") not in {
            "REACQUIRED",
            "ATTESTED",
        }:
            raise R4ExternalReceiptPreflightError("source data attestation method is invalid")
        _string(attestation["statement"], "source data attestation statement")
        frozen = cls._frozen_bundle(receipt["frozen_bundle"], "reproduction frozen bundle")
        cls._assert_fixed_checkout(frozen["checkout_commit"], "reproduction", fixed_release)
        _string_list(receipt["commands_and_scope"], "reproduction commands_and_scope")
        cls._aggregate_results(receipt["aggregate_results"], "reproduction aggregate_results")
        cls._failure_records(
            receipt["failure_and_negative_runs"], "reproduction failure_and_negative_runs"
        )
        cls._deviations(receipt["deviation_ledger"])
        cls._attestation(receipt["attestation"], "reproduction attestation")
        if (
            receipt["raw_values_included"] is not False
            or receipt["author_accessed_protected_observations"] is not False
        ):
            raise R4ExternalReceiptPreflightError("reproduction receipt includes protected values")
        _string(receipt["immutable_archive_locator"], "reproduction immutable archive locator")

    @classmethod
    def _adoption(cls, value: Any, fixed_release: Mapping[str, str]) -> None:
        fields = {
            "schema_version",
            "receipt_id",
            "protocol_id",
            "user",
            "task_description",
            "input_provenance",
            "checkout_commit",
            "environment_digest",
            "dependency_lockfile_sha256",
            "commands",
            "output_hashes",
            "successes_and_failures",
            "limitations_feedback",
            "public_summary_consent",
            "attestation",
            "immutable_archive_locator",
        }
        receipt = cls._exact(value, fields, "external user adoption receipt")
        if receipt["schema_version"] != 1 or receipt["protocol_id"] != cls.PROTOCOL_ID:
            raise R4ExternalReceiptPreflightError("adoption protocol identity is invalid")
        _string(receipt["receipt_id"], "adoption receipt_id")
        cls._person(receipt["user"], "external user")
        for field in {"task_description", "input_provenance", "limitations_feedback"}:
            _string(receipt[field], f"adoption {field}")
        _digest(receipt["checkout_commit"], "adoption checkout_commit", length=40)
        cls._assert_fixed_checkout(receipt["checkout_commit"], "adoption", fixed_release)
        _digest(receipt["environment_digest"], "adoption environment_digest")
        _digest(receipt["dependency_lockfile_sha256"], "adoption dependency_lockfile_sha256")
        _string_list(receipt["commands"], "adoption commands")
        hashes = receipt["output_hashes"]
        if not isinstance(hashes, Mapping) or not hashes:
            raise R4ExternalReceiptPreflightError("adoption output_hashes must be non-empty")
        for name, digest in hashes.items():
            _string(name, "adoption output hash name")
            _digest(digest, f"adoption output hash {name}")
        cls._failure_records(receipt["successes_and_failures"], "adoption successes_and_failures")
        if receipt["public_summary_consent"] is not True:
            raise R4ExternalReceiptPreflightError("adoption public summary consent is missing")
        cls._attestation(receipt["attestation"], "adoption attestation")
        _string(receipt["immutable_archive_locator"], "adoption immutable archive locator")

    def _bundle(
        self,
    ) -> tuple[
        dict[str, Any],
        dict[str, str],
        dict[str, dict[str, Any]],
        dict[str, Path],
    ]:
        if not self.bundle_path.is_file() or not self.documents_root.is_dir():
            raise R4ExternalReceiptPreflightError("bundle or documents root is missing")
        bundle = self._json(self.bundle_path, "R4 external receipt bundle")
        if set(bundle) != self.BUNDLE_FIELDS or bundle["schema_version"] != 1:
            raise R4ExternalReceiptPreflightError("R4 bundle fields are invalid")
        if bundle["submission_state"] != "SUBMITTED_FOR_PREFLIGHT":
            raise R4ExternalReceiptPreflightError("bundle is not submitted for preflight")
        _string(bundle["bundle_id"], "bundle_id")
        self._timestamp(bundle["submitted_at"], "submitted_at")
        if (
            bundle["evidence_class"] != "DEVELOPMENT_OBSERVATION"
            or bundle["allowed_claim_level"] != "EXPLORATORY"
            or bundle["identity_and_scope_audit_pending"] is not True
            or bundle["scientific_submission_ready"] is not False
        ):
            raise R4ExternalReceiptPreflightError("bundle evidence boundary is invalid")
        fixed_release = self._fixed_release(bundle["fixed_release"])
        self._assert_repository_anchor(fixed_release)
        documents = bundle["documents"]
        if not isinstance(documents, list) or len(documents) != len(self.DOCUMENT_TYPES):
            raise R4ExternalReceiptPreflightError("bundle document count is invalid")
        parsed: dict[str, dict[str, Any]] = {}
        paths: dict[str, Path] = {}
        for item_value in documents:
            item = self._exact(item_value, self.DOCUMENT_FIELDS, "R4 external document")
            document_type = _string(item["document_type"], "document_type")
            if document_type not in self.DOCUMENT_TYPES or document_type in parsed:
                raise R4ExternalReceiptPreflightError("bundle document types are invalid")
            if item["role_not_author_declared"] is not True:
                raise R4ExternalReceiptPreflightError(f"{document_type} is not declared non-author")
            path = self._document_path(
                _string(item["relative_path"], f"{document_type} path"), document_type
            )
            expected = _digest(item["sha256"], f"{document_type} checksum")
            if _sha256(path) != expected:
                raise R4ExternalReceiptPreflightError(f"{document_type} checksum differs")
            parsed[document_type] = self._json(path, document_type)
            paths[document_type] = path
        if tuple(parsed) != self.DOCUMENT_TYPES:
            raise R4ExternalReceiptPreflightError("bundle documents are incomplete")
        return bundle, fixed_release, parsed, paths

    @classmethod
    def _adoption_pair(cls, documents: Mapping[str, dict[str, Any]]) -> None:
        first = documents["external_user_adoption_receipt_01"]
        second = documents["external_user_adoption_receipt_02"]
        first_user = first["user"]
        second_user = second["user"]
        if first["receipt_id"] == second["receipt_id"] or (
            first_user["identity"] == second_user["identity"]
            and first_user["institution"] == second_user["institution"]
        ):
            raise R4ExternalReceiptPreflightError(
                "adoption receipts must declare distinct users or institutions"
            )

    def run(self, *, strict: bool = False) -> R4ExternalReceiptPreflightSummary:
        if not strict:
            raise R4ExternalReceiptPreflightError("R4 external receipt preflight requires --strict")
        if self.receipt_out.exists():
            raise R4ExternalReceiptPreflightError("preflight receipt already exists")
        bundle, fixed_release, documents, paths = self._bundle()
        self._evaluator(documents["independent_evaluator_receipt"], fixed_release)
        self._reproduction(documents["external_reproduction_receipt"], fixed_release)
        self._adoption(documents["external_user_adoption_receipt_01"], fixed_release)
        self._adoption(documents["external_user_adoption_receipt_02"], fixed_release)
        self._adoption_pair(documents)
        self.receipt_out.parent.mkdir(parents=True, exist_ok=True)
        receipt = {
            "schema_version": 1,
            "preflight_id": "bioif-r4-external-receipt-preflight-v1.0.0",
            "status": self.STATUS,
            "bundle_id": bundle["bundle_id"],
            "bundle_sha256": _sha256(self.bundle_path),
            "fixed_release": fixed_release,
            "document_sha256": {name: _sha256(path) for name, path in paths.items()},
            "document_count": len(paths),
            "non_author_declared_count": len(paths),
            "identity_authenticated": False,
            "independence_authenticated": False,
            "protected_lockbox_accepted": False,
            "external_scientific_reproduction_accepted": False,
            "external_user_adoption_accepted": False,
            "scientific_submission_ready": False,
            "claim_boundary": (
                "Structural preflight only; editorial identity, independence and scientific "
                "claim acceptance remain open."
            ),
        }
        self.receipt_out.write_text(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        return R4ExternalReceiptPreflightSummary(
            status=self.STATUS,
            bundle_id=str(bundle["bundle_id"]),
            document_count=len(paths),
            non_author_declared_count=len(paths),
            receipt_path=self.receipt_out,
        )

    def verify(self) -> R4ExternalReceiptPreflightSummary:
        """Verify the structural receipt and its referenced submitted bundle."""
        bundle, fixed_release, documents, paths = self._bundle()
        self._evaluator(documents["independent_evaluator_receipt"], fixed_release)
        self._reproduction(documents["external_reproduction_receipt"], fixed_release)
        self._adoption(documents["external_user_adoption_receipt_01"], fixed_release)
        self._adoption(documents["external_user_adoption_receipt_02"], fixed_release)
        self._adoption_pair(documents)
        receipt = self._json(self.receipt_out, "R4 external receipt preflight receipt")
        if (
            receipt.get("status") != self.STATUS
            or receipt.get("bundle_id") != bundle["bundle_id"]
            or receipt.get("bundle_sha256") != _sha256(self.bundle_path)
            or receipt.get("fixed_release") != fixed_release
            or receipt.get("document_sha256")
            != {name: _sha256(path) for name, path in paths.items()}
            or receipt.get("scientific_submission_ready") is not False
            or receipt.get("independence_authenticated") is not False
            or receipt.get("protected_lockbox_accepted") is not False
            or receipt.get("external_scientific_reproduction_accepted") is not False
            or receipt.get("external_user_adoption_accepted") is not False
        ):
            raise R4ExternalReceiptPreflightError(
                "R4 external receipt preflight receipt is invalid"
            )
        return R4ExternalReceiptPreflightSummary(
            status=self.STATUS,
            bundle_id=str(bundle["bundle_id"]),
            document_count=len(paths),
            non_author_declared_count=len(paths),
            receipt_path=self.receipt_out,
        )
