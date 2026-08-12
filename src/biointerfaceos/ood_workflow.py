"""Fixture-backed leave-group OOD and sensitivity workflow."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class OODWorkflowError(RuntimeError):
    """Raised when the T100 OOD contract is invalid."""


@dataclass(frozen=True)
class OODSummary:
    """Summary of leave-group and sensitivity evaluation."""

    dimensions: int
    groups: int
    low_n_groups: int
    leave_largest: int
    sensitivity_records: int
    primary_records: int
    calibration_records: int
    selective_risk_records: int
    claim_status: str
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OODWorkflowError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OODWorkflowError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise OODWorkflowError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise OODWorkflowError(f"{label} must be finite")
    return result


class OODWorkflow:
    """Run all frozen group dimensions without outcome-dependent keys."""

    DIMENSIONS = ("study", "lab", "family", "species", "biofluid", "time")
    SENSITIVITY = ("leave_largest_study", "drop_low_n", "evidence_grade_only")

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/robustness/ood_fixture.json"
        self.output_root = output_root or self.root / "reports/robustness/ood"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")), "OOD fixture"
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise OODWorkflowError(f"cannot load OOD fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != (
            "ood_leave_group_and_sensitivity"
        ):
            raise OODWorkflowError("OOD fixture schema or mode is invalid")
        for key in ("inputs", "preregistration", "group_rows", "sensitivity_rows"):
            if key not in data:
                raise OODWorkflowError(f"OOD fixture is missing {key}")
        if not all(
            isinstance(data[key], list) for key in ("inputs", "group_rows", "sensitivity_rows")
        ):
            raise OODWorkflowError("OOD fixture list fields are invalid")
        preregistration = _mapping(data["preregistration"], "OOD preregistration")
        if preregistration.get("schema_version") != 1:
            raise OODWorkflowError("OOD preregistration schema is invalid")
        if preregistration.get("group_dimensions") != list(self.DIMENSIONS):
            raise OODWorkflowError("OOD group dimensions are not frozen")
        if preregistration.get("sensitivity_scenarios") != list(self.SENSITIVITY):
            raise OODWorkflowError("OOD sensitivity scenarios are not frozen")
        if preregistration.get("target_values_exposed") is not False:
            raise OODWorkflowError("OOD target values must remain hidden")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        path = self.root / "reports/robustness/ablations/ablations_receipt.json"
        checksum = "bde553a6a188e2b0a733495d8b89493f9573086e05dd639db7c47edb7a2cee54"
        seen = False
        for value in fixture["inputs"]:
            row = _mapping(value, "OOD input")
            label = _string(row.get("label"), "OOD input label")
            if label != "T099 ablations receipt":
                raise OODWorkflowError(f"unexpected OOD input: {label}")
            declared = (self.root / _string(row.get("path"), "OOD input path")).resolve(strict=True)
            raw = path.read_bytes()
            payload = _mapping(json.loads(raw), "T099 ablations payload")
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise OODWorkflowError("OOD input path/checksum differs")
            if _sha256(raw) != checksum or payload.get("status") != "VALID":
                raise OODWorkflowError("T099 ablation receipt is not valid")
            seen = True
        if not seen:
            raise OODWorkflowError("T099 ablation receipt is missing")

    @classmethod
    def _rows(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        required = {
            "dimension",
            "group_id",
            "n",
            "primary_metric",
            "calibration_error",
            "selective_risk",
            "coverage",
            "ood",
            "evidence_grade",
            "is_largest_group",
            "key_source",
        }
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for value in fixture["group_rows"]:
            source = _mapping(value, "OOD group row")
            if set(source) != required:
                raise OODWorkflowError("OOD group fields do not match schema")
            dimension = _string(source.get("dimension"), "OOD dimension")
            group_id = _string(source.get("group_id"), "OOD group ID")
            if dimension not in cls.DIMENSIONS or (dimension, group_id) in seen:
                raise OODWorkflowError("OOD dimension/group is invalid or duplicated")
            if source.get("key_source") != "pre_outcome_group_key":
                raise OODWorkflowError("OOD group key is outcome-dependent")
            if not isinstance(source.get("ood"), bool) or not isinstance(
                source.get("is_largest_group"), bool
            ):
                raise OODWorkflowError("OOD group flags are invalid")
            rows.append(
                {
                    "dimension": dimension,
                    "group_id": group_id,
                    "n": int(_number(source.get("n"), "OOD group n")),
                    "primary_metric": round(
                        _number(source.get("primary_metric"), "primary metric"), 8
                    ),
                    "calibration_error": round(
                        _number(source.get("calibration_error"), "calibration error"), 8
                    ),
                    "selective_risk": round(
                        _number(source.get("selective_risk"), "selective risk"), 8
                    ),
                    "coverage": round(_number(source.get("coverage"), "coverage"), 8),
                    "ood": source["ood"],
                    "evidence_grade": _string(source.get("evidence_grade"), "evidence grade"),
                    "is_largest_group": source["is_largest_group"],
                    "key_source": "pre_outcome_group_key",
                }
            )
            seen.add((dimension, group_id))
        if {row["dimension"] for row in rows} != set(cls.DIMENSIONS):
            raise OODWorkflowError("not all OOD dimensions are represented")
        if sum(row["is_largest_group"] for row in rows) != 1:
            raise OODWorkflowError("exactly one largest study group is required")
        return rows

    @classmethod
    def _sensitivity(cls, fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "scenario",
            "dimension",
            "excluded_group",
            "primary_metric",
            "calibration_error",
            "selective_risk",
            "evidence_grade_only",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["sensitivity_rows"]:
            source = _mapping(value, "OOD sensitivity row")
            if set(source) != required:
                raise OODWorkflowError("OOD sensitivity fields do not match schema")
            scenario = _string(source.get("scenario"), "OOD sensitivity scenario")
            if scenario in seen or scenario not in cls.SENSITIVITY:
                raise OODWorkflowError("OOD sensitivity scenario is invalid or duplicated")
            if not isinstance(source.get("evidence_grade_only"), bool):
                raise OODWorkflowError("OOD sensitivity evidence-grade flag is invalid")
            rows.append(
                {
                    "scenario": scenario,
                    "dimension": _string(source.get("dimension"), "sensitivity dimension"),
                    "excluded_group": _string(source.get("excluded_group"), "excluded group"),
                    "primary_metric": round(
                        _number(source.get("primary_metric"), "sensitivity metric"), 8
                    ),
                    "calibration_error": round(
                        _number(source.get("calibration_error"), "sensitivity calibration"), 8
                    ),
                    "selective_risk": round(
                        _number(source.get("selective_risk"), "sensitivity risk"), 8
                    ),
                    "evidence_grade_only": source["evidence_grade_only"],
                }
            )
            seen.add(scenario)
        if seen != set(cls.SENSITIVITY):
            raise OODWorkflowError("OOD sensitivity suite is incomplete")
        return rows

    def run(self, *, all_groups: bool = True) -> OODSummary:
        """Run leave-group, calibration, selective-risk, and sensitivity checks."""
        if not all_groups:
            raise OODWorkflowError("--all is required for OOD suite")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = _mapping(fixture_data["preregistration"], "OOD preregistration")
        rows = self._rows(fixture_data, preregistration)
        sensitivity = self._sensitivity(fixture_data)
        low_n = [row for row in rows if row["n"] < int(preregistration["minimum_group_n"])]
        largest = [row for row in rows if row["is_largest_group"]]
        claim_status = (
            "NARROWED_BY_OOD" if low_n or any(row["ood"] for row in rows) else "SUPPORTED"
        )
        low_n_ledger = [
            {
                "dimension": row["dimension"],
                "group_id": row["group_id"],
                "n": row["n"],
                "reason": "low_n_and_ood",
                "abstain": True,
            }
            for row in low_n
        ]
        fixture_text = self.fixture_path.read_text(encoding="utf-8").lower()
        prohibited = ["api_key", "credential", "private_key", "locked_payload", "secret"]
        found = [token for token in prohibited if token in fixture_text]
        lockbox = {
            "schema_version": 1,
            "status": "CLEAN" if not found else "BLOCKED",
            "prohibited_tokens": found,
            "target_values_exposed": False,
            "raw_download": False,
            "network_accessed": False,
        }
        raw_payloads: dict[str, Any] = {
            "group_keys": {
                "schema_version": 1,
                "dimensions": list(self.DIMENSIONS),
                "rows": rows,
                "outcome_independent": True,
            },
            "primary": {"schema_version": 1, "rows": rows, "claim_status": claim_status},
            "calibration": {
                "schema_version": 1,
                "rows": [
                    {
                        "dimension": r["dimension"],
                        "group_id": r["group_id"],
                        "calibration_error": r["calibration_error"],
                        "coverage": r["coverage"],
                    }
                    for r in rows
                ],
            },
            "selective": {
                "schema_version": 1,
                "rows": [
                    {
                        "dimension": r["dimension"],
                        "group_id": r["group_id"],
                        "selective_risk": r["selective_risk"],
                        "abstain": r["ood"],
                    }
                    for r in rows
                ],
            },
            "sensitivity": {
                "schema_version": 1,
                "rows": sensitivity,
                "leave_largest_study": largest[0]["group_id"],
            },
            "low_n": {"schema_version": 1, "rows": low_n_ledger, "count": len(low_n)},
            "claim_gate": {
                "schema_version": 1,
                "status": claim_status,
                "low_n_groups": len(low_n),
                "policy": "narrow_applicability_domain_and_abstain",
            },
            "failures": {
                "schema_version": 1,
                "status": "VALID" if not found else "INVALID",
                "failures": [],
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "group_keys": self.output_root / "group_key_audit.json",
            "primary": self.output_root / "primary_metrics.json",
            "calibration": self.output_root / "calibration_selective_risk.json",
            "sensitivity": self.output_root / "sensitivity_report.json",
            "low_n": self.output_root / "low_n_ledger.json",
            "claim_gate": self.output_root / "claim_gate.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        artifacts: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            payload = _canonical(raw_payloads[name])
            path.write_bytes(payload)
            artifacts[name] = {
                "path": (
                    str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path)
                ),
                "sha256": _sha256(payload),
                "bytes": len(payload),
            }
        lockbox_path = self.output_root / "lockbox_scan.json"
        lockbox_bytes = _canonical(lockbox)
        lockbox_path.write_bytes(lockbox_bytes)
        artifacts["lockbox"] = {
            "path": (
                str(lockbox_path.relative_to(self.root))
                if lockbox_path.is_relative_to(self.root)
                else str(lockbox_path)
            ),
            "sha256": _sha256(lockbox_bytes),
            "bytes": len(lockbox_bytes),
        }
        receipt_path = self.output_root / "ood_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "dimensions": len(self.DIMENSIONS),
            "groups": len(rows),
            "low_n_groups": len(low_n),
            "leave_largest": len(largest),
            "sensitivity_records": len(sensitivity),
            "primary_records": len(rows),
            "calibration_records": len(rows),
            "selective_risk_records": len(rows),
            "claim_status": claim_status,
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifacts,
        }
        receipt_bytes = _canonical(receipt)
        receipt_path.write_bytes(receipt_bytes)
        manifest = {
            "schema_version": 1,
            "workflow": "OOD_LEAVE_GROUP_AND_SENSITIVITY_SUITE",
            "status": receipt["status"],
            "resume_key": resume_key,
            "resume_supported": True,
            "target_values_exposed": False,
            "artifacts": {
                **artifacts,
                "receipt": {
                    "path": (
                        str(receipt_path.relative_to(self.root))
                        if receipt_path.is_relative_to(self.root)
                        else str(receipt_path)
                    ),
                    "sha256": _sha256(receipt_bytes),
                    "bytes": len(receipt_bytes),
                },
            },
        }
        (self.output_root / "ood_manifest.json").write_bytes(_canonical(manifest))
        return OODSummary(
            dimensions=len(self.DIMENSIONS),
            groups=len(rows),
            low_n_groups=len(low_n),
            leave_largest=len(largest),
            sensitivity_records=len(sensitivity),
            primary_records=len(rows),
            calibration_records=len(rows),
            selective_risk_records=len(rows),
            claim_status=claim_status,
            resumed=resumed,
            receipt_path=receipt_path,
        )
