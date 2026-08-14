from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from biointerfaceos.r4_external_receipt_preflight import (
    R4ExternalReceiptPreflightError,
    R4ExternalReceiptPreflightWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_ID = "bioif-r4-external-evaluator-and-reproduction-v1.0.0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> str:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return _sha256(path)


def _fixed_release() -> dict[str, str]:
    return dict(R4ExternalReceiptPreflightWorkflow.FIXED_RELEASE)


def _person(identity: str, institution: str = "independent institution") -> dict[str, object]:
    return {
        "identity": identity,
        "institution": institution,
        "contact": "independent@example.org",
        "conflict_disclosure": "no author-team membership declared for contract test",
        "author_team_membership": False,
    }


def _attestation() -> dict[str, str]:
    return {
        "signed_attestation": "contract-test attestation",
        "signature_fingerprint": "contract-test-fingerprint",
        "signed_at": "2026-08-13T00:00:00+00:00",
    }


def _frozen_bundle() -> dict[str, str]:
    return {
        "checkout_commit": R4ExternalReceiptPreflightWorkflow.FIXED_RELEASE["commit"],
        "protocol_sha256": "b" * 64,
        "environment_digest": "c" * 64,
        "dependency_lockfile_sha256": "d" * 64,
        "input_manifest_sha256_or_protected_data_attestation": ("contract-test protected input attestation"),
    }


def _aggregate_results() -> dict[str, dict[str, str]]:
    return {
        "primary_endpoint": {"metric": "spearman", "value": "aggregate-only"},
        "cluster_aware_uncertainty": {"method": "cluster-bootstrap", "value": "reported"},
        "effective_counts": {"observations": "reported", "clusters": "reported"},
        "paired_ablation": {"comparison": "full-v-composition", "value": "reported"},
        "negative_control": {"method": "within-batch-permutation", "value": "reported"},
        "model_results": {"model": "sequence-only", "value": "reported"},
    }


def _failure_records() -> list[dict[str, str]]:
    return [
        {
            "run_id": "contract-run-1",
            "status": "PASS",
            "detail": "aggregate-only contract record",
        }
    ]


def _deviations() -> list[dict[str, str]]:
    return [{"deviation_id": "NONE", "severity": "NONE", "detail": "no deviation declared"}]


def _evaluator_receipt() -> dict[str, object]:
    return {
        "schema_version": 1,
        "receipt_id": "contract-evaluator",
        "protocol_id": PROTOCOL_ID,
        "evaluator": _person("independent evaluator"),
        "independence_safeguards": {
            "protected_input_held_by_evaluator": True,
            "author_row_level_access": False,
            "aggregate_receipt_only": True,
        },
        "frozen_bundle": _frozen_bundle(),
        "commands_and_scope": ["contract test scope"],
        "aggregate_results": _aggregate_results(),
        "failure_and_negative_runs": _failure_records(),
        "deviation_ledger": _deviations(),
        "attestation": _attestation(),
        "raw_values_included": False,
        "author_accessed_protected_observations": False,
        "post_freeze_tuning": False,
        "immutable_archive_locator": "https://example.org/contract-evaluator-receipt",
    }


def _reproduction_receipt() -> dict[str, object]:
    return {
        "schema_version": 1,
        "receipt_id": "contract-reproduction",
        "protocol_id": PROTOCOL_ID,
        "reproduction_team": _person("independent reproducer"),
        "source_data_attestation": {
            "method": "REACQUIRED",
            "statement": "contract test reacquired source declaration",
        },
        "frozen_bundle": _frozen_bundle(),
        "commands_and_scope": ["contract reproduction scope"],
        "aggregate_results": _aggregate_results(),
        "failure_and_negative_runs": _failure_records(),
        "deviation_ledger": _deviations(),
        "attestation": _attestation(),
        "raw_values_included": False,
        "author_accessed_protected_observations": False,
        "immutable_archive_locator": "https://example.org/contract-reproduction-receipt",
    }


def _adoption_receipt(
    receipt_id: str,
    identity: str,
    institution: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "receipt_id": receipt_id,
        "protocol_id": PROTOCOL_ID,
        "user": _person(identity, institution),
        "task_description": "installed and ran the public software contract",
        "input_provenance": "public tagged checkout and source instructions",
        "checkout_commit": R4ExternalReceiptPreflightWorkflow.FIXED_RELEASE["commit"],
        "environment_digest": "f" * 64,
        "dependency_lockfile_sha256": "0" * 64,
        "commands": ["contract adoption command"],
        "output_hashes": {"summary.json": "1" * 64},
        "successes_and_failures": _failure_records(),
        "limitations_feedback": "contract-test feedback",
        "public_summary_consent": True,
        "attestation": _attestation(),
        "immutable_archive_locator": "https://example.org/contract-adoption-receipt",
    }


def _write_submitted_bundle(tmp_path: Path) -> tuple[Path, Path]:
    documents_root = tmp_path / "documents"
    documents_root.mkdir()
    values = {
        "independent_evaluator_receipt": _evaluator_receipt(),
        "external_reproduction_receipt": _reproduction_receipt(),
        "external_user_adoption_receipt_01": _adoption_receipt(
            "contract-adoption-01", "independent user 01", "independent institution 01"
        ),
        "external_user_adoption_receipt_02": _adoption_receipt(
            "contract-adoption-02", "independent user 02", "independent institution 02"
        ),
    }
    checksums: dict[str, str] = {}
    for document_type, value in values.items():
        checksums[document_type] = _write_json(documents_root / f"{document_type}.json", value)

    bundle = {
        "schema_version": 1,
        "submission_state": "SUBMITTED_FOR_PREFLIGHT",
        "bundle_id": "contract-bundle",
        "submitted_at": "2026-08-13T00:00:00+00:00",
        "evidence_class": "DEVELOPMENT_OBSERVATION",
        "allowed_claim_level": "EXPLORATORY",
        "identity_and_scope_audit_pending": True,
        "scientific_submission_ready": False,
        "fixed_release": _fixed_release(),
        "documents": [
            {
                "document_type": document_type,
                "relative_path": f"{document_type}.json",
                "sha256": checksums[document_type],
                "role_not_author_declared": True,
            }
            for document_type in values
        ],
    }
    bundle_path = tmp_path / "bundle.json"
    _write_json(bundle_path, bundle)
    return bundle_path, documents_root


def test_r4_preflight_validates_three_receipts_without_promoting_evidence(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    receipt_path = tmp_path / "preflight.json"

    summary = R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, receipt_path).run(strict=True)

    assert summary.status == "STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW"
    assert summary.document_count == 4
    assert summary.non_author_declared_count == 4
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["fixed_release"] == _fixed_release()
    assert receipt["identity_authenticated"] is False
    assert receipt["independence_authenticated"] is False
    assert receipt["protected_lockbox_accepted"] is False
    assert receipt["external_scientific_reproduction_accepted"] is False
    assert receipt["external_user_adoption_accepted"] is False
    assert receipt["scientific_submission_ready"] is False

    verified = R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, receipt_path).verify()
    assert verified == summary


def test_r4_preflight_rejects_document_tampering(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    path = documents_root / "external_reproduction_receipt.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(R4ExternalReceiptPreflightError, match="checksum differs"):
        R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, tmp_path / "out.json").run(strict=True)


def test_r4_preflight_rejects_author_membership(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    path = documents_root / "external_user_adoption_receipt_01.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["user"]["author_team_membership"] = True
    _write_json(path, value)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    for document in bundle["documents"]:
        if document["document_type"] == "external_user_adoption_receipt_01":
            document["sha256"] = _sha256(path)
    _write_json(bundle_path, bundle)

    with pytest.raises(R4ExternalReceiptPreflightError, match="author-team membership"):
        R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, tmp_path / "out.json").run(strict=True)


def test_r4_preflight_rejects_release_drift(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["fixed_release"]["tag"] = "v0.1.3-r10.25"
    _write_json(bundle_path, bundle)

    with pytest.raises(R4ExternalReceiptPreflightError, match="immutable r10.28 release"):
        R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, tmp_path / "out.json").run(strict=True)


def test_r4_preflight_rejects_release_commit_drift(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["fixed_release"]["commit"] = "a" * 40
    _write_json(bundle_path, bundle)

    with pytest.raises(R4ExternalReceiptPreflightError, match="immutable r10.28 release"):
        R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, tmp_path / "out.json").run(strict=True)


def test_r4_preflight_rejects_release_manifest_hash_drift(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle["fixed_release"]["manifest_sha256"] = "c" * 64
    _write_json(bundle_path, bundle)

    with pytest.raises(R4ExternalReceiptPreflightError, match="immutable r10.28 release"):
        R4ExternalReceiptPreflightWorkflow(bundle_path, documents_root, tmp_path / "out.json").run(strict=True)


def test_r4_fixed_release_anchors_match_all_public_handoff_records() -> None:
    expected = R4ExternalReceiptPreflightWorkflow.FIXED_RELEASE
    handoff_records = [
        json.loads((ROOT / "docs/data/R4_T218_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json").read_text(encoding="utf-8"))[
            "fixed_release"
        ],
        json.loads(
            (ROOT / "docs/data/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.json").read_text(encoding="utf-8")
        )["fixed_release"],
        json.loads(
            (ROOT / "docs/data/R4_T240_EXTERNAL_RECEIPT_FIXED_RELEASE_BINDING_20260814.json").read_text(
                encoding="utf-8"
            )
        )["fixed_release"],
        json.loads(
            (ROOT / "docs/data/R4_T241_CANONICAL_RELEASE_MANIFEST_HASH_AUDIT_20260814.json").read_text(encoding="utf-8")
        )["fixed_release"],
    ]
    for record in handoff_records:
        assert record["tag"] == expected["tag"]
        assert record.get("commit", record.get("tag_target")) == expected["commit"]
        assert record["source_commit"] == expected["source_commit"]
        assert record["manifest_path"] == expected["manifest_path"]
        assert record["manifest_sha256"] == expected["manifest_sha256"]

    t235 = json.loads(
        (ROOT / "docs/data/R4_T235_PAPER_DATA_EXTERNAL_EVIDENCE_GOAL_20260814.json").read_text(encoding="utf-8")
    )["fixed_release"]
    assert t235["tag"] == expected["tag"]
    assert t235["manifest"] == expected["manifest_path"]
    assert t235["manifest_sha256"] == expected["manifest_sha256"]

    doi_release = json.loads((ROOT / "docs/release/R10_28_DOI_DEPOSIT_METADATA.json").read_text(encoding="utf-8"))[
        "release"
    ]
    assert doi_release["tag"] == expected["tag"]
    assert doi_release["release_commit"] == expected["commit"]
    assert doi_release["manifest_path"] == expected["manifest_path"]
    assert doi_release["manifest_sha256"] == expected["manifest_sha256"]


def test_r4_preflight_cli_preserves_non_promoting_status(tmp_path: Path) -> None:
    bundle_path, documents_root = _write_submitted_bundle(tmp_path)
    receipt_path = tmp_path / "preflight.json"
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "biointerfaceos",
            "data",
            "preflight-r4-external-receipts",
            "--bundle",
            str(bundle_path),
            "--documents-root",
            str(documents_root),
            "--receipt-out",
            str(receipt_path),
            "--strict",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "status=STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW" in result.stdout
    assert "independence_authenticated=false" in result.stdout
    assert "scientific_submission_ready=false" in result.stdout
