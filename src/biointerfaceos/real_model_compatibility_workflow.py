"""Compatibility gate for the R2 real-model evaluation program.

This gate deliberately separates a real, study-held-out *source locator*
benchmark from a biological prediction target.  It may report an unavailable
model evaluation, but it must never fill that state with fixture predictions or
an inferred causal result.
"""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.real_benchmark_workflow import RealBenchmarkError, RealBenchmarkWorkflow


class RealModelCompatibilityError(RuntimeError):
    """Raised when the real-model compatibility gate cannot be audited safely."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealModelCompatibilityError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealModelCompatibilityError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RealModelCompatibilityError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class RealModelCompatibilitySummary:
    """Compact accounting for a source-compatibility audit."""

    source_count: int
    endpoint_count: int
    compatible_target_count: int
    receipt_path: Path


class RealModelCompatibilityWorkflow:
    """Audit whether a real scientific model can be executed without semantic leakage."""

    AUDIT_ID = "bioif-r2-real-model-compatibility-v1.1.0"
    EVALUATED_AT = "2026-08-12T00:00:00+00:00"
    BENCHMARK_OUTPUT_RELATIVE = "reports/review_round_2/real_benchmark/v1.1.0"
    OUTPUT_RELATIVE = "reports/review_round_2/real_model_compatibility/v1.1.0"
    MINIMUM_STUDIES = 3
    MINIMUM_LABORATORIES = 3

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
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
            raise RealModelCompatibilityError(f"cannot parse {label}") from exc

    def _admission(self) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            benchmark_receipt = RealBenchmarkWorkflow(self.root).verify()
        except (RealBenchmarkError, OSError) as exc:
            raise RealModelCompatibilityError(
                "the T122 real-source benchmark receipt is unavailable or invalid"
            ) from exc
        admission_path = self.root / self.BENCHMARK_OUTPUT_RELATIVE / "source_admission.json"
        admission = self._json(admission_path, "T122 source admission")
        if admission.get("schema_version") != 1:
            raise RealModelCompatibilityError("T122 source admission schema is invalid")
        if benchmark_receipt.get("source_admission_sha256") != _sha256(admission_path):
            raise RealModelCompatibilityError("T122 source admission checksum differs from receipt")
        if admission.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise RealModelCompatibilityError("T122 admission evidence class is unsafe")
        if admission.get("allowed_claim_level") != "EXPLORATORY":
            raise RealModelCompatibilityError("T122 admission claim level is unsafe")
        items = admission.get("items")
        if not isinstance(items, list) or len(items) < self.MINIMUM_STUDIES:
            raise RealModelCompatibilityError("T122 source admission has too few real items")
        return benchmark_receipt, admission

    def _endpoint_groups(self, items: list[Any]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for value in items:
            item = _mapping(value, "T122 source-admission item")
            endpoint_id = _string(item.get("endpoint_id"), "T122 endpoint ID")
            unit = _string(item.get("unit"), "T122 endpoint unit")
            for field in (
                "item_id",
                "source_id",
                "study_id",
                "laboratory",
                "biological_system",
                "protocol_id",
                "raw_asset",
                "raw_locator",
                "independent_unit_id",
            ):
                _string(item.get(field), f"T122 item {field}")
            if any(
                token in str(item[field]).lower()
                for field in ("item_id", "source_id", "raw_asset")
                for token in ("fixture", "synthetic", "mock")
            ):
                raise RealModelCompatibilityError("a fixture-like record crossed into T123")
            groups.setdefault((endpoint_id, unit), []).append(item)

        rows: list[dict[str, Any]] = []
        for (endpoint_id, unit), members in sorted(groups.items()):
            studies = sorted({_string(row["study_id"], "study ID") for row in members})
            laboratories = sorted({_string(row["laboratory"], "laboratory") for row in members})
            independent_units = sorted(
                {_string(row["independent_unit_id"], "independent unit") for row in members}
            )
            rows.append(
                {
                    "endpoint_id": endpoint_id,
                    "unit": unit,
                    "item_count": len(members),
                    "study_ids": studies,
                    "laboratories": laboratories,
                    "independent_unit_ids": independent_units,
                    "study_count": len(studies),
                    "laboratory_count": len(laboratories),
                    "effective_n": len(independent_units),
                    "qualifies_for_study_ood": (
                        len(studies) >= self.MINIMUM_STUDIES
                        and len(laboratories) >= self.MINIMUM_LABORATORIES
                        and len(independent_units) >= self.MINIMUM_STUDIES
                    ),
                }
            )
        return rows

    def run(self, *, strict: bool = False) -> RealModelCompatibilitySummary:
        """Write an immutable, strict compatibility decision for T123.

        A successful command means the *gate* was checked successfully.  It does
        not mean a model was fitted; a missing compatible target remains an
        explicit blocked state.
        """

        if not strict:
            raise RealModelCompatibilityError("T123 compatibility audit requires --strict")
        if self.output_root.exists():
            raise RealModelCompatibilityError("real-model compatibility audit already executed")

        benchmark_receipt, admission = self._admission()
        items_value = admission["items"]
        assert isinstance(items_value, list)
        endpoint_groups = self._endpoint_groups(items_value)
        compatible = [row for row in endpoint_groups if row["qualifies_for_study_ood"]]
        source_rows = [
            {
                "source_id": _string(item["source_id"], "source ID"),
                "study_id": _string(item["study_id"], "study ID"),
                "laboratory": _string(item["laboratory"], "laboratory"),
                "biological_system": _string(item["biological_system"], "biological system"),
                "protocol_id": _string(item["protocol_id"], "protocol ID"),
                "endpoint_id": _string(item["endpoint_id"], "endpoint ID"),
                "unit": _string(item["unit"], "unit"),
                "effective_n_contribution": 1,
            }
            for item in items_value
        ]
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": self.EVALUATED_AT,
            "input_benchmark_receipt_sha256": _sha256(
                self.root / self.BENCHMARK_OUTPUT_RELATIVE / "benchmark_receipt.json"
            ),
            "input_source_admission_sha256": _sha256(
                self.root / self.BENCHMARK_OUTPUT_RELATIVE / "source_admission.json"
            ),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "source_rows": source_rows,
            "endpoint_groups": endpoint_groups,
            "compatible_targets": compatible,
            "minimum_requirements": {
                "study_count": self.MINIMUM_STUDIES,
                "laboratory_count": self.MINIMUM_LABORATORIES,
                "effective_n": self.MINIMUM_STUDIES,
                "identical_endpoint_and_unit": True,
                "paired_configurations": True,
                "declared_external_ood_cohort": True,
                "negative_controls": True,
            },
            "status": (
                "READY_FOR_FROZEN_REAL_MODEL_EVALUATION"
                if compatible
                else "BLOCKED_NO_COMPATIBLE_CROSS_STUDY_TARGET"
            ),
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "claim_boundary": (
                "No biological, causal, module-effect, robustness, or generalisation claim is "
                "supported by this audit. A source-locator benchmark is not a model target."
            ),
            "next_required_evidence": (
                "Admit at least three independently generated, row-level datasets with the same "
                "endpoint and unit; freeze paired configurations, seeds, a declared external OOD "
                "cohort and negative controls before fitting any model."
            ),
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "compatibility_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": self.EVALUATED_AT,
            "status": decision["status"],
            "compatibility_decision_sha256": _sha256(decision_path),
            "source_count": len({row["source_id"] for row in source_rows}),
            "endpoint_count": len(endpoint_groups),
            "compatible_target_count": len(compatible),
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "compatibility_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return RealModelCompatibilitySummary(
            source_count=_integer(receipt["source_count"], "source count", minimum=1),
            endpoint_count=_integer(receipt["endpoint_count"], "endpoint count", minimum=1),
            compatible_target_count=_integer(
                receipt["compatible_target_count"], "compatible target count"
            ),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify that an immutable T123 compatibility result remains intact."""

        decision_path = self.output_root / "compatibility_decision.json"
        receipt_path = self.output_root / "compatibility_receipt.json"
        decision = self._json(decision_path, "real-model compatibility decision")
        receipt = self._json(receipt_path, "real-model compatibility receipt")
        required_false = (
            "model_fitted",
            "paired_ablations_run",
            "external_ood_evaluated",
            "negative_controls_run",
            "independent_validation",
            "scientific_submission_ready",
        )
        if (
            receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != "BLOCKED_NO_COMPATIBLE_CROSS_STUDY_TARGET"
            or receipt.get("compatibility_decision_sha256") != _sha256(decision_path)
            or decision.get("status") != receipt["status"]
            or decision.get("compatible_targets") != []
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false[:4])
        ):
            raise RealModelCompatibilityError("real-model compatibility receipt is invalid")
        return receipt
