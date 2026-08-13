"""Tests for the external verification receipt preflight without external claims."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from biointerfaceos.external_verification_intake import (
    ExternalVerificationIntakeError,
    ExternalVerificationIntakeWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> str:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return _sha256(path.read_bytes())


def _write_structural_bundle(tmp_path: Path) -> tuple[Path, Path]:
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
        "evaluation_id": "synthetic-structural-evaluator",
        "protocol_id": "bioif-r2-independent-evaluation-protocol-v1.0.0",
        "evaluator": {
            "identity": "external evaluator declaration",
            "institution": "external institution declaration",
            "conflict_disclosure": "declared for later audit",
        },
        "frozen_bundle": frozen_bundle,
        "attestation": {
            "signed_attestation": "synthetic structural attestation",
            "signature_fingerprint": "synthetic structural fingerprint",
        },
        "aggregate_metrics": {"structural_metric": "aggregate-only placeholder"},
        "threshold_statuses": {"structural_threshold": "declared"},
        "environment_digest": "1" * 64,
        "raw_values_included": False,
        "author_team_accessed_protected_observations": False,
        "post_freeze_tuning": False,
    }
    reproduction = {
        "schema_version": 1,
        "report_id": "synthetic-structural-reproduction",
        "protocol_id": "bioif-r2-external-reproduction-editorial-protocol-v1.0.0",
        "reproduction_team": {
            "identity": "external reproducer declaration",
            "institution": "external reproduction institution",
            "conflict_disclosure": "declared for later audit",
            "author_team_membership": False,
        },
        "checkout_commit": "2" * 40,
        "environment_digest": "3" * 64,
        "source_data_attestation": {
            "method": "ATTESTED",
            "statement": "synthetic structural source attestation",
        },
        "commands_and_scope": ["synthetic structural command and declared scope"],
        "deviation_ledger": [
            {
                "deviation_id": "NONE_DECLARED",
                "severity": "NONE",
                "detail": "synthetic structural record",
            }
        ],
        "result_summary": {
            "scope": "synthetic structural scope",
            "outcome": "not a scientific result",
            "aggregate_only": True,
        },
        "attestation": {
            "signed_attestation": "synthetic structural attestation",
            "signature_fingerprint": "synthetic structural fingerprint",
        },
        "raw_protected_values_included": False,
    }
    editorial = {
        "schema_version": 1,
        "report_id": "synthetic-structural-editorial",
        "protocol_id": "bioif-r2-external-reproduction-editorial-protocol-v1.0.0",
        "reviewer": {
            "identity": "external editor declaration",
            "institution": "external editorial institution",
            "conflict_disclosure": "declared for later audit",
            "author_team_membership": False,
        },
        "r2_finding_matrix": [
            {
                "finding_id": f"R2-{number:02d}",
                "disposition": "EXPLICIT_DOWNGRADE",
                "evidence_or_downgrade_reference": "synthetic structural downgrade",
            }
            for number in range(1, 10)
        ],
        "critical_finding_count": 0,
        "manuscript_dispositions": ["protocol-only pending scope audit"],
        "attestation": {
            "signed_attestation": "synthetic structural attestation",
            "signature_fingerprint": "synthetic structural fingerprint",
        },
    }
    document_values = {
        "evaluator.json": evaluator,
        "reproduction.json": reproduction,
        "editorial.json": editorial,
    }
    checksums = {
        name: _write_json(documents_root / name, value) for name, value in document_values.items()
    }
    bundle = {
        "schema_version": 1,
        "submission_state": "SUBMITTED_FOR_PREFLIGHT",
        "intake_id": "synthetic-structural-verification",
        "submitted_at": "2026-08-13T00:00:00+00:00",
        "evidence_class": "DEVELOPMENT_OBSERVATION",
        "allowed_claim_level": "EXPLORATORY",
        "identity_and_scope_audit_pending": True,
        "scientific_submission_ready": False,
        "documents": [
            {
                "document_type": "independent_evaluator_receipt",
                "relative_path": "evaluator.json",
                "sha256": checksums["evaluator.json"],
                "role_not_author_declared": True,
            },
            {
                "document_type": "external_reproduction_receipt",
                "relative_path": "reproduction.json",
                "sha256": checksums["reproduction.json"],
                "role_not_author_declared": True,
            },
            {
                "document_type": "editorial_rereview_report",
                "relative_path": "editorial.json",
                "sha256": checksums["editorial.json"],
                "role_not_author_declared": True,
            },
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    _write_json(bundle_path, bundle)
    return bundle_path, documents_root


def _refresh_bundle_checksum(bundle_path: Path, documents_root: Path, document_name: str) -> None:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    for document in bundle["documents"]:
        if document["relative_path"] == document_name:
            document["sha256"] = _sha256((documents_root / document_name).read_bytes())
    _write_json(bundle_path, bundle)


def test_external_verification_preflight_requires_all_three_hashed_records(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)

    summary = ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run(strict=True)

    assert summary.status == "STRUCTURALLY_COMPLETE_REQUIRES_IDENTITY_AND_SCOPE_AUDIT"
    assert summary.document_count == 3
    assert summary.finding_count == 9
    assert summary.declared_open_critical_finding_count == 0


def test_external_verification_preflight_requires_strict_mode(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)

    with pytest.raises(ExternalVerificationIntakeError, match="requires --strict"):
        ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run()


def test_external_verification_preflight_rejects_checksum_mutation(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)
    (documents_root / "editorial.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ExternalVerificationIntakeError, match="checksum does not match"):
        ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run(strict=True)


def test_external_verification_preflight_requires_non_author_declaration(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["documents"][0]["role_not_author_declared"] = False
    _write_json(bundle_path, bundle)

    with pytest.raises(ExternalVerificationIntakeError, match="does not declare a non-author role"):
        ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run(strict=True)


def test_external_verification_preflight_rejects_evaluator_raw_values(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)
    evaluator_path = documents_root / "evaluator.json"
    evaluator = json.loads(evaluator_path.read_text(encoding="utf-8"))
    evaluator["raw_values_included"] = True
    _write_json(evaluator_path, evaluator)
    _refresh_bundle_checksum(bundle_path, documents_root, "evaluator.json")

    with pytest.raises(ExternalVerificationIntakeError, match="protected-data safeguards"):
        ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run(strict=True)


def test_external_verification_preflight_rejects_author_team_reproducer(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)
    reproduction_path = documents_root / "reproduction.json"
    reproduction = json.loads(reproduction_path.read_text(encoding="utf-8"))
    reproduction["reproduction_team"]["author_team_membership"] = True
    _write_json(reproduction_path, reproduction)
    _refresh_bundle_checksum(bundle_path, documents_root, "reproduction.json")

    with pytest.raises(ExternalVerificationIntakeError, match="author-team membership"):
        ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run(strict=True)


def test_external_verification_preflight_rejects_missing_r2_finding(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)
    editorial_path = documents_root / "editorial.json"
    editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
    editorial["r2_finding_matrix"].pop()
    _write_json(editorial_path, editorial)
    _refresh_bundle_checksum(bundle_path, documents_root, "editorial.json")

    with pytest.raises(ExternalVerificationIntakeError, match="wrong size"):
        ExternalVerificationIntakeWorkflow(bundle_path, documents_root).run(strict=True)


def test_external_verification_preflight_rejects_unfilled_template(tmp_path: Path) -> None:
    documents_root = tmp_path / "documents"
    documents_root.mkdir()
    template = ROOT / "docs/data/R2_EXTERNAL_VERIFICATION_BUNDLE_TEMPLATE.json"

    with pytest.raises(ExternalVerificationIntakeError, match="is not submitted"):
        ExternalVerificationIntakeWorkflow(template, documents_root).run(strict=True)


def test_external_verification_preflight_cli_preserves_non_promoting_status(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_structural_bundle(tmp_path)
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "biointerfaceos",
            "data",
            "preflight-external-verification",
            "--bundle",
            str(bundle_path),
            "--documents-root",
            str(documents_root),
            "--strict",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "status=STRUCTURALLY_COMPLETE_REQUIRES_IDENTITY_AND_SCOPE_AUDIT" in result.stdout
    assert "scientific_submission_ready=false" in result.stdout
