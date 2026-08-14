"""Create an append-only migration ledger and fail-closed evidence audit."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import (
    EvidenceClass,
    EvidenceSemanticsError,
    forbidden_terms,
    metadata_for,
    require_metadata,
)


class EvidenceSemanticsAuditError(RuntimeError):
    """Raised when the R2 evidence-semantics audit cannot run safely."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ArtifactSpec:
    """A historical or current artifact that needs explicit evidence classification."""

    artifact_type: str
    relative_path: str
    evidence_class: EvidenceClass
    scan_text: bool
    historical: bool


class EvidenceSemanticsAuditWorkflow:
    """Record legacy evidence boundaries without mutating their source artifacts."""

    AUDIT_ID = "bioif-evidence-semantics-audit-v1.2.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    QUARANTINE_RELATIVE = "docs/data/R2_LEGACY_FIXTURE_QUARANTINE.json"
    ARTIFACTS = (
        ArtifactSpec(
            "fixture_lockbox_contract",
            "tests/fixtures/lockbox/evaluate_fixture.json",
            EvidenceClass.FIXTURE_TEST,
            True,
            False,
        ),
        ArtifactSpec(
            "paper_a_manuscript",
            "release/manuscripts/paper_a/paper_a.md",
            EvidenceClass.FIXTURE_TEST,
            True,
            True,
        ),
        ArtifactSpec(
            "paper_b_manuscript",
            "release/manuscripts/paper_b/paper_b.md",
            EvidenceClass.FIXTURE_TEST,
            True,
            True,
        ),
        ArtifactSpec(
            "paper_c_prelock_manuscript",
            "release/manuscripts/paper_c_prelock/paper_c_prelock.md",
            EvidenceClass.FIXTURE_TEST,
            True,
            True,
        ),
        ArtifactSpec(
            "lockbox_evaluation_receipt",
            "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/first_run_receipt.json",
            EvidenceClass.FIXTURE_TEST,
            False,
            True,
        ),
        ArtifactSpec(
            "lockbox_audit_receipt",
            "reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/audit_receipt.json",
            EvidenceClass.FIXTURE_TEST,
            False,
            True,
        ),
        ArtifactSpec(
            "publication_figure_manifest",
            "reports/publication/final-v1.0.0/figure_manifest.json",
            EvidenceClass.FIXTURE_TEST,
            False,
            True,
        ),
        ArtifactSpec(
            "clean_room_replay_report",
            "release/public/bioif-public-v1.0.0/reproducibility/reproduction_report.json",
            EvidenceClass.SOFTWARE_REPLAY,
            True,
            True,
        ),
    )

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or (self.root / "reports/review_round_2/evidence_semantics/v1.2.0")

    def _path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise EvidenceSemanticsAuditError(f"evidence artifact is missing: {relative_path}")
        if "data/locked_test" in path.as_posix():
            raise EvidenceSemanticsAuditError(f"protected payload path is forbidden: {relative_path}")
        return path

    def _quarantine(self) -> tuple[dict[str, dict[str, str]], str]:
        """Validate immutable quarantine metadata for known legacy wording."""
        path = self._path(self.QUARANTINE_RELATIVE)
        payload = self._declared_metadata(path)
        if payload is None:
            raise EvidenceSemanticsAuditError("legacy fixture quarantine is invalid")
        required_fields = {
            "schema_version",
            "quarantine_id",
            "declared_at",
            "status",
            "quarantined_artifacts",
            "prohibited_uses",
        }
        if (
            set(payload) != required_fields
            or payload.get("schema_version") != 1
            or payload.get("quarantine_id") != "bioif-r2-legacy-fixture-quarantine-v1.0.0"
            or payload.get("declared_at") != self.AUDITED_AT
            or payload.get("status") != "ACTIVE_EXCLUDED_FROM_R2_CLAIM_AND_PUBLIC_RELEASE_SCOPE"
        ):
            raise EvidenceSemanticsAuditError("legacy fixture quarantine identity is invalid")
        prohibited_uses = payload.get("prohibited_uses")
        if not isinstance(prohibited_uses, list) or set(prohibited_uses) != {
            "current_r2_manuscript_evidence",
            "public_release_artifact",
            "scientific_replication_evidence",
            "empirical_validation_evidence",
        }:
            raise EvidenceSemanticsAuditError("legacy fixture quarantine prohibitions are invalid")
        artifacts = payload.get("quarantined_artifacts")
        if not isinstance(artifacts, list) or len(artifacts) != 1:
            raise EvidenceSemanticsAuditError("legacy fixture quarantine artifact inventory is invalid")
        artifact = artifacts[0]
        if not isinstance(artifact, dict) or set(artifact) != {
            "artifact_type",
            "path",
            "source_sha256",
            "evidence_class",
            "scope",
            "reason",
        }:
            raise EvidenceSemanticsAuditError("legacy fixture quarantine artifact schema is invalid")
        expected_path = "release/manuscripts/paper_a/paper_a.md"
        source_path = self._path(expected_path)
        if (
            artifact.get("artifact_type") != "paper_a_manuscript"
            or artifact.get("path") != expected_path
            or artifact.get("source_sha256") != _sha256(source_path)
            or artifact.get("evidence_class") != EvidenceClass.FIXTURE_TEST.value
            or artifact.get("scope") != "EXCLUDED_FROM_CURRENT_R2_MANUSCRIPT_AND_PUBLIC_RELEASE"
            or not isinstance(artifact.get("reason"), str)
            or not artifact["reason"].strip()
        ):
            raise EvidenceSemanticsAuditError("legacy fixture quarantine artifact is stale")
        return {expected_path: artifact}, _sha256(path)

    @staticmethod
    def _declared_metadata(path: Path) -> dict[str, Any] | None:
        if path.suffix != ".json":
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EvidenceSemanticsAuditError(f"cannot parse JSON artifact: {path}") from exc
        if not isinstance(value, dict):
            raise EvidenceSemanticsAuditError(f"JSON artifact must be an object: {path}")
        return value

    def _record(self, spec: ArtifactSpec) -> tuple[dict[str, Any], list[dict[str, str]]]:
        path = self._path(spec.relative_path)
        payload = self._declared_metadata(path)
        expected = metadata_for(spec.evidence_class)
        metadata_status = "MIGRATED_LEGACY"
        violations: list[dict[str, str]] = []
        if payload is not None and "evidence_class" in payload:
            try:
                require_metadata(payload, spec.relative_path)
            except EvidenceSemanticsError as exc:
                violations.append({"path": spec.relative_path, "finding": str(exc)})
            else:
                metadata_status = "DECLARED"
                if payload["evidence_class"] != expected["evidence_class"]:
                    violations.append(
                        {
                            "path": spec.relative_path,
                            "finding": "declared evidence class disagrees with migration policy",
                        }
                    )
        elif not spec.historical:
            violations.append(
                {
                    "path": spec.relative_path,
                    "finding": "new fixture artifact lacks required evidence metadata",
                }
            )
        if spec.scan_text:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden_terms(text, spec.evidence_class):
                violations.append(
                    {
                        "path": spec.relative_path,
                        "finding": f"forbidden {spec.evidence_class.value} wording: {pattern}",
                    }
                )
        return (
            {
                "artifact_type": spec.artifact_type,
                "path": spec.relative_path,
                "sha256": _sha256(path),
                "historical": spec.historical,
                "metadata_status": metadata_status,
                **expected,
                "prohibited_inferences": [
                    "empirical validation",
                    "scientific replication",
                    "universal law",
                ],
            },
            violations,
        )

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise EvidenceSemanticsAuditError("T116 requires --strict")
        if self.output_root.exists():
            raise EvidenceSemanticsAuditError("evidence-semantics audit already executed")
        quarantine, quarantine_sha256 = self._quarantine()
        records: list[dict[str, Any]] = []
        violations: list[dict[str, str]] = []
        for spec in self.ARTIFACTS:
            record, findings = self._record(spec)
            records.append(record)
            violations.extend(findings)
        quarantined = [finding for finding in violations if finding["path"] in quarantine]
        blocking = [finding for finding in violations if finding["path"] not in quarantine]
        status = (
            "PASS_EVIDENCE_SEMANTICS_WITH_QUARANTINED_LEGACY_FIXTURES" if not blocking else "BLOCKED_EVIDENCE_SEMANTICS"
        )
        ledger = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "records": records,
            "quarantine_manifest_sha256": quarantine_sha256,
            "quarantined_artifacts": list(quarantine.values()),
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": status,
            "blocking_findings": len(blocking),
            "findings": blocking,
            "quarantined_historical_findings": quarantined,
            "quarantine_manifest_sha256": quarantine_sha256,
            "submission_ready": False,
            "historical_sources_mutated": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        ledger_path = self.output_root / "evidence_migration_ledger.json"
        report_path = self.output_root / "evidence_semantics_report.json"
        ledger_path.write_bytes(_canonical(ledger))
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": status,
            "blocking_findings": len(blocking),
            "quarantined_historical_finding_count": len(quarantined),
            "quarantine_manifest_sha256": quarantine_sha256,
            "ledger_sha256": _sha256(ledger_path),
            "report_sha256": _sha256(report_path),
            "historical_sources_mutated": False,
        }
        receipt_path = self.output_root / "audit_receipt.json"
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return report

    def verify(self) -> dict[str, Any]:
        report_path = self.output_root / "evidence_semantics_report.json"
        ledger_path = self.output_root / "evidence_migration_ledger.json"
        receipt_path = self.output_root / "audit_receipt.json"
        if not report_path.is_file() or not ledger_path.is_file() or not receipt_path.is_file():
            raise EvidenceSemanticsAuditError("evidence-semantics audit outputs are missing")
        receipt = self._declared_metadata(receipt_path)
        report = self._declared_metadata(report_path)
        if receipt is None or report is None:
            raise EvidenceSemanticsAuditError("evidence-semantics audit payload is invalid")
        if (
            receipt.get("ledger_sha256") != _sha256(ledger_path)
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("status") != report.get("status")
            or receipt.get("blocking_findings") != report.get("blocking_findings")
            or receipt.get("quarantined_historical_finding_count")
            != len(report.get("quarantined_historical_findings", []))
            or receipt.get("quarantine_manifest_sha256") != report.get("quarantine_manifest_sha256")
            or receipt.get("historical_sources_mutated") is not False
        ):
            raise EvidenceSemanticsAuditError("evidence-semantics audit receipt is invalid")
        return report
