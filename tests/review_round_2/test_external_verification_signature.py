"""Tests for trusted-key verification of external R2 receipt documents."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from biointerfaceos.external_verification_signature import (
    ExternalVerificationSignatureError,
    ExternalVerificationSignatureWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]
GPG_AVAILABLE = shutil.which("gpg") is not None and shutil.which("gpgv") is not None
pytestmark = pytest.mark.skipif(not GPG_AVAILABLE, reason="GnuPG is required for signature tests")

DOCUMENT_TYPES = (
    "independent_evaluator_receipt",
    "external_reproduction_receipt",
    "editorial_rereview_report",
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> str:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return _sha256(path.read_bytes())


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result


def _primary_fingerprint(home: Path) -> str:
    output = _run(["gpg", "--batch", "--homedir", str(home), "--with-colons", "--list-keys"]).stdout
    expecting_primary = False
    for line in output.splitlines():
        fields = line.split(":")
        if fields[0] == "pub":
            expecting_primary = True
        elif fields[0] == "fpr" and expecting_primary:
            return fields[9].lower()
    raise AssertionError("test OpenPGP key has no primary fingerprint")


def _create_signer(root: Path, name: str) -> tuple[Path, str]:
    home = root / f"gpg-{name}"
    home.mkdir()
    _run(
        [
            "gpg",
            "--batch",
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "",
            "--homedir",
            str(home),
            "--quick-generate-key",
            f"T139 {name} <{name}@example.test>",
            "ed25519",
            "sign",
            "0",
        ]
    )
    fingerprint = _primary_fingerprint(home)
    public_key = root / "keys" / f"{name}.asc"
    public_key.parent.mkdir(exist_ok=True)
    _run(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(home),
            "--armor",
            "--output",
            str(public_key),
            "--export",
            fingerprint,
        ]
    )
    return home, fingerprint


def _write_package(tmp_path: Path) -> dict[str, Path | dict[str, str]]:
    signer_homes: dict[str, Path] = {}
    fingerprints: dict[str, str] = {}
    for name, document_type in zip(
        ("evaluator", "reproducer", "editor"), DOCUMENT_TYPES, strict=True
    ):
        signer_homes[document_type], fingerprints[document_type] = _create_signer(tmp_path, name)

    documents_root = tmp_path / "documents"
    documents_root.mkdir()
    frozen_bundle = {
        "git_commit": "a" * 40,
        "environment_lock_sha256": "b" * 64,
        "target_registry_sha256": "c" * 64,
        "split_manifest_sha256": "d" * 64,
        "model_configuration_sha256": "e" * 64,
        "prediction_archive_sha256": "f" * 64,
        "threshold_ledger_sha256": "0" * 64,
    }
    evaluator = {
        "schema_version": 1,
        "evaluation_id": "test-evaluator",
        "protocol_id": "bioif-r2-independent-evaluation-protocol-v1.0.0",
        "evaluator": {
            "identity": "declared external evaluator",
            "institution": "external institution",
            "conflict_disclosure": "no conflict declared",
        },
        "frozen_bundle": frozen_bundle,
        "attestation": {
            "signed_attestation": "test detached signature",
            "signature_fingerprint": fingerprints[DOCUMENT_TYPES[0]],
        },
        "aggregate_metrics": {"aggregate": "only"},
        "threshold_statuses": {"threshold": "declared"},
        "environment_digest": "1" * 64,
        "raw_values_included": False,
        "author_team_accessed_protected_observations": False,
        "post_freeze_tuning": False,
    }
    reproduction = {
        "schema_version": 1,
        "report_id": "test-reproduction",
        "protocol_id": "bioif-r2-external-reproduction-editorial-protocol-v1.0.0",
        "reproduction_team": {
            "identity": "declared external reproducer",
            "institution": "external institution",
            "conflict_disclosure": "no conflict declared",
            "author_team_membership": False,
        },
        "checkout_commit": "2" * 40,
        "environment_digest": "3" * 64,
        "source_data_attestation": {"method": "ATTESTED", "statement": "test attestation"},
        "commands_and_scope": ["test command"],
        "deviation_ledger": [
            {"deviation_id": "NONE", "severity": "NONE", "detail": "test structural record"}
        ],
        "result_summary": {
            "scope": "test scope",
            "outcome": "test outcome",
            "aggregate_only": True,
        },
        "attestation": {
            "signed_attestation": "test detached signature",
            "signature_fingerprint": fingerprints[DOCUMENT_TYPES[1]],
        },
        "raw_protected_values_included": False,
    }
    editorial = {
        "schema_version": 1,
        "report_id": "test-editorial",
        "protocol_id": "bioif-r2-external-reproduction-editorial-protocol-v1.0.0",
        "reviewer": {
            "identity": "declared external editor",
            "institution": "external institution",
            "conflict_disclosure": "no conflict declared",
            "author_team_membership": False,
        },
        "r2_finding_matrix": [
            {
                "finding_id": f"R2-{number:02d}",
                "disposition": "EXPLICIT_DOWNGRADE",
                "evidence_or_downgrade_reference": "test downgrade",
            }
            for number in range(1, 10)
        ],
        "critical_finding_count": 0,
        "manuscript_dispositions": ["test protocol-only disposition"],
        "attestation": {
            "signed_attestation": "test detached signature",
            "signature_fingerprint": fingerprints[DOCUMENT_TYPES[2]],
        },
    }
    document_names = {
        DOCUMENT_TYPES[0]: "evaluator.json",
        DOCUMENT_TYPES[1]: "reproduction.json",
        DOCUMENT_TYPES[2]: "editorial.json",
    }
    values = {
        DOCUMENT_TYPES[0]: evaluator,
        DOCUMENT_TYPES[1]: reproduction,
        DOCUMENT_TYPES[2]: editorial,
    }
    checksums = {
        document_type: _write_json(documents_root / document_names[document_type], value)
        for document_type, value in values.items()
    }
    bundle = {
        "schema_version": 1,
        "submission_state": "SUBMITTED_FOR_PREFLIGHT",
        "intake_id": "test-signature-intake",
        "submitted_at": "2026-08-13T00:00:00+00:00",
        "evidence_class": "DEVELOPMENT_OBSERVATION",
        "allowed_claim_level": "EXPLORATORY",
        "identity_and_scope_audit_pending": True,
        "scientific_submission_ready": False,
        "documents": [
            {
                "document_type": document_type,
                "relative_path": document_names[document_type],
                "sha256": checksums[document_type],
                "role_not_author_declared": True,
            }
            for document_type in DOCUMENT_TYPES
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    _write_json(bundle_path, bundle)

    signatures_root = tmp_path / "signatures"
    signatures_root.mkdir()
    signature_names: dict[str, str] = {}
    for document_type in DOCUMENT_TYPES:
        signature_name = f"{document_type}.asc"
        signature_names[document_type] = signature_name
        _run(
            [
                "gpg",
                "--batch",
                "--pinentry-mode",
                "loopback",
                "--passphrase",
                "",
                "--homedir",
                str(signer_homes[document_type]),
                "--armor",
                "--local-user",
                fingerprints[document_type],
                "--output",
                str(signatures_root / signature_name),
                "--detach-sign",
                str(documents_root / document_names[document_type]),
            ]
        )
    signature_manifest_path = tmp_path / "signature-manifest.json"
    _write_json(
        signature_manifest_path,
        {
            "schema_version": 1,
            "verification_id": "test-signature-verification",
            "verified_at": "2026-08-13T00:00:00+00:00",
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "bundle_sha256": _sha256(bundle_path.read_bytes()),
            "signatures": [
                {
                    "document_type": document_type,
                    "signature_relative_path": signature_names[document_type],
                }
                for document_type in DOCUMENT_TYPES
            ],
        },
    )
    registry_path = tmp_path / "trusted-signers.json"
    _write_json(
        registry_path,
        {
            "schema_version": 1,
            "registry_id": "test-approved-registry",
            "approved_at": "2026-08-13T00:00:00+00:00",
            "approval_scope": "test scope-owner approval record",
            "signers": [
                {
                    "document_type": document_type,
                    "signer_key_fingerprint": fingerprints[document_type],
                    "public_key_relative_path": f"{name}.asc",
                    "public_key_sha256": _sha256((tmp_path / "keys" / f"{name}.asc").read_bytes()),
                }
                for name, document_type in zip(
                    ("evaluator", "reproducer", "editor"), DOCUMENT_TYPES, strict=True
                )
            ],
        },
    )
    return {
        "bundle_path": bundle_path,
        "documents_root": documents_root,
        "signature_manifest_path": signature_manifest_path,
        "signatures_root": signatures_root,
        "registry_path": registry_path,
        "keys_root": tmp_path / "keys",
        "receipt_path": tmp_path / "signature-receipt.json",
        "fingerprints": fingerprints,
    }


def _workflow(paths: dict[str, Path | dict[str, str]]) -> ExternalVerificationSignatureWorkflow:
    return ExternalVerificationSignatureWorkflow(
        bundle_path=paths["bundle_path"],  # type: ignore[arg-type]
        documents_root=paths["documents_root"],  # type: ignore[arg-type]
        signature_manifest_path=paths["signature_manifest_path"],  # type: ignore[arg-type]
        signatures_root=paths["signatures_root"],  # type: ignore[arg-type]
        trusted_signer_registry_path=paths["registry_path"],  # type: ignore[arg-type]
        trusted_keys_root=paths["keys_root"],  # type: ignore[arg-type]
        receipt_path=paths["receipt_path"],  # type: ignore[arg-type]
    )


def test_signature_verification_accepts_three_distinct_registered_keys(tmp_path: Path) -> None:
    paths = _write_package(tmp_path)

    summary = _workflow(paths).run(strict=True)

    assert summary.status == (
        "CRYPTOGRAPHIC_SIGNATURES_VERIFIED_REQUIRES_IDENTITY_SCOPE_AND_SCIENTIFIC_AUDIT"
    )
    assert summary.verified_document_count == 3
    receipt = json.loads(Path(paths["receipt_path"]).read_text(encoding="utf-8"))
    assert receipt["identity_authenticated"] is False
    assert receipt["scientific_submission_ready"] is False


def test_signature_verification_rejects_reused_key_across_roles(tmp_path: Path) -> None:
    paths = _write_package(tmp_path)
    registry_path = Path(paths["registry_path"])
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["signers"][1] = dict(registry["signers"][0])
    registry["signers"][1]["document_type"] = DOCUMENT_TYPES[1]
    _write_json(registry_path, registry)

    with pytest.raises(ExternalVerificationSignatureError, match="distinct trusted signing key"):
        _workflow(paths).run(strict=True)


def test_signature_verification_rejects_signature_bound_to_another_document(tmp_path: Path) -> None:
    paths = _write_package(tmp_path)
    manifest_path = Path(paths["signature_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["signatures"][1]["signature_relative_path"] = manifest["signatures"][0][
        "signature_relative_path"
    ]
    _write_json(manifest_path, manifest)

    with pytest.raises(
        ExternalVerificationSignatureError, match="detached signature does not verify"
    ):
        _workflow(paths).run(strict=True)


def test_signature_verification_refuses_to_overwrite_a_receipt(tmp_path: Path) -> None:
    paths = _write_package(tmp_path)
    Path(paths["receipt_path"]).write_text("existing", encoding="utf-8")

    with pytest.raises(ExternalVerificationSignatureError, match="receipt path already exists"):
        _workflow(paths).run(strict=True)


def test_signature_verification_cli_preserves_non_accepting_boundary(tmp_path: Path) -> None:
    paths = _write_package(tmp_path)
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "biointerfaceos",
            "data",
            "verify-external-verification-signatures",
            "--bundle",
            str(paths["bundle_path"]),
            "--documents-root",
            str(paths["documents_root"]),
            "--signature-manifest",
            str(paths["signature_manifest_path"]),
            "--signatures-root",
            str(paths["signatures_root"]),
            "--trusted-signer-registry",
            str(paths["registry_path"]),
            "--trusted-keys-root",
            str(paths["keys_root"]),
            "--receipt-out",
            str(paths["receipt_path"]),
            "--strict",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "EXTERNAL_VERIFICATION_SIGNATURE_VALID" in result.stdout
    assert "identity_authenticated=false" in result.stdout
    assert "scientific_submission_ready=false" in result.stdout
