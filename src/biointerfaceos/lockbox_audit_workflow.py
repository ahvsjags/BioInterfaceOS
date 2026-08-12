"""Audit sealed lockbox statuses without changing the frozen prediction package."""

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
    require_metadata,
)
from biointerfaceos.lockbox import LockboxFirewall


class LockboxAuditError(RuntimeError):
    """Raised when the post-lock audit contract is violated."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LockboxAuditError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LockboxAuditError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class LockboxAuditSummary:
    """Summary of the immutable post-lock audit."""

    audit_id: str
    prediction_count: int
    replicated: int
    refuted: int
    inconclusive: int
    abstentions: int
    claim_count: int
    receipt_path: Path


class LockboxAuditWorkflow:
    """Map sealed evaluator metadata to claims while preserving all boundaries."""

    RELEASE_ID = "bioif-internal-prelock-v1.0.0"
    AUDIT_ID = "bioif-lockbox-audit-v1.0.0"
    AUDITED_AT = "2026-08-12T00:00:00+00:00"
    ALLOWED_STATUSES = frozenset({"REPLICATED", "REFUTED", "INCONCLUSIVE"})
    REQUIRED_INPUTS = {
        "release manifest",
        "release receipt",
        "signature",
        "lockbox plan",
        "evaluator authorization",
        "prediction table",
        "claim matrix",
        "allowed wording",
        "evaluation results",
        "operation log",
        "first-run receipt",
    }
    EXPECTED_BINDINGS = {
        "C1": ("P1", "DEVELOPMENT_SUPPORTED"),
        "C2": ("P2", "DEVELOPMENT_SUPPORTED"),
        "C3": ("P3", "BOUNDED_BY_COUNTEREXAMPLES"),
        "C4": ("P4", "BOUNDED_BY_ABSTENTION"),
        "C5": ("P5", "EXPLORATORY_ONLY"),
    }
    EXPECTED_STATIC_CLAIMS = {
        "C6": ("LANGUAGE_GATE", "LANGUAGE_GATE_PRESERVED"),
        "C7": ("LANGUAGE_GATE", "APPLICABILITY_LIMIT_PRESERVED"),
        "C8": ("PRELOCK_ONLY", "EVALUATOR_AUTHORIZED_METADATA_ONLY"),
    }

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/lockbox/audit_fixture.json"
        self.output_root = output_root or (
            self.root / "reports/lockbox/audit/bioif-lockbox-audit-v1.0.0"
        )

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=False)
        if not path.is_relative_to(self.root):
            raise LockboxAuditError(f"{label} escaped repository")
        if "data/locked_test" in path.as_posix():
            raise LockboxAuditError(f"protected payload path is forbidden: {label}")
        if not path.is_file():
            raise LockboxAuditError(f"input file is missing: {label}")
        return path

    def _json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LockboxAuditError(f"cannot load {label}: {exc}") from exc

    def _fixture(self) -> dict[str, Any]:
        fixture = self._json(self.fixture_path, "lockbox audit fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "lockbox_audit_once":
            raise LockboxAuditError("lockbox audit fixture schema or mode is invalid")
        prereg = _mapping(fixture.get("preregistration"), "audit preregistration")
        if (
            prereg.get("audit_id") != self.AUDIT_ID
            or prereg.get("release_id") != self.RELEASE_ID
            or prereg.get("audited_at") != self.AUDITED_AT
            or prereg.get("once") is not True
        ):
            raise LockboxAuditError("audit identity is not frozen")
        inputs = fixture.get("inputs")
        if (
            not isinstance(inputs, list)
            or {row.get("label") for row in inputs} != self.REQUIRED_INPUTS
        ):
            raise LockboxAuditError("lockbox audit input set is incomplete")
        return fixture

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "lockbox audit input")
            label = _string(row.get("label"), "audit input label")
            path = self._path(row.get("path"), f"{label} path")
            if _string(row.get("kind"), f"{label} kind") != "json":
                raise LockboxAuditError(f"audit input must be JSON: {label}")
            if _sha256(path) != _string(row.get("sha256"), f"{label} checksum"):
                raise LockboxAuditError(f"input checksum differs: {label}")
            loaded[label] = self._json(path, label)
        return loaded

    @staticmethod
    def _verify_release(inputs: Mapping[str, Mapping[str, Any]]) -> None:
        manifest = inputs["release manifest"]
        receipt = inputs["release receipt"]
        signature = inputs["signature"]
        plan = inputs["lockbox plan"]
        auth = inputs["evaluator authorization"]
        if (
            manifest.get("status") != "FROZEN_INTERNAL_PRELOCK"
            or manifest.get("lockbox_accessed") is not False
        ):
            raise LockboxAuditError("signed release is not a valid pre-lock release")
        if (
            receipt.get("release_id") != manifest.get("release_id")
            or receipt.get("lockbox_accessed") is not False
        ):
            raise LockboxAuditError("release receipt boundary is invalid")
        if signature.get("signature") != receipt.get("signature") or not signature.get(
            "signed_manifest_sha256"
        ):
            raise LockboxAuditError("release signature metadata is invalid")
        if plan.get("scope") != "evaluator_only" or plan.get("development_access") is not False:
            raise LockboxAuditError("lockbox plan grants development access")
        if (
            auth.get("scope") != "evaluator_only"
            or auth.get("not_for_development") is not True
            or auth.get("lockbox_accessed") is not False
        ):
            raise LockboxAuditError("evaluator authorization is invalid")

    @classmethod
    def _validate_prediction_table(cls, table: Mapping[str, Any]) -> list[dict[str, str]]:
        if table.get("protected_results_included") is not False:
            raise LockboxAuditError("prediction table includes protected results")
        rows = table.get("predictions")
        if not isinstance(rows, list) or len(rows) != 5:
            raise LockboxAuditError("prediction table must contain five predictions")
        normalized: list[dict[str, str]] = []
        for value in rows:
            row = _mapping(value, "prediction row")
            prediction_id = _string(row.get("prediction_id"), "prediction id")
            candidate_id = _string(row.get("candidate_id"), f"{prediction_id} candidate id")
            if row.get("status") != "PREDICTED_BEFORE_LOCKBOX":
                raise LockboxAuditError("prediction table was changed after pre-lock")
            normalized.append({"prediction_id": prediction_id, "candidate_id": candidate_id})
        if {row["prediction_id"] for row in normalized} != {"P1", "P2", "P3", "P4", "P5"}:
            raise LockboxAuditError("prediction IDs are not unique or complete")
        expected_candidates = {"P1": "C1", "P2": "C2", "P3": "C3", "P4": "C4", "P5": "C5"}
        if {row["prediction_id"]: row["candidate_id"] for row in normalized} != expected_candidates:
            raise LockboxAuditError("prediction-to-candidate binding was changed")
        return normalized

    @classmethod
    def _validate_claim_matrix(cls, matrix: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        rows = matrix.get("claims")
        if not isinstance(rows, list) or len(rows) != 8:
            raise LockboxAuditError("claim matrix must contain eight claims")
        indexed: dict[str, dict[str, Any]] = {}
        for value in rows:
            row = _mapping(value, "claim row")
            claim_id = _string(row.get("claim_id"), "claim id")
            if claim_id in indexed:
                raise LockboxAuditError("claim IDs are duplicated")
            indexed[claim_id] = row
        if set(indexed) != set(cls.EXPECTED_BINDINGS) | set(cls.EXPECTED_STATIC_CLAIMS):
            raise LockboxAuditError("claim matrix IDs are incomplete")
        for claim_id, (_, before) in cls.EXPECTED_BINDINGS.items():
            if indexed[claim_id].get("status") != before:
                raise LockboxAuditError(f"claim threshold/status changed: {claim_id}")
        for claim_id, (before, _) in cls.EXPECTED_STATIC_CLAIMS.items():
            if indexed[claim_id].get("status") != before:
                raise LockboxAuditError(f"claim language/applicability gate changed: {claim_id}")
        return indexed

    @staticmethod
    def _verify_wording(wording: Mapping[str, Any]) -> None:
        blocked = set(wording.get("blocked", []))
        required = {"causes", "mediates", "universal law", "universal transfer"}
        if not required.issubset(blocked):
            raise LockboxAuditError("blocked wording gate was weakened")
        rules = set(wording.get("global_rules", []))
        if (
            "association-only wording for mediation" not in rules
            or "narrow applicability under OOD and selection sensitivity" not in rules
        ):
            raise LockboxAuditError("language/applicability limits were weakened")

    @staticmethod
    def _verify_evaluation(inputs: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        results = inputs["evaluation results"]
        log = inputs["operation log"]
        receipt = inputs["first-run receipt"]
        try:
            evidence_class, claim_level = require_metadata(receipt, "first-run receipt")
        except EvidenceSemanticsError as exc:
            raise LockboxAuditError(
                "legacy fixture evaluation cannot be consumed by a new scientific audit"
            ) from exc
        if (
            evidence_class is not EvidenceClass.LOCKED_EVALUATION
            or claim_level is not AllowedClaimLevel.EVALUATOR_BACKED
        ):
            raise LockboxAuditError(
                "only independently evaluator-backed locked evidence may enter a scientific audit"
            )
        if (
            results.get("status") != "SEALED_METADATA_ONLY"
            or results.get("raw_values_written") is not False
        ):
            raise LockboxAuditError("evaluation results are not metadata-only")
        if (
            receipt.get("status") != "VALID_FIRST_RUN_SEALED"
            or receipt.get("first_run") is not True
            or receipt.get("once") is not True
        ):
            raise LockboxAuditError("first-run receipt is not sealed")
        if receipt.get("release_id") != LockboxAuditWorkflow.RELEASE_ID:
            raise LockboxAuditError("evaluation release ID differs")
        if receipt.get("evaluation_results_sha256") != _sha256_bytes(_canonical(results)):
            raise LockboxAuditError("evaluation result hash differs from receipt")
        if receipt.get("operation_log_sha256") != _sha256_bytes(_canonical(log)):
            raise LockboxAuditError("operation log hash differs from receipt")
        if (
            log.get("operations")
            != [
                "verify_release",
                "load_prediction_metadata",
                "emit_aggregate_status",
                "seal_receipt",
            ]
            or log.get("train_calls") != 0
            or log.get("tune_calls") != 0
            or log.get("selection_calls") != 0
            or log.get("prediction_rewrites") != 0
            or log.get("development_reads") is not False
            or log.get("protected_values_read") is not False
        ):
            raise LockboxAuditError("evaluation operation log violates the frozen protocol")
        try:
            require_metadata(results, "evaluation results")
            require_metadata(log, "operation log")
        except EvidenceSemanticsError as exc:
            raise LockboxAuditError("evaluation evidence metadata is invalid") from exc
        rows = results.get("rows")
        if not isinstance(rows, list) or len(rows) != 5:
            raise LockboxAuditError("sealed evaluation does not contain five rows")
        ids = [row.get("prediction_id") for row in rows]
        if set(ids) != {"P1", "P2", "P3", "P4", "P5"} or len(ids) != len(set(ids)):
            raise LockboxAuditError("sealed evaluation IDs are not unique and complete")
        for value in rows:
            row = _mapping(value, "sealed evaluation row")
            if row.get("status") not in LockboxAuditWorkflow.ALLOWED_STATUSES:
                raise LockboxAuditError("sealed evaluation status is invalid")
            if not isinstance(row.get("abstained"), bool):
                raise LockboxAuditError("sealed abstention flag is invalid")
            if not isinstance(row.get("failure_class"), str) or not row["failure_class"]:
                raise LockboxAuditError("sealed failure class is missing")
            if "raw_value" in row or "protected_value" in row:
                raise LockboxAuditError("protected value entered audit input")
        return [dict(row) for row in rows]

    @staticmethod
    def _status_after(status: str) -> str:
        return {
            "REPLICATED": "POSTLOCK_REPLICATED",
            "REFUTED": "POSTLOCK_REFUTED",
            "INCONCLUSIVE": "POSTLOCK_INCONCLUSIVE",
        }[status]

    def _build_outputs(
        self,
        inputs: Mapping[str, Mapping[str, Any]],
        predictions: list[dict[str, str]],
        claims: Mapping[str, Mapping[str, Any]],
        results: list[dict[str, Any]],
        audited_at: str,
    ) -> dict[str, bytes]:
        result_by_id = {row["prediction_id"]: row for row in results}
        prediction_by_id = {row["prediction_id"]: row for row in predictions}
        transitions: list[dict[str, Any]] = []
        for claim_id, (prediction_id, before) in self.EXPECTED_BINDINGS.items():
            result = result_by_id[prediction_id]
            transitions.append(
                {
                    "claim_id": claim_id,
                    "prediction_id": prediction_id,
                    "before_status": before,
                    "postlock_status": result["status"],
                    "after_status": self._status_after(result["status"]),
                    "candidate_id": prediction_by_id[prediction_id]["candidate_id"],
                    "abstained": result["abstained"],
                    "failure_class": result["failure_class"],
                    "threshold_changed": False,
                    "prediction_rewritten": False,
                    "evidence": [
                        "release/manuscripts/paper_c_prelock/claim_matrix.json",
                        "release/manuscripts/paper_c_prelock/prediction_table.json",
                        "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/evaluation_results.json",
                        "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/first_run_receipt.json",
                    ],
                }
            )
        for claim_id, (before, after) in self.EXPECTED_STATIC_CLAIMS.items():
            transitions.append(
                {
                    "claim_id": claim_id,
                    "prediction_id": None,
                    "before_status": before,
                    "postlock_status": None,
                    "after_status": after,
                    "abstained": False,
                    "failure_class": "preserved_boundary",
                    "threshold_changed": False,
                    "prediction_rewritten": False,
                    "evidence": [
                        "release/manuscripts/paper_c_prelock/claim_matrix.json",
                        "release/manuscripts/paper_c_prelock/allowed_wording.json",
                        "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/first_run_receipt.json",
                    ],
                }
            )
        prediction_counts = {
            status: sum(row["status"] == status for row in results)
            for status in self.ALLOWED_STATUSES
        }
        abstentions = sum(row["abstained"] for row in results)
        claim_transitions = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "release_id": self.RELEASE_ID,
            "audited_at": audited_at,
            "status": "VALID_POSTLOCK_AUDIT",
            "transitions": transitions,
        }
        failure_analysis = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "failures": [
                {
                    "prediction_id": row["prediction_id"],
                    "status": row["status"],
                    "abstained": row["abstained"],
                    "failure_class": row["failure_class"],
                    "disposition": (
                        "retain_inconclusive"
                        if row["status"] == "INCONCLUSIVE"
                        else "retain_refuted"
                        if row["status"] == "REFUTED"
                        else "none"
                    ),
                }
                for row in results
                if row["status"] != "REPLICATED" or row["abstained"]
            ],
            "raw_values_included": False,
            "protected_values_read": False,
        }
        source_hashes = {
            label.replace(" ", "_"): _sha256(self._path(row["path"], f"{label} path"))
            for row in self._fixture()["inputs"]
            for label in [_string(row["label"], "audit input label")]
        }
        audit_report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "release_id": self.RELEASE_ID,
            "audited_at": audited_at,
            "status": "VALID_POSTLOCK_AUDIT",
            "prediction_count": len(results),
            "replicated": prediction_counts["REPLICATED"],
            "refuted": prediction_counts["REFUTED"],
            "inconclusive": prediction_counts["INCONCLUSIVE"],
            "abstentions": abstentions,
            "claim_count": len(transitions),
            "threshold_changes": 0,
            "prediction_rewrites": 0,
            "raw_values_written": False,
            "protected_values_read": False,
            "language_gates_preserved": True,
            "applicability_limits_preserved": True,
            "source_hashes": source_hashes,
        }
        transition_bytes = _canonical(claim_transitions)
        failure_bytes = _canonical(failure_analysis)
        report_bytes = _canonical(audit_report)
        receipt = {
            "schema_version": 1,
            "status": "VALID_POSTLOCK_AUDIT_SEALED",
            "audit_id": self.AUDIT_ID,
            "release_id": self.RELEASE_ID,
            "audited_at": audited_at,
            "once": True,
            "prediction_count": len(results),
            "replicated": prediction_counts["REPLICATED"],
            "refuted": prediction_counts["REFUTED"],
            "inconclusive": prediction_counts["INCONCLUSIVE"],
            "abstentions": abstentions,
            "claim_count": len(transitions),
            "threshold_changes": 0,
            "prediction_rewrites": 0,
            "raw_values_written": False,
            "protected_values_read": False,
            "claim_transitions_sha256": _sha256_bytes(transition_bytes),
            "failure_analysis_sha256": _sha256_bytes(failure_bytes),
            "audit_report_sha256": _sha256_bytes(report_bytes),
            "receipt_key": _sha256_bytes(transition_bytes + failure_bytes + report_bytes),
        }
        return {
            "claim_transitions.json": transition_bytes,
            "failure_analysis.json": failure_bytes,
            "audit_report.json": report_bytes,
            "audit_receipt.json": _canonical(receipt),
        }

    def _scan_outputs(self) -> None:
        if not self.output_root.is_relative_to(self.root):
            return
        firewall = LockboxFirewall(self.root)
        paths = [
            self.output_root / name
            for name in (
                "claim_transitions.json",
                "failure_analysis.json",
                "audit_report.json",
                "audit_receipt.json",
            )
        ]
        contamination = firewall.scan(paths)
        if not contamination.clean:
            raise LockboxAuditError("post-lock audit outputs are contaminated")

    def run(self, *, strict: bool = False) -> LockboxAuditSummary:
        if not strict:
            raise LockboxAuditError("T110 requires --strict")
        if self.output_root.exists():
            raise LockboxAuditError("post-lock audit already executed; overwrite refused")
        fixture = self._fixture()
        inputs = self._inputs(fixture)
        self._verify_release(inputs)
        predictions = self._validate_prediction_table(inputs["prediction table"])
        claims = self._validate_claim_matrix(inputs["claim matrix"])
        self._verify_wording(inputs["allowed wording"])
        results = self._verify_evaluation(inputs)
        outputs = self._build_outputs(inputs, predictions, claims, results, self.AUDITED_AT)
        self.output_root.mkdir(parents=True, exist_ok=False)
        for name, payload in outputs.items():
            (self.output_root / name).write_bytes(payload)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        self._scan_outputs()
        return LockboxAuditSummary(
            audit_id=self.AUDIT_ID,
            prediction_count=len(results),
            replicated=sum(row["status"] == "REPLICATED" for row in results),
            refuted=sum(row["status"] == "REFUTED" for row in results),
            inconclusive=sum(row["status"] == "INCONCLUSIVE" for row in results),
            abstentions=sum(row["abstained"] for row in results),
            claim_count=8,
            receipt_path=self.output_root / "audit_receipt.json",
        )

    def verify(self) -> LockboxAuditSummary:
        if not self.output_root.is_dir():
            raise LockboxAuditError("post-lock audit output is missing")
        transition_path = self.output_root / "claim_transitions.json"
        failure_path = self.output_root / "failure_analysis.json"
        report_path = self.output_root / "audit_report.json"
        receipt = self._json(self.output_root / "audit_receipt.json", "audit receipt")
        transitions = self._json(transition_path, "claim transitions")
        failure = self._json(failure_path, "failure analysis")
        report = self._json(report_path, "audit report")
        if (
            receipt.get("status") != "VALID_POSTLOCK_AUDIT_SEALED"
            or receipt.get("once") is not True
        ):
            raise LockboxAuditError("audit receipt status is invalid")
        if (
            receipt.get("claim_transitions_sha256") != _sha256(transition_path)
            or receipt.get("failure_analysis_sha256") != _sha256(failure_path)
            or receipt.get("audit_report_sha256") != _sha256(report_path)
        ):
            raise LockboxAuditError("post-lock audit hash mismatch")
        if (
            transitions.get("status") != "VALID_POSTLOCK_AUDIT"
            or len(transitions.get("transitions", [])) != 8
            or failure.get("raw_values_included") is not False
            or failure.get("protected_values_read") is not False
            or report.get("threshold_changes") != 0
            or report.get("prediction_rewrites") != 0
            or report.get("raw_values_written") is not False
            or report.get("protected_values_read") is not False
        ):
            raise LockboxAuditError("post-lock audit boundary is invalid")
        for field in (
            "audit_id",
            "release_id",
            "prediction_count",
            "replicated",
            "refuted",
            "inconclusive",
            "abstentions",
            "claim_count",
            "threshold_changes",
            "prediction_rewrites",
        ):
            if receipt.get(field) != report.get(field):
                raise LockboxAuditError(f"audit receipt summary differs: {field}")
        prediction_rows = [row for row in transitions["transitions"] if row.get("prediction_id")]
        if (
            len(prediction_rows) != 5
            or {row.get("postlock_status") for row in prediction_rows} != self.ALLOWED_STATUSES
        ):
            raise LockboxAuditError("post-lock prediction status coverage is incomplete")
        self._scan_outputs()
        return LockboxAuditSummary(
            audit_id=str(receipt["audit_id"]),
            prediction_count=int(receipt["prediction_count"]),
            replicated=int(receipt["replicated"]),
            refuted=int(receipt["refuted"]),
            inconclusive=int(receipt["inconclusive"]),
            abstentions=int(receipt["abstentions"]),
            claim_count=int(receipt["claim_count"]),
            receipt_path=self.output_root / "audit_receipt.json",
        )
