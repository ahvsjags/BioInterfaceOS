"""Audit the executable R2 external-evidence handoff path.

This workflow checks that the source-intake, independent-evaluation, external
reproduction and editorial-review stages agree with the current R2 acceptance
protocol. It audits process readiness only: it does not receive data,
authenticate a person, admit a target, or accept a scientific claim.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from biointerfaceos.evidence_semantics import EvidenceClass, metadata_for


class R2ExternalGatePathError(RuntimeError):
    """Raised when the external R2 handoff path has drifted or weakened."""


@dataclass(frozen=True)
class R2ExternalGatePathSummary:
    """Summary of the non-promoting external-gate path audit."""

    status: str
    stage_count: int
    reference_count: int
    command_count: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".md", ".yaml", ".yml", ".txt", ".tsv", ".py"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise R2ExternalGatePathError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise R2ExternalGatePathError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise R2ExternalGatePathError(f"{label} must be an integer")
    return int(value)


class R2ExternalGatePathWorkflow:
    """Verify the ordered, fail-closed path for future external evidence."""

    AUDIT_ID = "bioif-r2-external-gate-path-audit-v1.1.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    OUTPUT_RELATIVE = "reports/review_round_2/external_gate_path/v1.1.0"
    REFERENCES = {
        "handoff_package": (
            "docs/data/R2_EXTERNAL_EVIDENCE_HANDOFF.json",
            "R2 external-evidence handoff package",
        ),
        "handoff_receipt": (
            "reports/review_round_2/external_evidence_handoff/v1.10.0/external_evidence_handoff_receipt.json",
            "R2 external-evidence handoff receipt",
        ),
        "source_template": (
            "docs/data/R2_EXTERNAL_SOURCE_INTAKE_TEMPLATE.json",
            "external source-intake template",
        ),
        "verification_template": (
            "docs/data/R2_EXTERNAL_VERIFICATION_BUNDLE_TEMPLATE.json",
            "external verification template",
        ),
        "external_protocol": (
            "docs/data/R2_EXTERNAL_REPRODUCTION_AND_EDITORIAL_PROTOCOL.json",
            "external reproduction and editorial protocol",
        ),
        "acceptance_gates": (
            "docs/review_round_2/ACCEPTANCE_GATES.yaml",
            "R2 acceptance gates",
        ),
        "t124_readiness": (
            "reports/review_round_2/independent_evaluation/v1.0.0/readiness_receipt.json",
            "T124 evaluator-readiness receipt",
        ),
        "r2_acceptance": (
            "reports/review_round_2/r2_acceptance/v1.8.0/acceptance_readiness_receipt.json",
            "R2 acceptance-readiness receipt",
        ),
        "source_execplan": (
            "docs/execplans/T135_external_source_intake_preflight.md",
            "T135 external source-intake execution plan",
        ),
        "verification_execplan": (
            "docs/execplans/T136_external_verification_receipt_preflight.md",
            "T136 external verification execution plan",
        ),
        "signature_execplan": (
            "docs/execplans/T139_external_signature_verification.md",
            "T139 external signature execution plan",
        ),
        "operator_runbook": (
            "docs/review_round_2/R2_EXTERNAL_GATE_PATH.md",
            "R2 external gate-path operator runbook",
        ),
        "cli": ("src/biointerfaceos/cli.py", "BioInterfaceOS CLI"),
    }
    HANDOFF_ORDER = [
        "source_intake_and_license_gate",
        "cross_laboratory_target_admission",
        "t121_amendment_and_real_model_freeze",
        "independent_protected_data_evaluation",
        "external_scientific_reproduction",
        "editorial_rereview_and_r2_acceptance",
    ]
    COMMANDS = {
        "source_intake": "preflight-external-source-intake",
        "verification_preflight": "preflight-external-verification",
        "signature_verification": "verify-external-verification-signatures",
        "r2_acceptance": "accept-r2",
        "external_handoff": "audit-r2-external-handoff",
        "r2_remediation": "audit-r2-remediation",
    }
    REQUIRED_EXTERNAL_GATES = {
        "independent_lockbox",
        "external_scientific_reproduction",
        "final_editorial_audit",
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: str, label: str) -> Path:
        path = (self.root / relative).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R2ExternalGatePathError(f"{label} is missing or outside the repository")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R2ExternalGatePathError(f"cannot parse {label}") from exc

    @staticmethod
    def _yaml(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise R2ExternalGatePathError(f"cannot parse {label}") from exc

    def _sources(self) -> dict[str, dict[str, str]]:
        return {
            key: {"path": relative, "sha256": _sha256(self._path(relative, label))}
            for key, (relative, label) in self.REFERENCES.items()
        }

    def _audit_state(self) -> dict[str, int | str]:
        handoff = self._json(self._path(*self.REFERENCES["handoff_package"]), "handoff package")
        handoff_receipt = self._json(self._path(*self.REFERENCES["handoff_receipt"]), "handoff receipt")
        if (
            handoff.get("status") != "READY_FOR_EXTERNAL_SOURCE_INTAKE"
            or handoff.get("cohort_routing", {}).get("active_route") != "CC0_ONLY"
            or handoff.get("current_state")
            != {
                "admitted_cross_lab_target_count": 0,
                "model_use": "PROHIBITED",
                "independent_evaluator_receipt_verified": False,
                "external_reproduction_verified": False,
                "editorial_rereview_verified": False,
                "scientific_submission_ready": False,
            }
            or handoff_receipt.get("status") != handoff.get("status")
            or handoff_receipt.get("external_source_received") is not False
            or handoff_receipt.get("scientific_submission_ready") is not False
        ):
            raise R2ExternalGatePathError("external handoff state is not fail-closed")
        if handoff.get("handoff_order") != self.HANDOFF_ORDER:
            raise R2ExternalGatePathError("external handoff order is invalid")

        source_template = self._json(self._path(*self.REFERENCES["source_template"]), "source-intake template")
        if (
            source_template.get("submission_state") != "TEMPLATE_NOT_FOR_VALIDATION"
            or source_template.get("target_admission_requested") is not False
            or source_template.get("source_records") != []
        ):
            raise R2ExternalGatePathError("source-intake template is promotable")
        verification_template = self._json(
            self._path(*self.REFERENCES["verification_template"]), "verification template"
        )
        if (
            verification_template.get("submission_state") != "TEMPLATE_NOT_FOR_VALIDATION"
            or verification_template.get("identity_and_scope_audit_pending") is not True
            or verification_template.get("scientific_submission_ready") is not False
            or verification_template.get("documents") != []
        ):
            raise R2ExternalGatePathError("verification template is promotable")

        protocol = self._json(self._path(*self.REFERENCES["external_protocol"]), "external protocol")
        external_requirements = _mapping(
            protocol.get("external_reproduction_requirements"),
            "external reproduction requirements",
        )
        editorial_requirements = _mapping(protocol.get("editorial_rereview_requirements"), "editorial requirements")
        if (
            protocol.get("status") != "PROTOCOL_ONLY_PENDING_T123_T124_T126_T127"
            or any(value is not True for value in external_requirements.values())
            or any(value is not True for value in editorial_requirements.values())
        ):
            raise R2ExternalGatePathError("external protocol weakens an independence gate")

        gates = self._yaml(self._path(*self.REFERENCES["acceptance_gates"]), "acceptance gates")
        required_gates = _mapping(gates.get("required_gates"), "required gates")
        if not self.REQUIRED_EXTERNAL_GATES.issubset(required_gates):
            raise R2ExternalGatePathError("acceptance gates omit an external stage")
        for gate_id in self.REQUIRED_EXTERNAL_GATES:
            gate = _mapping(required_gates[gate_id], f"acceptance gate {gate_id}")
            if not _string(gate.get("pass_evidence"), f"acceptance gate {gate_id} pass evidence"):
                raise R2ExternalGatePathError(f"acceptance gate {gate_id} has no pass evidence")
            if not _string(gate.get("fallback"), f"acceptance gate {gate_id} fallback"):
                raise R2ExternalGatePathError(f"acceptance gate {gate_id} has no fallback")

        t124 = self._json(self._path(*self.REFERENCES["t124_readiness"]), "T124 readiness")
        acceptance = self._json(self._path(*self.REFERENCES["r2_acceptance"]), "R2 acceptance")
        if (
            t124.get("status") != "BLOCKED_T123_COMPATIBLE_TARGET_REQUIRED"
            or t124.get("external_evaluator_receipt_verified") is not False
            or t124.get("protected_observations_accessed") is not False
            or acceptance.get("status") != "BLOCKED_R2_EXTERNAL_EVIDENCE_REQUIRED"
            or acceptance.get("prerequisite_blocker_count") != 9
            or acceptance.get("external_reproduction_verified") is not False
            or acceptance.get("editorial_rereview_verified") is not False
            or acceptance.get("scientific_submission_ready") is not False
        ):
            raise R2ExternalGatePathError("current external acceptance state is inconsistent")

        cli = self._path(*self.REFERENCES["cli"]).read_text(encoding="utf-8")
        missing_commands = [name for name, command in self.COMMANDS.items() if command not in cli]
        if missing_commands:
            raise R2ExternalGatePathError(f"CLI lacks external gate commands: {', '.join(missing_commands)}")
        for key in ("source_execplan", "verification_execplan"):
            content = self._path(*self.REFERENCES[key]).read_text(encoding="utf-8")
            if "--strict" not in content or "never" not in content.lower():
                raise R2ExternalGatePathError(f"{key} lacks strict non-promoting instructions")
        runbook = self._path(*self.REFERENCES["operator_runbook"]).read_text(encoding="utf-8")
        if "preflight-external-source-intake" not in runbook or "scientific_submission_ready" not in runbook:
            raise R2ExternalGatePathError("operator runbook lacks external intake or readiness boundary")
        return {
            "stage_count": len(self.HANDOFF_ORDER),
            "reference_count": len(self.REFERENCES),
            "command_count": len(self.COMMANDS),
            "status": "READY_FOR_EXTERNAL_HANDOFF_WITH_EXTERNAL_GATES_OPEN",
        }

    def run(self, *, strict: bool = False) -> R2ExternalGatePathSummary:
        """Write one immutable process-readiness receipt."""
        if not strict:
            raise R2ExternalGatePathError("R2 external gate-path audit requires --strict")
        if self.output_root.exists():
            raise R2ExternalGatePathError("R2 external gate-path audit already executed")
        metrics = self._audit_state()
        sources = self._sources()
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": "PASS_R2_EXTERNAL_GATE_PATH_AUDIT",
            **metadata_for(EvidenceClass.DEVELOPMENT_OBSERVATION),
            "gate_status": metrics["status"],
            "ordered_stages": self.HANDOFF_ORDER,
            "command_inventory": self.COMMANDS,
            "reference_receipts": sources,
            "stage_count": metrics["stage_count"],
            "reference_count": metrics["reference_count"],
            "command_count": metrics["command_count"],
            "external_source_received": False,
            "independent_evaluator_receipt_verified": False,
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "external_gate_path_report.json"
        receipt_path = self.output_root / "external_gate_path_receipt.json"
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "gate_status": report["gate_status"],
            "external_gate_path_report_sha256": _sha256(report_path),
            "stage_count": report["stage_count"],
            "reference_count": report["reference_count"],
            "command_count": report["command_count"],
            "external_source_received": False,
            "independent_evaluator_receipt_verified": False,
            "external_reproduction_verified": False,
            "editorial_rereview_verified": False,
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return R2ExternalGatePathSummary(
            status=_string(report.get("status"), "R2 external gate-path status"),
            stage_count=_integer(report.get("stage_count"), "R2 external gate-path stage count"),
            reference_count=_integer(report.get("reference_count"), "R2 external gate-path reference count"),
            command_count=_integer(report.get("command_count"), "R2 external gate-path command count"),
            receipt_path=receipt_path,
        )

    def verify(self) -> R2ExternalGatePathSummary:
        """Verify the immutable process-readiness receipt and source hashes."""
        report_path = self.output_root / "external_gate_path_report.json"
        receipt_path = self.output_root / "external_gate_path_receipt.json"
        report = self._json(report_path, "external gate-path report")
        receipt = self._json(receipt_path, "external gate-path receipt")
        metrics = self._audit_state()
        process_flags = (
            "external_source_received",
            "independent_evaluator_receipt_verified",
            "external_reproduction_verified",
            "editorial_rereview_verified",
        )
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != "PASS_R2_EXTERNAL_GATE_PATH_AUDIT"
            or receipt.get("status") != report.get("status")
            or receipt.get("external_gate_path_report_sha256") != _sha256(report_path)
            or report.get("gate_status") != metrics["status"]
            or report.get("stage_count") != metrics["stage_count"]
            or report.get("reference_count") != metrics["reference_count"]
            or report.get("command_count") != metrics["command_count"]
            or receipt.get("stage_count") != metrics["stage_count"]
            or receipt.get("reference_count") != metrics["reference_count"]
            or receipt.get("command_count") != metrics["command_count"]
            or any(report.get(key) is not False for key in process_flags)
            or report.get("scientific_submission_ready") is not False
            or any(receipt.get(key) is not False for key in (*process_flags, "scientific_submission_ready"))
        ):
            raise R2ExternalGatePathError("R2 external gate-path receipt is invalid")
        if report.get("ordered_stages") != self.HANDOFF_ORDER or report.get("command_inventory") != self.COMMANDS:
            raise R2ExternalGatePathError("R2 external gate-path inventory is stale")
        if report.get("reference_receipts") != self._sources():
            raise R2ExternalGatePathError("R2 external gate-path source inventory is stale")
        if not all(
            not bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            for path in self.output_root.rglob("*")
        ):
            raise R2ExternalGatePathError("R2 external gate-path output is writable")
        return R2ExternalGatePathSummary(
            status=_string(report.get("status"), "R2 external gate-path status"),
            stage_count=_integer(report.get("stage_count"), "R2 external gate-path stage count"),
            reference_count=_integer(report.get("reference_count"), "R2 external gate-path reference count"),
            command_count=_integer(report.get("command_count"), "R2 external gate-path command count"),
            receipt_path=receipt_path,
        )
