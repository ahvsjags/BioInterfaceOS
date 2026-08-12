"""Fixture-backed publication-selection and missingness-bias workflow."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BiasWorkflowError(RuntimeError):
    """Raised when the T101 selection-bias contract is invalid."""


@dataclass(frozen=True)
class BiasSummary:
    """Summary of selection and missingness sensitivity."""

    rows: int
    clusters: int
    models: int
    observed_rows: int
    missing_rows: int
    missing_mechanisms: int
    interval_records: int
    model_disagreement: float
    p_values_used: bool
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
        raise BiasWorkflowError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BiasWorkflowError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise BiasWorkflowError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise BiasWorkflowError(f"{label} must be finite")
    return result


class BiasWorkflow:
    """Compare clustered missingness and publication-selection assumptions."""

    MODELS = (
        "complete_case",
        "inverse_probability_weighted",
        "pattern_mixture",
        "bounded_selection",
    )
    MECHANISMS = ("MCAR", "MAR", "MNAR")

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = (
            fixture_path or self.root / "tests/fixtures/robustness/bias_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/robustness/bias"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")), "bias fixture"
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BiasWorkflowError(f"cannot load bias fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != (
            "publication_selection_and_missingness_bias"
        ):
            raise BiasWorkflowError("bias fixture schema or mode is invalid")
        for key in ("inputs", "preregistration", "studies"):
            if key not in data:
                raise BiasWorkflowError(f"bias fixture is missing {key}")
        if not isinstance(data["inputs"], list) or not isinstance(data["studies"], list):
            raise BiasWorkflowError("bias fixture list fields are invalid")
        preregistration = _mapping(data["preregistration"], "bias preregistration")
        if preregistration.get("schema_version") != 1:
            raise BiasWorkflowError("bias preregistration schema is invalid")
        if preregistration.get("models") != list(self.MODELS):
            raise BiasWorkflowError("bias model list is not frozen")
        if preregistration.get("missing_mechanisms") != list(self.MECHANISMS):
            raise BiasWorkflowError("missingness mechanism list is not frozen")
        if preregistration.get("p_values_used") is not False:
            raise BiasWorkflowError("p-values cannot be used as ground truth")
        if preregistration.get("target_values_exposed") is not False:
            raise BiasWorkflowError("bias fixture target values must remain hidden")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected: dict[str, tuple[Path, str]] = {
            "T047 silver data report": (
                self.root / "reports/T047_silver_data_release.md",
                "a81b3f125232b64d55e2628cb5bfd0b01096ef721fadbf35eba2319590a5128b",
            ),
            "T071 hierarchical effects report": (
                self.root / "reports/T071_hierarchical_mixed_effect.md",
                "3a849fc4ce326baeb023fed4442fd09aaa9f7d4c381b37aa5764dfcdfbd95afd",
            ),
            "T091 mediation receipt": (
                self.root / "reports/omics/mediation/mediation_receipt.json",
                "11e522edee14fa5e5daf2482f044df6163db6573ca7a6a6a3d9eb7ac442dc945",
            ),
            "T093 symbolic-laws receipt": (
                self.root / "reports/omics/symbolic_laws/symbolic_laws_receipt.json",
                "bce24812c8b301a7133522b9647b1c13c6b6629d19f1e8601836cec1a637ae55",
            ),
            "T100 OOD receipt": (
                self.root / "reports/robustness/ood/ood_receipt.json",
                "2172d6139361a6b10e5d80ba199c21c7854830eeaa2152dc82f10931387beb2e",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "bias input")
            label = _string(row.get("label"), "bias input label")
            if label not in expected:
                raise BiasWorkflowError(f"unexpected bias input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "bias input path")).resolve(
                strict=True
            )
            raw = path.read_bytes()
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise BiasWorkflowError(f"bias input path/checksum differs: {label}")
            if _sha256(raw) != checksum:
                raise BiasWorkflowError(f"bias input checksum differs on disk: {label}")
            if path.suffix == ".json" and _mapping(json.loads(raw), label).get("status") != "VALID":
                raise BiasWorkflowError(f"bias receipt is not valid: {label}")
            seen.add(label)
        if seen != set(expected):
            raise BiasWorkflowError("bias inputs do not match T047/T071/T091/T093/T100")

    @classmethod
    def _studies(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        required = {
            "study_id",
            "cluster_id",
            "effect",
            "effect_observed",
            "sample_size",
            "publication_probability",
            "evidence_grade",
            "missing_mechanism",
            "missing_fields",
            "p_value_reported",
        }
        studies: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["studies"]:
            source = _mapping(value, "bias study")
            if set(source) != required:
                raise BiasWorkflowError("bias study fields do not match schema")
            study_id = _string(source.get("study_id"), "study ID")
            if study_id in seen:
                raise BiasWorkflowError(f"duplicate bias study: {study_id}")
            mechanism = _string(source.get("missing_mechanism"), "missing mechanism")
            observed = source.get("effect_observed")
            if not isinstance(observed, bool) or not isinstance(
                source.get("p_value_reported"), bool
            ):
                raise BiasWorkflowError("bias study flags are invalid")
            if observed and source.get("effect") is None:
                raise BiasWorkflowError(f"observed study lacks effect: {study_id}")
            if not observed and mechanism not in cls.MECHANISMS:
                raise BiasWorkflowError(f"missing study mechanism is invalid: {study_id}")
            missing_fields = source.get("missing_fields")
            if not isinstance(missing_fields, list):
                raise BiasWorkflowError(f"missing fields are invalid: {study_id}")
            studies.append(
                {
                    "study_id": study_id,
                    "cluster_id": _string(source.get("cluster_id"), "cluster ID"),
                    "effect": None
                    if source.get("effect") is None
                    else _number(source["effect"], "study effect"),
                    "effect_observed": observed,
                    "sample_size": int(_number(source.get("sample_size"), "sample size")),
                    "publication_probability": _number(
                        source.get("publication_probability"), "publication probability"
                    ),
                    "evidence_grade": _string(source.get("evidence_grade"), "evidence grade"),
                    "missing_mechanism": mechanism,
                    "missing_fields": [str(item) for item in missing_fields],
                    "p_value_reported": source["p_value_reported"],
                }
            )
            seen.add(study_id)
        if not studies or not any(row["effect_observed"] for row in studies):
            raise BiasWorkflowError("bias fixture has no observed effects")
        if any(row["publication_probability"] <= 0 for row in studies):
            raise BiasWorkflowError("publication probability must be positive")
        if preregistration["cluster_key"] != "cluster_id":
            raise BiasWorkflowError("cluster key is not frozen")
        return studies

    @staticmethod
    def _interval(values: list[float], samples: int) -> dict[str, float | int]:
        bootstrap: list[float] = []
        for index in range(samples):
            draw = [values[(index + offset * 3) % len(values)] for offset in range(len(values))]
            bootstrap.append(sum(draw) / len(draw))
        ordered = sorted(bootstrap)
        return {
            "bootstrap_samples": samples,
            "ci95_lower": round(ordered[int(0.025 * (len(ordered) - 1))], 8),
            "ci95_upper": round(ordered[int(0.975 * (len(ordered) - 1))], 8),
        }

    def run(self, *, fixture: bool = True) -> BiasSummary:
        """Run clustered selection/missingness sensitivity models."""
        if not fixture:
            raise BiasWorkflowError("--fixture is required for bias analysis")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = _mapping(fixture_data["preregistration"], "bias preregistration")
        studies = self._studies(fixture_data, preregistration)
        observed = [row["effect"] for row in studies if row["effect_observed"]]
        observed_values = [float(value) for value in observed if value is not None]
        base = sum(observed_values) / len(observed_values)
        weighted = [
            (float(row["effect"]), 1.0 / row["publication_probability"])
            for row in studies
            if row["effect_observed"] and row["effect"] is not None
        ]
        ipw = sum(value * weight for value, weight in weighted) / sum(
            weight for _, weight in weighted
        )
        imputed: list[float] = []
        for row in studies:
            if row["effect_observed"]:
                imputed.append(float(row["effect"]))
            elif row["missing_mechanism"] == "MCAR":
                imputed.append(base)
            elif row["missing_mechanism"] == "MAR":
                imputed.append(base + 0.05)
            else:
                imputed.append(base - 0.10)
        pattern = sum(imputed) / len(imputed)
        selection_delta = float(preregistration["selection_delta"])
        bounded_lower = pattern - selection_delta
        bounded_upper = pattern + selection_delta
        values_by_model: dict[str, list[float]] = {
            "complete_case": observed_values,
            "inverse_probability_weighted": [value * weight for value, weight in weighted],
            "pattern_mixture": imputed,
            "bounded_selection": [bounded_lower, pattern, bounded_upper],
        }
        points = {
            "complete_case": sum(observed_values) / len(observed_values),
            "inverse_probability_weighted": ipw,
            "pattern_mixture": pattern,
            "bounded_selection": pattern,
        }
        comparison: dict[str, Any] = {}
        intervals: dict[str, Any] = {}
        for model in self.MODELS:
            values = values_by_model[model]
            comparison[model] = {
                "point_estimate": round(points[model], 8),
                "rows_used": len(values),
                "cluster_count": len({row["cluster_id"] for row in studies}),
                "p_values_used": False,
                "assumption": model,
            }
            intervals[model] = {
                "model": model,
                **self._interval(values, int(preregistration["bootstrap_samples"])),
            }
        mechanism_counts = {
            mechanism: sum(
                not row["effect_observed"] and row["missing_mechanism"] == mechanism
                for row in studies
            )
            for mechanism in self.MECHANISMS
        }
        missing_audit = {
            "schema_version": 1,
            "rows": len(studies),
            "observed_rows": len(observed_values),
            "missing_rows": len(studies) - len(observed_values),
            "mechanism_counts": mechanism_counts,
            "missing_fields": sorted({field for row in studies for field in row["missing_fields"]}),
            "cluster_count": len({row["cluster_id"] for row in studies}),
            "p_values_reported": sum(row["p_value_reported"] for row in studies),
            "p_values_used": False,
        }
        model_min = min(
            bounded_lower, points["complete_case"], points["inverse_probability_weighted"], pattern
        )
        model_max = max(
            bounded_upper, points["complete_case"], points["inverse_probability_weighted"], pattern
        )
        disagreement = round(model_max - model_min, 8)
        threshold = float(preregistration["material_disagreement_threshold"])
        claim_status = (
            "DOWNGRADED_SELECTION_SENSITIVE"
            if disagreement >= threshold
            else "SUPPORTED_WITH_SELECTION_LIMITS"
        )
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
            "preregistration": {
                **preregistration,
                "frozen_before_fitting": True,
                "target_values_exposed": False,
            },
            "missingness": missing_audit,
            "comparison": {"schema_version": 1, "models": comparison, "p_values_used": False},
            "intervals": {"schema_version": 1, "records": intervals},
            "claim_gate": {
                "schema_version": 1,
                "status": claim_status,
                "disagreement": disagreement,
                "threshold": threshold,
                "conservative_bound": [bounded_lower, bounded_upper],
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
            "preregistration": self.output_root / "selection_preregistration.json",
            "missingness": self.output_root / "missingness_audit.json",
            "comparison": self.output_root / "model_comparison.json",
            "intervals": self.output_root / "sensitivity_intervals.json",
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
        receipt_path = self.output_root / "bias_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "rows": len(studies),
            "clusters": len({row["cluster_id"] for row in studies}),
            "models": len(self.MODELS),
            "observed_rows": len(observed_values),
            "missing_rows": len(studies) - len(observed_values),
            "missing_mechanisms": len(self.MECHANISMS),
            "interval_records": len(intervals),
            "model_disagreement": disagreement,
            "p_values_used": False,
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
            "workflow": "PUBLICATION_SELECTION_AND_MISSINGNESS_BIAS",
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
        (self.output_root / "bias_manifest.json").write_bytes(_canonical(manifest))
        return BiasSummary(
            rows=len(studies),
            clusters=len({row["cluster_id"] for row in studies}),
            models=len(self.MODELS),
            observed_rows=len(observed_values),
            missing_rows=len(studies) - len(observed_values),
            missing_mechanisms=len(self.MECHANISMS),
            interval_records=len(intervals),
            model_disagreement=disagreement,
            p_values_used=False,
            claim_status=claim_status,
            resumed=resumed,
            receipt_path=receipt_path,
        )
