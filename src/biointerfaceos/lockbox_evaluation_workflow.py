"""Run the evaluator-only, metadata-only one-shot lockbox protocol."""

# The evaluator output intentionally contains statuses and digests only.
# It never materializes protected values in development artifacts.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import (
    CONTRACT_STATUSES,
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    metadata_for,
    require_metadata,
)
from biointerfaceos.lockbox import LockboxFirewall


class LockboxEvaluationError(RuntimeError):
    """Raised when a one-shot evaluator run violates its frozen protocol."""


@dataclass(frozen=True)
class LockboxEvaluationSummary:
    """Summary of the sealed evaluator receipt."""

    release_id: str
    prediction_count: int
    contract_matched: int
    contract_contradicted: int
    contract_indeterminate: int
    abstentions: int
    raw_values_written: bool
    train_calls: int
    tune_calls: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LockboxEvaluationError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LockboxEvaluationError(f"{label} must be a non-empty string")
    return value.strip()


class LockboxEvaluationWorkflow:
    """Verify the signed pre-lock release and seal one metadata-only run."""

    REQUIRED_INPUTS = {
        "release manifest",
        "release receipt",
        "signature",
        "lockbox plan",
        "evaluator authorization",
        "prediction table",
    }
    ALLOWED_STATUSES = CONTRACT_STATUSES
    FORBIDDEN_OPERATIONS = frozenset({"train", "tune", "select", "rewrite_prediction"})

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = (
            fixture_path or self.root / "tests/fixtures/lockbox/evaluate_fixture.json"
        )
        self.output_root = (
            output_root or self.root / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0"
        )

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=False)
        if not path.is_relative_to(self.root):
            raise LockboxEvaluationError(f"{label} escaped repository")
        if "data/locked_test" in path.as_posix():
            raise LockboxEvaluationError(f"protected payload path is forbidden: {label}")
        if not path.is_file():
            raise LockboxEvaluationError(f"input file is missing: {label}")
        return path

    def _json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LockboxEvaluationError(f"cannot load {label}: {exc}") from exc

    def _fixture(self) -> dict[str, Any]:
        fixture = self._json(self.fixture_path, "lockbox evaluation fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "lockbox_evaluation_once":
            raise LockboxEvaluationError("lockbox fixture schema or mode is invalid")
        prereg = _mapping(fixture.get("preregistration"), "lockbox preregistration")
        if (
            prereg.get("release_id") != "bioif-internal-prelock-v1.0.0"
            or prereg.get("evaluated_at") != "2026-08-12T00:00:00+00:00"
        ):
            raise LockboxEvaluationError("lockbox evaluation identity is not frozen")
        if prereg.get("once") is not True or prereg.get("raw_values_allowed") is not False:
            raise LockboxEvaluationError("lockbox one-shot boundary is invalid")
        try:
            evidence_class, claim_level = require_metadata(fixture, "lockbox evaluation fixture")
        except EvidenceSemanticsError as exc:
            raise LockboxEvaluationError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.FIXTURE_TEST
            or claim_level is not AllowedClaimLevel.CONTRACT_TEST
        ):
            raise LockboxEvaluationError("lockbox fixture evidence class must remain contract-only")
        inputs = fixture.get("inputs")
        if (
            not isinstance(inputs, list)
            or {row.get("label") for row in inputs} != self.REQUIRED_INPUTS
        ):
            raise LockboxEvaluationError("lockbox input set is incomplete")
        return fixture

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "lockbox input")
            label = _string(row.get("label"), "lockbox input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            if _sha256(raw) != _string(row.get("sha256"), f"{label} checksum"):
                raise LockboxEvaluationError(f"input checksum differs: {label}")
            if _string(row.get("kind"), f"{label} kind") != "json":
                raise LockboxEvaluationError(f"lockbox input must be JSON: {label}")
            loaded[label] = self._json(path, label)
        return loaded

    @staticmethod
    def _verify_authorization(inputs: Mapping[str, Mapping[str, Any]]) -> None:
        manifest = inputs["release manifest"]
        receipt = inputs["release receipt"]
        signature = inputs["signature"]
        plan = inputs["lockbox plan"]
        auth = inputs["evaluator authorization"]
        if (
            manifest.get("status") != "FROZEN_INTERNAL_PRELOCK"
            or manifest.get("lockbox_accessed") is not False
        ):
            raise LockboxEvaluationError("signed release is not a valid pre-lock release")
        if (
            receipt.get("release_id") != manifest.get("release_id")
            or receipt.get("lockbox_accessed") is not False
        ):
            raise LockboxEvaluationError("release receipt boundary is invalid")
        if signature.get("signature") != receipt.get("signature") or not signature.get(
            "signed_manifest_sha256"
        ):
            raise LockboxEvaluationError("release signature metadata is invalid")
        if plan.get("scope") != "evaluator_only" or plan.get("development_access") is not False:
            raise LockboxEvaluationError("lockbox plan grants development access")
        if (
            auth.get("scope") != "evaluator_only"
            or auth.get("not_for_development") is not True
            or auth.get("lockbox_accessed") is not False
        ):
            raise LockboxEvaluationError("evaluator authorization is invalid")

    @classmethod
    def _predictions(cls, data: Mapping[str, Any]) -> list[dict[str, Any]]:
        table = _mapping(data["prediction table"], "prediction table")
        if table.get("protected_results_included") is not False:
            raise LockboxEvaluationError("prediction table includes protected results")
        rows = table.get("predictions")
        if not isinstance(rows, list) or len(rows) != 5:
            raise LockboxEvaluationError("prediction table must contain five predictions")
        normalized: list[dict[str, Any]] = []
        for row_value in rows:
            row = _mapping(row_value, "prediction row")
            prediction_id = _string(row.get("prediction_id"), "prediction id")
            if prediction_id not in {"P1", "P2", "P3", "P4", "P5"}:
                raise LockboxEvaluationError("unexpected prediction id")
            normalized.append(
                {
                    "prediction_id": prediction_id,
                    "status": row.get("status", "PREDICTED_BEFORE_LOCKBOX"),
                }
            )
        if {row["prediction_id"] for row in normalized} != {"P1", "P2", "P3", "P4", "P5"}:
            raise LockboxEvaluationError("prediction IDs are not unique")
        return normalized

    def run(self, *, release: str, once: bool) -> LockboxEvaluationSummary:
        """Run exactly one evaluator pass and seal metadata-only outputs."""
        if release != "FROZEN_DEV" or not once:
            raise LockboxEvaluationError("T109 requires --release FROZEN_DEV --once")
        if self.output_root.exists():
            raise LockboxEvaluationError("one-shot evaluation already executed; overwrite refused")
        fixture = self._fixture()
        inputs = self._inputs(fixture)
        self._verify_authorization(inputs)
        predictions = self._predictions(inputs)
        prereg = _mapping(fixture["preregistration"], "lockbox preregistration")
        operations = fixture.get("operations")
        if operations != [
            "verify_release",
            "load_prediction_metadata",
            "emit_aggregate_status",
            "seal_receipt",
        ]:
            raise LockboxEvaluationError(
                "evaluator operation sequence differs from preregistration"
            )
        if self.FORBIDDEN_OPERATIONS.intersection(str(item) for item in operations):
            raise LockboxEvaluationError("forbidden train/tune/select operation requested")
        result_rows = []
        for row in fixture["results"]:
            result = _mapping(row, "evaluator result")
            prediction_id = _string(result.get("prediction_id"), "evaluator prediction id")
            status = _string(result.get("status"), f"{prediction_id} status")
            digest = _string(result.get("metric_digest"), f"{prediction_id} metric digest")
            if (
                status not in self.ALLOWED_STATUSES
                or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
            ):
                raise LockboxEvaluationError(f"invalid metadata result for {prediction_id}")
            if not isinstance(result.get("abstained"), bool):
                raise LockboxEvaluationError(f"abstention flag is invalid for {prediction_id}")
            result_rows.append(
                {
                    "prediction_id": prediction_id,
                    "status": status,
                    "metric_digest": digest,
                    "abstained": result["abstained"],
                    "failure_class": _string(
                        result.get("failure_class"), f"{prediction_id} failure class"
                    ),
                }
            )
        if {row["prediction_id"] for row in result_rows} != {
            row["prediction_id"] for row in predictions
        }:
            raise LockboxEvaluationError("evaluator results do not cover the frozen predictions")
        if len(result_rows) != len(predictions):
            raise LockboxEvaluationError("evaluator result IDs are duplicated")
        counts = {
            status: sum(row["status"] == status for row in result_rows)
            for status in self.ALLOWED_STATUSES
        }
        abstentions = sum(row["abstained"] for row in result_rows)
        evaluation_results = {
            "schema_version": 1,
            "release_id": "bioif-internal-prelock-v1.0.0",
            "status": "SEALED_FIXTURE_CONTRACT_ONLY",
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "raw_values_written": False,
            "rows": result_rows,
        }
        operation_log = {
            "schema_version": 1,
            "release_id": "bioif-internal-prelock-v1.0.0",
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "operations": operations,
            "train_calls": 0,
            "tune_calls": 0,
            "selection_calls": 0,
            "prediction_rewrites": 0,
            "development_reads": False,
            "protected_values_read": False,
        }
        result_bytes = _canonical(evaluation_results)
        log_bytes = _canonical(operation_log)
        receipt = {
            "schema_version": 1,
            "status": "VALID_FIXTURE_CONTRACT_RUN_SEALED",
            "release_id": "bioif-internal-prelock-v1.0.0",
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "evaluated_at": prereg["evaluated_at"],
            "once": True,
            "first_run": True,
            "raw_values_written": False,
            "protected_values_read": False,
            "development_reads": False,
            "train_calls": 0,
            "tune_calls": 0,
            "prediction_rewrites": 0,
            "prediction_count": len(result_rows),
            "contract_matched": counts["CONTRACT_EXPECTATION_MET"],
            "contract_contradicted": counts["CONTRACT_EXPECTATION_CONTRADICTED"],
            "contract_indeterminate": counts["CONTRACT_EVIDENCE_INDETERMINATE"],
            "abstentions": abstentions,
            "evaluation_results_sha256": _sha256(result_bytes),
            "operation_log_sha256": _sha256(log_bytes),
            "receipt_key": _sha256(result_bytes + log_bytes),
        }
        payloads = {
            "evaluation_results.json": result_bytes,
            "operation_log.json": log_bytes,
            "first_run_receipt.json": _canonical(receipt),
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        for name, payload in payloads.items():
            (self.output_root / name).write_bytes(payload)
        for path in self.output_root.iterdir():
            path.chmod(0o444)
        self.output_root.chmod(0o555)
        self._scan_outputs()
        return LockboxEvaluationSummary(
            release_id="bioif-internal-prelock-v1.0.0",
            prediction_count=len(result_rows),
            contract_matched=counts["CONTRACT_EXPECTATION_MET"],
            contract_contradicted=counts["CONTRACT_EXPECTATION_CONTRADICTED"],
            contract_indeterminate=counts["CONTRACT_EVIDENCE_INDETERMINATE"],
            abstentions=abstentions,
            raw_values_written=False,
            train_calls=0,
            tune_calls=0,
            receipt_path=self.output_root / "first_run_receipt.json",
        )

    def verify(self) -> LockboxEvaluationSummary:
        """Verify the sealed first-run receipt without reading protected payloads."""
        if not self.output_root.is_dir():
            raise LockboxEvaluationError("sealed evaluation output is missing")
        receipt = self._json(self.output_root / "first_run_receipt.json", "first-run receipt")
        results = self._json(self.output_root / "evaluation_results.json", "evaluation results")
        log = self._json(self.output_root / "operation_log.json", "operation log")
        result_bytes = _canonical(results)
        log_bytes = _canonical(log)
        if (
            receipt.get("status") != "VALID_FIXTURE_CONTRACT_RUN_SEALED"
            or receipt.get("once") is not True
            or receipt.get("first_run") is not True
        ):
            raise LockboxEvaluationError("first-run receipt status is invalid")
        if receipt.get("evaluation_results_sha256") != _sha256(result_bytes) or receipt.get(
            "operation_log_sha256"
        ) != _sha256(log_bytes):
            raise LockboxEvaluationError("sealed evaluator hash mismatch")
        if (
            require_metadata(receipt, "sealed evaluator receipt")[0]
            is not EvidenceClass.FIXTURE_TEST
            or require_metadata(results, "sealed evaluation results")[0]
            is not EvidenceClass.FIXTURE_TEST
            or require_metadata(log, "sealed evaluator operation log")[0]
            is not EvidenceClass.FIXTURE_TEST
            or receipt.get("allowed_claim_level") != AllowedClaimLevel.CONTRACT_TEST.value
            or results.get("allowed_claim_level") != AllowedClaimLevel.CONTRACT_TEST.value
            or log.get("allowed_claim_level") != AllowedClaimLevel.CONTRACT_TEST.value
            or receipt.get("raw_values_written") is not False
            or receipt.get("protected_values_read") is not False
            or receipt.get("train_calls") != 0
            or receipt.get("tune_calls") != 0
        ):
            raise LockboxEvaluationError("sealed evaluator boundary is invalid")
        rows = results.get("rows")
        if not isinstance(rows, list):
            raise LockboxEvaluationError("sealed evaluator rows are invalid")
        counts = {
            status: sum(row.get("status") == status for row in rows)
            for status in self.ALLOWED_STATUSES
        }
        abstentions = sum(bool(row.get("abstained")) for row in rows)
        self._scan_outputs()
        return LockboxEvaluationSummary(
            release_id=str(receipt["release_id"]),
            prediction_count=len(rows),
            contract_matched=counts["CONTRACT_EXPECTATION_MET"],
            contract_contradicted=counts["CONTRACT_EXPECTATION_CONTRADICTED"],
            contract_indeterminate=counts["CONTRACT_EVIDENCE_INDETERMINATE"],
            abstentions=abstentions,
            raw_values_written=False,
            train_calls=int(receipt["train_calls"]),
            tune_calls=int(receipt["tune_calls"]),
            receipt_path=self.output_root / "first_run_receipt.json",
        )

    def _scan_outputs(self) -> None:
        """Scan production outputs with the repository firewall."""
        if not self.output_root.is_relative_to(self.root):
            return
        firewall = LockboxFirewall(self.root)
        contamination = firewall.scan(
            [self.output_root / "evaluation_results.json", self.output_root / "operation_log.json"]
        )
        if not contamination.clean:
            raise LockboxEvaluationError("sealed evaluator outputs are contaminated")
