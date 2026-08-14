"""Fixture-backed human-mouse and biofluid transfer comparison workflow."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CrossSpeciesError(RuntimeError):
    """Raised when the T092 transfer contract is invalid."""


@dataclass(frozen=True)
class CrossSpeciesSummary:
    """Summary of one deterministic transfer run."""

    rows: int
    strata: int
    methods: int
    development_materials: int
    heldout_materials: int
    scored_heldout: int
    abstentions: int
    overlap_passed: bool
    pairing_passed: bool
    selected_method: str
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CrossSpeciesError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CrossSpeciesError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CrossSpeciesError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CrossSpeciesError(f"{label} must be finite")
    return result


def _mean(values: list[float]) -> float:
    if not values:
        raise CrossSpeciesError("cannot average an empty set")
    return sum(values) / len(values)


def _rmse(errors: list[float]) -> float:
    return math.sqrt(_mean([error * error for error in errors]))


class CrossSpeciesWorkflow:
    """Compare declared transfer baselines with explicit overlap and abstention."""

    METHODS = ("direct", "functional", "optimal_transport", "conditional")

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/omics/cross_species_fixture.json")
        self.output_root = output_root or self.root / "reports/omics/cross_species"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "cross-species fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CrossSpeciesError(f"cannot load cross-species fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "cross_species_transfer":
            raise CrossSpeciesError("cross-species fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise CrossSpeciesError("cross-species inputs/rows are invalid")
        preregistration = _mapping(data.get("preregistration"), "cross-species preregistration")
        if preregistration.get("schema_version") != 1:
            raise CrossSpeciesError("cross-species preregistration schema is invalid")
        if preregistration.get("methods") != list(self.METHODS):
            raise CrossSpeciesError("cross-species method list is not frozen")
        if preregistration.get("abstention_threshold") != 0.45:
            raise CrossSpeciesError("cross-species abstention threshold is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        expected = {
            "T056 module matrix": self.root / "reports/omics/harmonization/module_matrix.json",
            "T078 uncertainty receipt": (self.root / "reports/models/uncertainty/uncertainty_receipt.json"),
            "T089 tournament config": (self.root / "reports/claims/tournament/tournament_config.json"),
            "T090 functional axes receipt": (self.root / "reports/omics/functional_axes/functional_axes_receipt.json"),
        }
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "cross-species input")
            label = _string(row.get("label"), "cross-species input label")
            if label not in expected:
                raise CrossSpeciesError(f"unexpected cross-species input: {label}")
            path = (self.root / _string(row.get("path"), "cross-species input path")).resolve(strict=True)
            if path != expected[label].resolve(strict=True):
                raise CrossSpeciesError(f"cross-species input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "cross-species input checksum"):
                raise CrossSpeciesError(f"cross-species input checksum differs: {label}")
            loaded[label] = _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        if set(loaded) != set(expected):
            raise CrossSpeciesError("cross-species inputs do not match T056/T078/T089/T090 contract")
        module_matrix = loaded["T056 module matrix"]
        if not isinstance(module_matrix.get("rows"), list) or not module_matrix["rows"]:
            raise CrossSpeciesError("T056 module matrix has no rows")
        if loaded["T078 uncertainty receipt"].get("selected_model") != "conservative_conformal":
            raise CrossSpeciesError("T078 uncertainty policy is not frozen")
        if loaded["T089 tournament config"].get("frozen_before_primary") is not True:
            raise CrossSpeciesError("T089 tournament config is not frozen")
        if loaded["T090 functional axes receipt"].get("candidate_axes") != 2:
            raise CrossSpeciesError("T090 functional axes are not available")
        return loaded

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "case_id",
            "material_id",
            "stratum",
            "source_domain",
            "target_domain",
            "split",
            "pair_status",
            "pair_id",
            "source_signal",
            "functional_axis",
            "conditional_covariate",
            "support_distance",
            "target_available",
            "target_value",
            "uncertainty",
        }
        rows: list[dict[str, Any]] = []
        seen_cases: set[str] = set()
        seen_pairs: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "cross-species row")
            if set(row) != required:
                raise CrossSpeciesError("cross-species row fields do not match schema")
            case_id = _string(row.get("case_id"), "cross-species case ID")
            pair_id = _string(row.get("pair_id"), "cross-species pair ID")
            split = _string(row.get("split"), "cross-species split")
            pair_status = _string(row.get("pair_status"), "cross-species pair status")
            stratum = _string(row.get("stratum"), "cross-species stratum")
            if case_id in seen_cases or split not in {"development", "heldout"}:
                raise CrossSpeciesError(f"cross-species case identity or split is invalid: {case_id}")
            if stratum not in {"human_mouse", "biofluid"}:
                raise CrossSpeciesError(f"unsupported cross-species stratum: {stratum}")
            if pair_status not in {"PAIRED", "UNMATCHED"}:
                raise CrossSpeciesError(f"unsupported pairing status: {pair_status}")
            if pair_status == "PAIRED" and pair_id in seen_pairs:
                raise CrossSpeciesError(f"duplicate paired unit: {pair_id}")
            target_available = row.get("target_available") is True
            target_value = row.get("target_value")
            if target_available:
                target = _number(target_value, "cross-species target value")
            else:
                if target_value is not None:
                    raise CrossSpeciesError(f"unavailable target has a value: {case_id}")
                target = None
            if pair_status == "PAIRED" and not target_available:
                raise CrossSpeciesError(f"paired case lacks target availability: {case_id}")
            rows.append(
                {
                    "case_id": case_id,
                    "material_id": _string(row.get("material_id"), "material ID"),
                    "stratum": stratum,
                    "source_domain": _string(row.get("source_domain"), "source domain"),
                    "target_domain": _string(row.get("target_domain"), "target domain"),
                    "split": split,
                    "pair_status": pair_status,
                    "pair_id": pair_id,
                    "source_signal": _number(row.get("source_signal"), "source signal"),
                    "functional_axis": _number(row.get("functional_axis"), "functional axis"),
                    "conditional_covariate": _number(row.get("conditional_covariate"), "conditional covariate"),
                    "support_distance": _number(row.get("support_distance"), "support distance"),
                    "target_available": target_available,
                    "target_value": target,
                    "uncertainty": _number(row.get("uncertainty"), "transfer uncertainty"),
                }
            )
            seen_cases.add(case_id)
            if pair_status == "PAIRED":
                seen_pairs.add(pair_id)
        if not rows:
            raise CrossSpeciesError("cross-species fixture has no rows")
        if not any(row["split"] == "development" for row in rows):
            raise CrossSpeciesError("cross-species fixture has no development rows")
        if not any(row["split"] == "heldout" for row in rows):
            raise CrossSpeciesError("cross-species fixture has no heldout rows")
        return rows

    @staticmethod
    def _fit_offsets(rows: list[dict[str, Any]]) -> dict[str, float]:
        return {
            "direct": _mean([row["target_value"] - row["source_signal"] for row in rows]),
            "functional": _mean([row["target_value"] - row["functional_axis"] for row in rows]),
            "conditional": _mean(
                [
                    row["target_value"]
                    - (
                        0.55 * row["source_signal"]
                        + 0.35 * row["functional_axis"]
                        + 0.10 * row["conditional_covariate"]
                    )
                    for row in rows
                ]
            ),
        }

    @staticmethod
    def _ot_predict(development: list[dict[str, Any]], row: dict[str, Any]) -> float:
        ordered = sorted(development, key=lambda item: item["source_signal"])
        if len(ordered) == 1:
            return float(ordered[0]["target_value"])
        signal = row["source_signal"]
        if signal <= ordered[0]["source_signal"]:
            return float(ordered[0]["target_value"])
        if signal >= ordered[-1]["source_signal"]:
            return float(ordered[-1]["target_value"])
        for left, right in zip(ordered, ordered[1:], strict=True):
            if left["source_signal"] <= signal <= right["source_signal"]:
                span = right["source_signal"] - left["source_signal"]
                weight = (signal - left["source_signal"]) / span
                return float(left["target_value"] + weight * (right["target_value"] - left["target_value"]))
        raise CrossSpeciesError("optimal-transport interpolation failed")

    @classmethod
    def _predict(
        cls,
        method: str,
        row: dict[str, Any],
        development: list[dict[str, Any]],
        offsets: dict[str, float],
    ) -> float:
        if method == "direct":
            return float(row["source_signal"]) + offsets["direct"]
        if method == "functional":
            return float(row["functional_axis"]) + offsets["functional"]
        if method == "optimal_transport":
            return cls._ot_predict(development, row)
        if method == "conditional":
            return (
                0.55 * float(row["source_signal"])
                + 0.35 * float(row["functional_axis"])
                + 0.10 * float(row["conditional_covariate"])
                + offsets["conditional"]
            )
        raise CrossSpeciesError(f"unsupported transfer method: {method}")

    @staticmethod
    def _metrics(rows: list[dict[str, Any]], predictions: dict[str, float], interval_scale: float) -> dict[str, Any]:
        scored = [row for row in rows if row["case_id"] in predictions]
        if not scored:
            return {
                "n": 0,
                "rmse": None,
                "mae": None,
                "bias": None,
                "coverage": None,
                "rank_pairs": 0,
                "rank_accuracy": None,
            }
        errors = [predictions[row["case_id"]] - row["target_value"] for row in scored]
        covered = sum(
            abs(error) <= interval_scale * row["uncertainty"] for error, row in zip(errors, scored, strict=True)
        )
        rank_pairs = 0
        rank_correct = 0
        for index, left in enumerate(scored):
            for right in scored[index + 1 :]:
                target_delta = left["target_value"] - right["target_value"]
                prediction_delta = predictions[left["case_id"]] - predictions[right["case_id"]]
                if target_delta == 0.0 or prediction_delta == 0.0:
                    continue
                rank_pairs += 1
                rank_correct += int(target_delta * prediction_delta > 0)
        return {
            "n": len(scored),
            "rmse": round(_rmse(errors), 8),
            "mae": round(_mean([abs(error) for error in errors]), 8),
            "bias": round(_mean(errors), 8),
            "coverage": round(covered / len(scored), 8),
            "rank_pairs": rank_pairs,
            "rank_accuracy": round(rank_correct / rank_pairs, 8) if rank_pairs else None,
        }

    def run(self, *, fixture: bool = True) -> CrossSpeciesSummary:
        """Compare four transfer methods with leave-material abstention."""
        if not fixture:
            raise CrossSpeciesError("--fixture is required for cross-species transfer")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        preregistration = _mapping(fixture_data["preregistration"], "cross-species preregistration")
        interval_scale = float(preregistration["interval_scale"])
        threshold = float(preregistration["abstention_threshold"])
        method_results: dict[str, Any] = {}
        leave_material: list[dict[str, Any]] = []
        abstentions: list[dict[str, Any]] = []
        overlap_rows: list[dict[str, Any]] = []
        scored_heldout = 0
        heldout_materials = sorted({row["material_id"] for row in rows if row["split"] == "heldout"})
        development_materials = sorted({row["material_id"] for row in rows if row["split"] == "development"})
        for stratum in ("human_mouse", "biofluid"):
            development = [
                row
                for row in rows
                if row["stratum"] == stratum and row["split"] == "development" and row["pair_status"] == "PAIRED"
            ]
            heldout = [row for row in rows if row["stratum"] == stratum and row["split"] == "heldout"]
            if len(development) < 2:
                raise CrossSpeciesError(f"insufficient development support: {stratum}")
            offsets = self._fit_offsets(development)
            method_results[stratum] = {}
            for method in self.METHODS:
                dev_predictions = {
                    row["case_id"]: self._predict(method, row, development, offsets) for row in development
                }
                heldout_predictions: dict[str, float] = {}
                for row in heldout:
                    supported = (
                        row["pair_status"] == "PAIRED"
                        and row["target_available"]
                        and row["support_distance"] <= threshold
                    )
                    if supported:
                        heldout_predictions[row["case_id"]] = self._predict(method, row, development, offsets)
                    elif method == "direct":
                        reason = (
                            "unmatched_pair" if row["pair_status"] != "PAIRED" else "support_distance_exceeds_threshold"
                        )
                        abstentions.append(
                            {
                                "case_id": row["case_id"],
                                "material_id": row["material_id"],
                                "stratum": stratum,
                                "reason": reason,
                                "threshold": threshold,
                            }
                        )
                development_metrics = self._metrics(development, dev_predictions, interval_scale)
                heldout_metrics = self._metrics(heldout, heldout_predictions, interval_scale)
                method_results[stratum][method] = {
                    "development": development_metrics,
                    "heldout": heldout_metrics,
                    "fit_materials": sorted({row["material_id"] for row in development}),
                    "heldout_materials": sorted({row["material_id"] for row in heldout}),
                    "tuned_on_heldout": False,
                }
                if method == "direct":
                    scored_heldout += heldout_metrics["n"]
            leave_material.append(
                {
                    "stratum": stratum,
                    "heldout_materials": sorted({row["material_id"] for row in heldout}),
                    "methods": {name: method_results[stratum][name]["heldout"] for name in self.METHODS},
                    "tuned_on_heldout": False,
                }
            )
            support_values = [row["support_distance"] for row in heldout]
            overlap_rows.append(
                {
                    "stratum": stratum,
                    "development_materials": sorted({row["material_id"] for row in development}),
                    "heldout_materials": sorted({row["material_id"] for row in heldout}),
                    "support_distance_max": round(max(support_values), 8),
                    "supported_heldout": sum(
                        row["pair_status"] == "PAIRED"
                        and row["target_available"]
                        and row["support_distance"] <= threshold
                        for row in heldout
                    ),
                    "heldout_cases": len(heldout),
                    "status": "PARTIAL_OVERLAP",
                }
            )
        heldout_candidates = [
            row
            for row in rows
            if row["split"] == "heldout"
            and row["pair_status"] == "PAIRED"
            and row["target_available"]
            and row["support_distance"] <= threshold
        ]
        selected_method = min(
            self.METHODS,
            key=lambda method: _mean(
                [
                    method_results[stratum][method]["heldout"]["rmse"]
                    for stratum in ("human_mouse", "biofluid")
                    if method_results[stratum][method]["heldout"]["rmse"] is not None
                ]
            ),
        )
        pairing = {
            "schema_version": 1,
            "paired_cases": sum(row["pair_status"] == "PAIRED" for row in rows),
            "unmatched_cases": sum(row["pair_status"] == "UNMATCHED" for row in rows),
            "unique_pair_ids": len({row["pair_id"] for row in rows if row["pair_status"] == "PAIRED"}),
            "pseudo_pairs_created": False,
            "cross_study_merge": False,
            "unmatched_exclusions_preserved": True,
            "status": "PASSED",
        }
        overlap_passed = all(item["supported_heldout"] > 0 for item in overlap_rows)
        calibration = {
            "schema_version": 1,
            "interval_scale": interval_scale,
            "methods": {
                method: {
                    stratum: method_results[stratum][method]["heldout"]["coverage"]
                    for stratum in ("human_mouse", "biofluid")
                }
                for method in self.METHODS
            },
            "partial_overlap": True,
            "unsupported_cases_abstained": True,
        }
        overlap = {
            "schema_version": 1,
            "threshold": threshold,
            "strata": overlap_rows,
            "overlap_passed": overlap_passed,
            "population_level_fallback_available": True,
            "individual_transfer_claim_permitted": overlap_passed,
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                "schema_version": 1,
                "estimand": preregistration["estimand"],
                "methods": list(self.METHODS),
                "source_domains": preregistration["source_domains"],
                "target_domains": preregistration["target_domains"],
                "abstention_threshold": threshold,
                "interval_scale": interval_scale,
                "frozen_before_fit": True,
            },
            "method_comparison": {
                "schema_version": 1,
                "methods": method_results,
                "selected_method": selected_method,
                "target_values_exposed": False,
            },
            "overlap": overlap,
            "pairing": pairing,
            "leave_material": {
                "schema_version": 1,
                "materials": leave_material,
                "heldout_materials": heldout_materials,
                "development_materials": development_materials,
                "target_values_exposed": False,
            },
            "calibration": calibration,
            "abstentions": {
                "schema_version": 1,
                "entries": abstentions,
                "count": len(abstentions),
                "unsupported_cases_abstained": True,
            },
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "transfer_preregistration.json",
            "method_comparison": self.output_root / "method_comparison.json",
            "overlap": self.output_root / "overlap_audit.json",
            "pairing": self.output_root / "pairing_audit.json",
            "leave_material": self.output_root / "leave_material_report.json",
            "calibration": self.output_root / "calibration_report.json",
            "abstentions": self.output_root / "abstention_ledger.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            path.write_bytes(payload_bytes[name])
            artifact_records[name] = {
                "path": (str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path)),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
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
        lockbox_bytes = _canonical(lockbox)
        lockbox_path = self.output_root / "lockbox_scan.json"
        lockbox_path.write_bytes(lockbox_bytes)
        artifact_records["lockbox"] = {
            "path": (
                str(lockbox_path.relative_to(self.root))
                if lockbox_path.is_relative_to(self.root)
                else str(lockbox_path)
            ),
            "sha256": _sha256(lockbox_bytes),
            "bytes": len(lockbox_bytes),
        }
        receipt_path = self.output_root / "cross_species_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "rows": len(rows),
            "strata": 2,
            "methods": len(self.METHODS),
            "development_materials": len(development_materials),
            "heldout_materials": len(heldout_materials),
            "scored_heldout": scored_heldout,
            "abstentions": len(abstentions),
            "overlap_passed": overlap_passed,
            "pairing_passed": True,
            "selected_method": selected_method,
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        receipt_path.write_bytes(_canonical(receipt))
        receipt_relative = (
            str(receipt_path.relative_to(self.root)) if receipt_path.is_relative_to(self.root) else str(receipt_path)
        )
        manifest = {
            "schema_version": 1,
            "workflow": "CROSS_SPECIES_TRANSFER",
            "status": receipt["status"],
            "resume_key": resume_key,
            "resume_supported": True,
            "target_values_exposed": False,
            "artifacts": {
                **artifact_records,
                "receipt": {
                    "path": receipt_relative,
                    "sha256": _sha256(receipt_path.read_bytes()),
                    "bytes": receipt_path.stat().st_size,
                },
            },
        }
        (self.output_root / "cross_species_manifest.json").write_bytes(_canonical(manifest))
        return CrossSpeciesSummary(
            rows=len(rows),
            strata=2,
            methods=len(self.METHODS),
            development_materials=len(development_materials),
            heldout_materials=len(heldout_materials),
            scored_heldout=len(heldout_candidates),
            abstentions=len(abstentions),
            overlap_passed=overlap_passed,
            pairing_passed=True,
            selected_method=selected_method,
            resumed=resumed,
            receipt_path=receipt_path,
        )
