"""Verify externally supplied R2 receipt signatures against an approved key registry.

This module deliberately has a narrow evidentiary role.  It verifies that the
three already-preflighted documents were signed by three registered OpenPGP
keys.  It cannot establish the real-world identity, independence, authority or
scientific validity of a person possessing such a key.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
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
from biointerfaceos.external_verification_intake import (
    ExternalVerificationIntakeError,
    ExternalVerificationIntakeWorkflow,
)


class ExternalVerificationSignatureError(RuntimeError):
    """Raised when a signed external verification package is not admissible."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalVerificationSignatureError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalVerificationSignatureError(f"{label} must be a non-empty string")
    return value.strip()


def _checksum(value: Any, label: str) -> str:
    checksum = _string(value, label)
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise ExternalVerificationSignatureError(f"{label} must be a lowercase SHA-256")
    return checksum


def _fingerprint(value: Any, label: str) -> str:
    fingerprint = _string(value, label).lower()
    if len(fingerprint) != 40 or any(
        character not in "0123456789abcdef" for character in fingerprint
    ):
        raise ExternalVerificationSignatureError(
            f"{label} must be a 40-character OpenPGP primary-key fingerprint"
        )
    return fingerprint


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _timestamp(value: Any, label: str) -> str:
    timestamp = _string(value, label)
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalVerificationSignatureError(f"{label} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ExternalVerificationSignatureError(f"{label} must include a timezone")
    return timestamp


@dataclass(frozen=True)
class ExternalVerificationSignatureSummary:
    """Non-accepting receipt for the cryptographic portion of external review."""

    status: str
    verification_id: str
    verified_document_count: int
    verified_signer_count: int
    receipt_path: Path


class ExternalVerificationSignatureWorkflow:
    """Fail closed unless detached signatures match independently registered keys."""

    STATUS = "CRYPTOGRAPHIC_SIGNATURES_VERIFIED_REQUIRES_IDENTITY_SCOPE_AND_SCIENTIFIC_AUDIT"
    DOCUMENT_TYPES = (
        "independent_evaluator_receipt",
        "external_reproduction_receipt",
        "editorial_rereview_report",
    )
    REQUIRED_SIGNATURE_MANIFEST = {
        "schema_version",
        "verification_id",
        "verified_at",
        "evidence_class",
        "allowed_claim_level",
        "bundle_sha256",
        "signatures",
    }
    REQUIRED_SIGNATURE = {"document_type", "signature_relative_path"}
    REQUIRED_TRUST_REGISTRY = {
        "schema_version",
        "registry_id",
        "approved_at",
        "approval_scope",
        "signers",
    }
    REQUIRED_SIGNER = {
        "document_type",
        "signer_key_fingerprint",
        "public_key_relative_path",
        "public_key_sha256",
    }

    def __init__(
        self,
        *,
        bundle_path: Path,
        documents_root: Path,
        signature_manifest_path: Path,
        signatures_root: Path,
        trusted_signer_registry_path: Path,
        trusted_keys_root: Path,
        receipt_path: Path,
        gpg_binary: str = "gpg",
        gpgv_binary: str = "gpgv",
    ) -> None:
        self.bundle_path = bundle_path.resolve(strict=False)
        self.documents_root = documents_root.resolve(strict=False)
        self.signature_manifest_path = signature_manifest_path.resolve(strict=False)
        self.signatures_root = signatures_root.resolve(strict=False)
        self.trusted_signer_registry_path = trusted_signer_registry_path.resolve(strict=False)
        self.trusted_keys_root = trusted_keys_root.resolve(strict=False)
        self.receipt_path = receipt_path.resolve(strict=False)
        self.gpg_binary = gpg_binary
        self.gpgv_binary = gpgv_binary

    @staticmethod
    def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
        result = _mapping(value, label)
        if set(result) != expected:
            raise ExternalVerificationSignatureError(f"{label} fields are incomplete or unexpected")
        return result

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExternalVerificationSignatureError(f"cannot parse {label}") from exc

    @staticmethod
    def _file(path: Path, label: str) -> Path:
        if not path.is_file():
            raise ExternalVerificationSignatureError(f"{label} is missing")
        return path

    @staticmethod
    def _directory(path: Path, label: str) -> Path:
        if not path.is_dir():
            raise ExternalVerificationSignatureError(f"{label} is missing")
        return path

    @staticmethod
    def _relative_file(root: Path, relative_path: Any, label: str) -> Path:
        raw_path = _string(relative_path, label)
        if "\\" in raw_path:
            raise ExternalVerificationSignatureError(f"{label} must use a relative POSIX path")
        pure_path = PurePosixPath(raw_path)
        if pure_path.is_absolute() or not pure_path.parts or ".." in pure_path.parts:
            raise ExternalVerificationSignatureError(f"{label} escapes its declared root")
        path = (root / Path(*pure_path.parts)).resolve(strict=False)
        if not path.is_relative_to(root) or not path.is_file():
            raise ExternalVerificationSignatureError(
                f"{label} is missing or outside its declared root"
            )
        return path

    @staticmethod
    def _attestation_fingerprint(document: dict[str, Any], label: str) -> str:
        try:
            attestation = _mapping(document["attestation"], f"{label} attestation")
        except KeyError as exc:
            raise ExternalVerificationSignatureError(f"{label} has no attestation") from exc
        return _fingerprint(
            attestation.get("signature_fingerprint"), f"{label} signature fingerprint"
        )

    @staticmethod
    def _run(command: Sequence[str], label: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError as exc:
            raise ExternalVerificationSignatureError(f"{label} executable is unavailable") from exc
        except subprocess.TimeoutExpired as exc:
            raise ExternalVerificationSignatureError(f"{label} timed out") from exc

    def _signature_manifest(self) -> tuple[dict[str, Any], dict[str, Path]]:
        manifest = self._exact_keys(
            self._json(
                self._file(self.signature_manifest_path, "signature manifest"), "signature manifest"
            ),
            self.REQUIRED_SIGNATURE_MANIFEST,
            "signature manifest",
        )
        if manifest["schema_version"] != 1:
            raise ExternalVerificationSignatureError("signature manifest schema version is invalid")
        _string(manifest["verification_id"], "signature verification id")
        _timestamp(manifest["verified_at"], "signature verification time")
        try:
            evidence_class, claim_level = require_metadata(manifest, "signature manifest")
        except EvidenceSemanticsError as exc:
            raise ExternalVerificationSignatureError(
                "signature manifest metadata is invalid"
            ) from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise ExternalVerificationSignatureError("signature manifest claim level is invalid")
        if _checksum(manifest["bundle_sha256"], "signature manifest bundle checksum") != _sha256(
            self._file(self.bundle_path, "external verification bundle")
        ):
            raise ExternalVerificationSignatureError(
                "signature manifest is not bound to the bundle bytes"
            )
        entries = manifest["signatures"]
        if not isinstance(entries, list) or len(entries) != len(self.DOCUMENT_TYPES):
            raise ExternalVerificationSignatureError(
                "signature manifest has the wrong signature count"
            )
        signature_paths: dict[str, Path] = {}
        for value in entries:
            entry = self._exact_keys(value, self.REQUIRED_SIGNATURE, "signature manifest entry")
            document_type = _string(entry["document_type"], "signature document type")
            if document_type not in self.DOCUMENT_TYPES or document_type in signature_paths:
                raise ExternalVerificationSignatureError(
                    "signature manifest document types are invalid"
                )
            signature_paths[document_type] = self._relative_file(
                self._directory(self.signatures_root, "signatures root"),
                entry["signature_relative_path"],
                f"{document_type} detached signature",
            )
        if tuple(signature_paths) != self.DOCUMENT_TYPES:
            raise ExternalVerificationSignatureError(
                "signature manifest does not cover all document types"
            )
        return manifest, signature_paths

    def _trusted_signers(self) -> dict[str, dict[str, Any]]:
        registry = self._exact_keys(
            self._json(
                self._file(self.trusted_signer_registry_path, "trusted signer registry"),
                "trusted signer registry",
            ),
            self.REQUIRED_TRUST_REGISTRY,
            "trusted signer registry",
        )
        if registry["schema_version"] != 1:
            raise ExternalVerificationSignatureError(
                "trusted signer registry schema version is invalid"
            )
        _string(registry["registry_id"], "trusted signer registry id")
        _timestamp(registry["approved_at"], "trusted signer registry approval time")
        _string(registry["approval_scope"], "trusted signer registry approval scope")
        values = registry["signers"]
        if not isinstance(values, list) or len(values) != len(self.DOCUMENT_TYPES):
            raise ExternalVerificationSignatureError(
                "trusted signer registry has the wrong signer count"
            )
        trusted_root = self._directory(self.trusted_keys_root, "trusted keys root")
        signers: dict[str, dict[str, Any]] = {}
        fingerprints: set[str] = set()
        for value in values:
            signer = self._exact_keys(value, self.REQUIRED_SIGNER, "trusted signer entry")
            document_type = _string(signer["document_type"], "trusted signer document type")
            if document_type not in self.DOCUMENT_TYPES or document_type in signers:
                raise ExternalVerificationSignatureError(
                    "trusted signer document types are invalid"
                )
            fingerprint = _fingerprint(
                signer["signer_key_fingerprint"], "trusted signer fingerprint"
            )
            if fingerprint in fingerprints:
                raise ExternalVerificationSignatureError(
                    "each external role must use a distinct trusted signing key"
                )
            fingerprints.add(fingerprint)
            key_path = self._relative_file(
                trusted_root,
                signer["public_key_relative_path"],
                f"{document_type} trusted public key",
            )
            if _checksum(signer["public_key_sha256"], "trusted public-key checksum") != _sha256(
                key_path
            ):
                raise ExternalVerificationSignatureError(
                    f"{document_type} trusted public-key checksum does not match bytes"
                )
            signers[document_type] = {**signer, "key_path": key_path, "fingerprint": fingerprint}
        if tuple(signers) != self.DOCUMENT_TYPES:
            raise ExternalVerificationSignatureError(
                "trusted signer registry does not cover all roles"
            )
        return signers

    def _public_key_fingerprint(self, key_path: Path, home: Path) -> str:
        result = self._run(
            [
                self.gpg_binary,
                "--batch",
                "--no-options",
                "--homedir",
                str(home),
                "--with-colons",
                "--import-options",
                "show-only",
                "--dry-run",
                "--import",
                str(key_path),
            ],
            "OpenPGP public-key inspection",
        )
        if result.returncode != 0:
            raise ExternalVerificationSignatureError("trusted public key cannot be inspected")
        expecting_primary_fingerprint = False
        for line in result.stdout.splitlines():
            fields = line.split(":")
            if not fields:
                continue
            if fields[0] == "pub":
                expecting_primary_fingerprint = True
            elif fields[0] == "fpr" and expecting_primary_fingerprint and len(fields) > 9:
                return _fingerprint(fields[9], "inspected public-key fingerprint")
        raise ExternalVerificationSignatureError("trusted public key has no primary fingerprint")

    def _import_key(self, key_path: Path, keyring: Path, home: Path) -> None:
        result = self._run(
            [
                self.gpg_binary,
                "--batch",
                "--no-options",
                "--homedir",
                str(home),
                "--no-default-keyring",
                "--keyring",
                str(keyring),
                "--import",
                str(key_path),
            ],
            "OpenPGP trusted-key import",
        )
        if result.returncode != 0:
            raise ExternalVerificationSignatureError("trusted public key cannot be imported")

    def _verify_signature(
        self,
        *,
        keyring: Path,
        home: Path,
        signature_path: Path,
        document_path: Path,
        expected_fingerprint: str,
        document_type: str,
    ) -> None:
        result = self._run(
            [
                self.gpgv_binary,
                "--homedir",
                str(home),
                "--keyring",
                str(keyring),
                "--status-fd",
                "1",
                str(signature_path),
                str(document_path),
            ],
            f"{document_type} detached-signature verification",
        )
        if result.returncode != 0:
            raise ExternalVerificationSignatureError(
                f"{document_type} detached signature does not verify"
            )
        valid_signatures = []
        for line in result.stdout.splitlines():
            prefix = "[GNUPG:] VALIDSIG "
            if line.startswith(prefix):
                values = line[len(prefix) :].split()
                if len(values) >= 10:
                    valid_signatures.append(values[-1].lower())
        if valid_signatures != [expected_fingerprint]:
            raise ExternalVerificationSignatureError(
                f"{document_type} signature is not bound to its registered primary key"
            )

    def _validated_documents(self) -> dict[str, tuple[Path, dict[str, Any]]]:
        try:
            preflight = ExternalVerificationIntakeWorkflow(self.bundle_path, self.documents_root)
            preflight.run(strict=True)
            parsed = preflight._bundle()
        except ExternalVerificationIntakeError as exc:
            raise ExternalVerificationSignatureError(
                "external verification structural preflight failed"
            ) from exc
        bundle = _mapping(parsed["bundle"], "preflighted external verification bundle")
        parsed_documents = _mapping(parsed["documents"], "preflighted external documents")
        documents: dict[str, tuple[Path, dict[str, Any]]] = {}
        for value in bundle["documents"]:
            entry = _mapping(value, "preflighted document entry")
            document_type = _string(entry["document_type"], "preflighted document type")
            document_path = preflight._document_path(
                entry["relative_path"], f"{document_type} path"
            )
            documents[document_type] = (
                document_path,
                _mapping(parsed_documents[document_type], document_type),
            )
        if tuple(documents) != self.DOCUMENT_TYPES:
            raise ExternalVerificationSignatureError("preflighted documents are incomplete")
        return documents

    def _receipt_target(self) -> Path:
        if self.receipt_path.exists():
            raise ExternalVerificationSignatureError("signature receipt path already exists")
        parent = self.receipt_path.parent
        if not parent.is_dir():
            raise ExternalVerificationSignatureError(
                "signature receipt parent directory is missing"
            )
        for root in (self.documents_root, self.signatures_root, self.trusted_keys_root):
            if self.receipt_path.is_relative_to(root):
                raise ExternalVerificationSignatureError(
                    "signature receipt must not be written into an incoming evidence root"
                )
        return self.receipt_path

    def run(self, *, strict: bool = False) -> ExternalVerificationSignatureSummary:
        """Verify cryptographic provenance without accepting an external result."""
        if not strict:
            raise ExternalVerificationSignatureError(
                "external signature verification requires --strict"
            )
        manifest, signature_paths = self._signature_manifest()
        signers = self._trusted_signers()
        documents = self._validated_documents()
        receipt_path = self._receipt_target()
        if shutil.which(self.gpg_binary) is None or shutil.which(self.gpgv_binary) is None:
            raise ExternalVerificationSignatureError("OpenPGP verifier executables are unavailable")

        with tempfile.TemporaryDirectory(prefix="bioif-r2-signature-") as temporary:
            home = Path(temporary)
            keyring = home / "trustedkeys.kbx"
            for document_type in self.DOCUMENT_TYPES:
                signer = signers[document_type]
                observed_fingerprint = self._public_key_fingerprint(signer["key_path"], home)
                if observed_fingerprint != signer["fingerprint"]:
                    raise ExternalVerificationSignatureError(
                        f"{document_type} public key does not match its registered fingerprint"
                    )
                self._import_key(signer["key_path"], keyring, home)
            for document_type in self.DOCUMENT_TYPES:
                document_path, document = documents[document_type]
                expected_fingerprint = signers[document_type]["fingerprint"]
                if self._attestation_fingerprint(document, document_type) != expected_fingerprint:
                    raise ExternalVerificationSignatureError(
                        f"{document_type} attestation is not bound to its registered key"
                    )
                self._verify_signature(
                    keyring=keyring,
                    home=home,
                    signature_path=signature_paths[document_type],
                    document_path=document_path,
                    expected_fingerprint=expected_fingerprint,
                    document_type=document_type,
                )

        receipt = {
            "schema_version": 1,
            "verification_id": manifest["verification_id"],
            "verified_at": manifest["verified_at"],
            "status": self.STATUS,
            "bundle_sha256": _sha256(self.bundle_path),
            "trusted_signer_registry_sha256": _sha256(self.trusted_signer_registry_path),
            "verified_documents": [
                {
                    "document_type": document_type,
                    "document_sha256": _sha256(documents[document_type][0]),
                    "detached_signature_sha256": _sha256(signature_paths[document_type]),
                    "registered_primary_key_fingerprint": signers[document_type]["fingerprint"],
                }
                for document_type in self.DOCUMENT_TYPES
            ],
            "identity_authenticated": False,
            "independence_authenticated": False,
            "scope_audited": False,
            "scientific_claim_accepted": False,
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        return ExternalVerificationSignatureSummary(
            status=self.STATUS,
            verification_id=manifest["verification_id"],
            verified_document_count=len(self.DOCUMENT_TYPES),
            verified_signer_count=len(self.DOCUMENT_TYPES),
            receipt_path=receipt_path,
        )
