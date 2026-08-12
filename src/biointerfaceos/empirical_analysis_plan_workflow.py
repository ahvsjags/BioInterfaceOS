"""Freeze and audit the outcome-free empirical analysis contract for T121."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    require_metadata,
)


class EmpiricalAnalysisPlanError(RuntimeError):
    """Raised when an empirical plan is incomplete, outcome-bearing, or unsafe."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EmpiricalAnalysisPlanError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EmpiricalAnalysisPlanError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise EmpiricalAnalysisPlanError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class EmpiricalAnalysisPlanSummary:
    """Compact accounting for a validated, outcome-free T121 analysis contract."""

    plan_id: str
    estimand_count: int
    available_development_estimands: int
    unavailable_held_out_estimands: int
    receipt_path: Path


class EmpiricalAnalysisPlanWorkflow:
    """Validate the analysis plan without calculating an outcome or fitting a model."""

    PLAN_ID = "bioif-r2-empirical-analysis-plan-v1.1.0"
    PLAN_FROZEN_AT = "2026-08-12T00:00:00+00:00"
    PLAN_RELATIVE = "data/empirical/R2_ANALYSIS_PLAN.json"
    T120_RECEIPT_RELATIVE = "reports/review_round_2/empirical_provenance/v1.1.0/audit_receipt.json"
    OUTPUT_RELATIVE = "reports/review_round_2/empirical_analysis_plan/v1.1.0"
    REQUIRED_PLAN_FIELDS = {
        "schema_version",
        "plan_id",
        "evidence_class",
        "allowed_claim_level",
        "source_registry_id",
        "source_audit_receipt",
        "scope",
        "primary_independent_unit",
        "estimands",
        "split_manifest",
        "model_selection",
        "intervals",
        "multiplicity",
        "missingness",
        "prohibited_actions",
        "claim_boundary",
    }
    REQUIRED_ESTIMAND_FIELDS = {
        "estimand_id",
        "status",
        "outcome_endpoint_id",
        "target_population",
        "independent_unit",
        "minimum_effective_n",
        "analysis_class",
        "analysis_rule",
        "confirmatory",
    }
    FORBIDDEN_RESULT_FIELDS = frozenset(
        {
            "accuracy",
            "auc",
            "effect_size",
            "mean",
            "median",
            "metric_result",
            "observed_value",
            "p_value",
            "raw_value",
        }
    )

    def __init__(
        self,
        root: Path,
        *,
        plan_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.plan_path = plan_path or self.root / self.PLAN_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EmpiricalAnalysisPlanError(f"cannot parse {label}") from exc

    @classmethod
    def _contains_result_field(cls, value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                key in cls.FORBIDDEN_RESULT_FIELDS or cls._contains_result_field(item)
                for key, item in value.items()
            )
        if isinstance(value, list):
            return any(cls._contains_result_field(item) for item in value)
        return False

    def _source_receipt(self, plan: dict[str, Any]) -> dict[str, Any]:
        reference = _mapping(plan.get("source_audit_receipt"), "source audit receipt reference")
        if set(reference) != {"path", "sha256"}:
            raise EmpiricalAnalysisPlanError("source audit receipt reference fields are invalid")
        relative = _string(reference.get("path"), "source audit receipt path")
        if relative != self.T120_RECEIPT_RELATIVE:
            raise EmpiricalAnalysisPlanError("analysis plan must use the immutable T120 receipt")
        receipt_path = (self.root / relative).resolve(strict=False)
        if not receipt_path.is_relative_to(self.root) or not receipt_path.is_file():
            raise EmpiricalAnalysisPlanError("T120 receipt is missing")
        if _string(reference.get("sha256"), "source audit receipt SHA-256") != _sha256(
            receipt_path
        ):
            raise EmpiricalAnalysisPlanError("T120 receipt checksum differs")
        receipt = self._json(receipt_path, "T120 receipt")
        if (
            receipt.get("status") != "PASS_EMPIRICAL_PROVENANCE"
            or receipt.get("registry_id") != plan.get("source_registry_id")
            or receipt.get("empirical_source") is not True
            or receipt.get("statistical_conclusions") is not False
            or receipt.get("independent_validation") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise EmpiricalAnalysisPlanError("T120 receipt crosses the evidence boundary")
        return receipt

    @staticmethod
    def _exact(value: Any, expected: dict[str, Any], label: str) -> None:
        if _mapping(value, label) != expected:
            raise EmpiricalAnalysisPlanError(f"{label} is not frozen as required")

    def _validate_plan(self) -> tuple[dict[str, Any], dict[str, Any]]:
        plan = self._json(self.plan_path, "empirical analysis plan")
        if set(plan) != self.REQUIRED_PLAN_FIELDS or plan.get("schema_version") != 1:
            raise EmpiricalAnalysisPlanError("analysis plan fields or schema are invalid")
        if plan.get("plan_id") != self.PLAN_ID or plan.get("scope") != "DEVELOPMENT_ONLY":
            raise EmpiricalAnalysisPlanError("analysis plan identity or scope is invalid")
        try:
            evidence_class, claim_level = require_metadata(plan, "empirical analysis plan")
        except EvidenceSemanticsError as exc:
            raise EmpiricalAnalysisPlanError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise EmpiricalAnalysisPlanError("analysis plan evidence metadata is unsafe")
        if self._contains_result_field(plan):
            raise EmpiricalAnalysisPlanError(
                "analysis plan contains an outcome or performance field"
            )
        receipt = self._source_receipt(plan)
        self._exact(
            plan["primary_independent_unit"],
            {
                "name": "giant unilamellar vesicle",
                "identifier_field": "independent_unit_id",
                "nesting_order": [
                    "source_id",
                    "study_id",
                    "laboratory",
                    "biological_system",
                    "independent_unit_id",
                ],
            },
            "primary independent unit",
        )
        self._exact(
            plan["split_manifest"],
            {
                "development_source_ids": ["LEEDS-1450"],
                "held_out_source_ids": [],
                "held_out_group_key": "study_id",
                "held_out_policy": "REQUIRED_BEFORE_T122",
                "current_status": "UNAVAILABLE_PENDING_ADDITIONAL_STUDIES",
            },
            "study-held-out split manifest",
        )
        self._exact(
            plan["model_selection"],
            {
                "outer_split": "STUDY_HELD_OUT",
                "inner_selection": "NESTED_GROUP_CV",
                "group_key": "study_id",
                "minimum_distinct_studies": 3,
                "current_status": "UNAVAILABLE_PENDING_ADDITIONAL_STUDIES",
                "selection_before_held_out_access": True,
            },
            "nested model-selection protocol",
        )
        self._exact(
            plan["intervals"],
            {
                "method": "study-clustered bootstrap percentile interval",
                "cluster_key": "study_id",
                "minimum_distinct_studies": 3,
                "current_status": "UNAVAILABLE_PENDING_ADDITIONAL_STUDIES",
            },
            "cluster-aware interval policy",
        )
        self._exact(
            plan["multiplicity"],
            {
                "family": "all endpoint-protocol estimands in one registered analysis family",
                "method": "Holm step-down",
                "current_status": "FROZEN_FOR_FUTURE_MULTI_ENDPOINT_ANALYSES",
            },
            "multiplicity policy",
        )
        self._exact(
            plan["missingness"],
            {
                "endpoint_values": "do not impute",
                "independent_unit_identity": "do not impute",
                "reporting": (
                    "report missing cells, excluded units and exclusion reasons before any analysis"
                ),
                "complete_case_substitution": "prohibited without a new registered amendment",
            },
            "missingness policy",
        )
        prohibited_actions = plan["prohibited_actions"]
        expected_prohibitions = {
            "no outcome analysis in T121",
            "no fixture or synthetic replacement",
            "no current-study held-out label",
            "no model fitting or performance claim",
            "no independent validation claim",
        }
        if (
            not isinstance(prohibited_actions, list)
            or set(prohibited_actions) != expected_prohibitions
        ):
            raise EmpiricalAnalysisPlanError("prohibited-action boundary is invalid")
        _string(plan.get("claim_boundary"), "analysis-plan claim boundary")
        estimands = plan["estimands"]
        if not isinstance(estimands, list) or len(estimands) != 2:
            raise EmpiricalAnalysisPlanError("analysis plan must define two estimands")
        ids: set[str] = set()
        available = 0
        unavailable = 0
        for value in estimands:
            estimand = _mapping(value, "analysis estimand")
            if set(estimand) != self.REQUIRED_ESTIMAND_FIELDS:
                raise EmpiricalAnalysisPlanError("analysis estimand fields are invalid")
            estimand_id = _string(estimand.get("estimand_id"), "estimand ID")
            if estimand_id in ids:
                raise EmpiricalAnalysisPlanError("analysis estimand IDs are not unique")
            ids.add(estimand_id)
            _string(estimand.get("outcome_endpoint_id"), "estimand endpoint")
            _string(estimand.get("target_population"), "estimand target population")
            _string(estimand.get("independent_unit"), "estimand independent unit")
            _string(estimand.get("analysis_class"), "estimand analysis class")
            _string(estimand.get("analysis_rule"), "estimand analysis rule")
            if estimand.get("confirmatory") is not False:
                raise EmpiricalAnalysisPlanError("all T121 estimands must remain non-confirmatory")
            minimum_n = _integer(estimand.get("minimum_effective_n"), "estimand minimum n")
            if estimand_id == "E001_GUV_SHRINKING_RATE_DEVELOPMENT_DESCRIPTION":
                if (
                    estimand.get("status") != "PLANNED_DEVELOPMENT_ONLY"
                    or minimum_n != receipt.get("observation_count")
                    or estimand.get("analysis_class") != "DESCRIPTIVE_WITHOUT_CONFIRMATORY_TEST"
                ):
                    raise EmpiricalAnalysisPlanError(
                        "development estimand is not source-constrained"
                    )
                available += 1
            elif estimand_id == "E002_STUDY_HELD_OUT_TRANSPORT":
                if (
                    estimand.get("status") != "UNAVAILABLE_PENDING_ADDITIONAL_STUDIES"
                    or minimum_n != 3
                    or estimand.get("analysis_class") != "STUDY_HELD_OUT_EVALUATION"
                ):
                    raise EmpiricalAnalysisPlanError("held-out estimand must remain unavailable")
                unavailable += 1
            else:
                raise EmpiricalAnalysisPlanError("unknown analysis estimand")
        if available != 1 or unavailable != 1:
            raise EmpiricalAnalysisPlanError("analysis-plan availability accounting is invalid")
        return plan, receipt

    def run(self, *, strict: bool = False) -> EmpiricalAnalysisPlanSummary:
        """Freeze one immutable plan receipt without reading outcome values."""

        if not strict:
            raise EmpiricalAnalysisPlanError("T121 requires --strict")
        if self.output_root.exists():
            raise EmpiricalAnalysisPlanError("empirical analysis plan already frozen")
        plan, receipt = self._validate_plan()
        self.output_root.mkdir(parents=True, exist_ok=False)
        plan_path = self.output_root / "frozen_analysis_plan.json"
        self._write(plan_path, plan)
        plan_receipt = {
            "schema_version": 1,
            "plan_id": self.PLAN_ID,
            "frozen_at": self.PLAN_FROZEN_AT,
            "status": "PASS_EMPIRICAL_ANALYSIS_PLAN",
            "source_registry_id": plan["source_registry_id"],
            "source_audit_receipt_sha256": _sha256(self.root / self.T120_RECEIPT_RELATIVE),
            "plan_sha256": _sha256(plan_path),
            "estimand_count": 2,
            "available_development_estimands": 1,
            "unavailable_held_out_estimands": 1,
            "source_observation_count": receipt["observation_count"],
            "plan_frozen": True,
            "outcome_analysis_run": False,
            "model_fitted": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "analysis_plan_receipt.json"
        self._write(receipt_path, plan_receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return EmpiricalAnalysisPlanSummary(
            plan_id=self.PLAN_ID,
            estimand_count=2,
            available_development_estimands=1,
            unavailable_held_out_estimands=1,
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable plan receipt without running an empirical analysis."""

        plan_path = self.output_root / "frozen_analysis_plan.json"
        receipt_path = self.output_root / "analysis_plan_receipt.json"
        frozen_plan = self._json(plan_path, "frozen analysis plan")
        receipt = self._json(receipt_path, "analysis-plan receipt")
        if (
            receipt.get("plan_id") != self.PLAN_ID
            or receipt.get("status") != "PASS_EMPIRICAL_ANALYSIS_PLAN"
            or receipt.get("plan_sha256") != _sha256(plan_path)
            or receipt.get("source_audit_receipt_sha256")
            != _sha256(self.root / self.T120_RECEIPT_RELATIVE)
            or receipt.get("plan_frozen") is not True
            or receipt.get("outcome_analysis_run") is not False
            or receipt.get("model_fitted") is not False
            or receipt.get("independent_validation") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise EmpiricalAnalysisPlanError("analysis-plan receipt is invalid")
        return frozen_plan
