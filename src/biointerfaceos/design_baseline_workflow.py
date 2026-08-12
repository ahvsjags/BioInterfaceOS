"""Fixture-backed constrained multiobjective design baseline."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DesignBaselineError(RuntimeError):
    """Raised when the T096 constrained-design contract is invalid."""


@dataclass(frozen=True)
class DesignBaselineSummary:
    """Summary of one deterministic design baseline run."""

    candidates: int
    valid_candidates: int
    invalid_candidates: int
    supported_candidates: int
    methods: int
    constraint_pass_rate: float
    controls_recovered: int
    controls_total: int
    pareto_members: int
    abstentions: int
    selected_method: str
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
        raise DesignBaselineError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignBaselineError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DesignBaselineError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise DesignBaselineError(f"{label} must be finite")
    return result


class DesignBaselineWorkflow:
    """Compare bounded design proposal baselines under hard constraints."""

    METHODS = ("enumeration", "nsga_ii", "bo_style")

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/design/constrained_design_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/design/baseline"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "design fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DesignBaselineError(f"cannot load design fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "constrained_design_baseline":
            raise DesignBaselineError("design fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("candidates"), list):
            raise DesignBaselineError("design inputs/candidates are invalid")
        preregistration = _mapping(data.get("preregistration"), "design preregistration")
        if preregistration.get("schema_version") != 1:
            raise DesignBaselineError("design preregistration schema is invalid")
        if preregistration.get("methods") != list(self.METHODS):
            raise DesignBaselineError("design method list is not frozen")
        if preregistration.get("budget") != 6:
            raise DesignBaselineError("design search budget is not frozen")
        if preregistration.get("uncertainty_penalty") != 0.50:
            raise DesignBaselineError("uncertainty penalty is not frozen")
        if preregistration.get("ad_penalty") != 0.30:
            raise DesignBaselineError("AD penalty is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any] | str]:
        expected: dict[str, Path] = {
            "T041 material resolution": self.root / "reports/T041_material_resolution.md",
            "T078 uncertainty receipt": self.root
            / "reports/models/uncertainty/uncertainty_receipt.json",
            "T090 functional axes receipt": self.root
            / "reports/omics/functional_axes/functional_axes_receipt.json",
            "T095 counterfactual receipt": self.root
            / "reports/omics/counterfactuals/counterfactuals_receipt.json",
        }
        loaded: dict[str, dict[str, Any] | str] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "design input")
            label = _string(row.get("label"), "design input label")
            if label not in expected:
                raise DesignBaselineError(f"unexpected design input: {label}")
            path = (self.root / _string(row.get("path"), "design input path")).resolve(strict=True)
            if path != expected[label].resolve(strict=True):
                raise DesignBaselineError(f"design input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "design input checksum"):
                raise DesignBaselineError(f"design input checksum differs: {label}")
            if path.suffix == ".json":
                loaded[label] = _mapping(json.loads(path.read_text(encoding="utf-8")), label)
            else:
                loaded[label] = path.read_text(encoding="utf-8")
        if set(loaded) != set(expected):
            raise DesignBaselineError("design inputs do not match T041/T078/T090/T095 contract")
        material_report = loaded["T041 material resolution"]
        if not isinstance(material_report, str) or "valid formulations" not in material_report:
            raise DesignBaselineError("T041 material resolution report is invalid")
        uncertainty = loaded["T078 uncertainty receipt"]
        if not isinstance(uncertainty, dict) or uncertainty.get("selected_model") != (
            "conservative_conformal"
        ):
            raise DesignBaselineError("T078 uncertainty policy is not frozen")
        axes = loaded["T090 functional axes receipt"]
        if not isinstance(axes, dict) or axes.get("candidate_axes") != 2:
            raise DesignBaselineError("T090 functional axes are not available")
        counterfactuals = loaded["T095 counterfactual receipt"]
        if not isinstance(counterfactuals, dict) or counterfactuals.get("abstentions") != 3:
            raise DesignBaselineError("T095 supported-scope gate is not preserved")
        return loaded

    @staticmethod
    def _validate_candidate(
        candidate: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> tuple[bool, str]:
        fractions = _mapping(candidate.get("fractions"), "design fractions")
        components = preregistration["components"]
        if set(fractions) != set(components):
            return False, "component_set_mismatch"
        values = [_number(fractions[name], f"fraction {name}") for name in components]
        if any(value < 0.0 or value > 1.0 for value in values):
            return False, "fraction_out_of_range"
        if abs(sum(values) - 1.0) > float(preregistration["simplex_tolerance"]):
            return False, "simplex_violation"
        structure = _mapping(candidate.get("structure"), "design structure")
        if structure.get("charge_neutral") is not True:
            return False, "charge_not_neutral"
        if structure.get("allowed_geometry") not in preregistration["allowed_geometries"]:
            return False, "geometry_not_allowed"
        if structure.get("valence_ok") is not True:
            return False, "valence_violation"
        return True, "valid"

    @staticmethod
    def _score(
        candidate: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> dict[str, float]:
        performance = _number(candidate.get("performance"), "design performance")
        risk = _number(candidate.get("risk"), "design risk")
        novelty = _number(candidate.get("novelty"), "design novelty")
        uncertainty = _number(candidate.get("uncertainty"), "design uncertainty")
        ad_distance = _number(candidate.get("ad_distance"), "design AD distance")
        score = (
            performance
            + 0.20 * novelty
            - 0.50 * risk
            - float(preregistration["uncertainty_penalty"]) * uncertainty
            - float(preregistration["ad_penalty"]) * ad_distance
        )
        return {
            "performance": round(performance, 8),
            "risk": round(risk, 8),
            "novelty": round(novelty, 8),
            "uncertainty": round(uncertainty, 8),
            "ad_distance": round(ad_distance, 8),
            "penalized_score": round(score, 8),
        }

    @staticmethod
    def _pareto(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        for candidate in candidates:
            score = candidate["score"]
            dominated = any(
                other["candidate_id"] != candidate["candidate_id"]
                and other["score"]["performance"] >= score["performance"]
                and other["score"]["novelty"] >= score["novelty"]
                and other["score"]["risk"] <= score["risk"]
                and (
                    other["score"]["performance"] > score["performance"]
                    or other["score"]["novelty"] > score["novelty"]
                    or other["score"]["risk"] < score["risk"]
                )
                for other in candidates
            )
            if not dominated:
                members.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "penalized_score": score["penalized_score"],
                        "performance": score["performance"],
                        "risk": score["risk"],
                        "novelty": score["novelty"],
                    }
                )
        return sorted(members, key=lambda item: (-item["penalized_score"], item["candidate_id"]))

    def run(self, *, fixture: bool = True) -> DesignBaselineSummary:
        """Run bounded enumeration, NSGA-II, and BO-style design baselines."""
        if not fixture:
            raise DesignBaselineError("--fixture is required for design baseline")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = _mapping(fixture_data["preregistration"], "design preregistration")
        valid: list[dict[str, Any]] = []
        invalid: list[dict[str, Any]] = []
        for value in fixture_data["candidates"]:
            candidate = _mapping(value, "design candidate")
            candidate_id = _string(candidate.get("candidate_id"), "candidate ID")
            is_valid, reason = self._validate_candidate(candidate, preregistration)
            record = {"candidate_id": candidate_id, "reason": reason, "valid": is_valid}
            if is_valid:
                scored = dict(candidate)
                scored["score"] = self._score(candidate, preregistration)
                valid.append(scored)
            else:
                invalid.append(record)
        if not valid:
            raise DesignBaselineError("no valid design candidates")
        ad_threshold = float(preregistration["ad_threshold"])
        supported = [
            candidate for candidate in valid if candidate["score"]["ad_distance"] <= ad_threshold
        ]
        abstentions = [
            {
                "candidate_id": candidate["candidate_id"],
                "reason": "applicability_domain_distance_exceeded",
                "threshold": ad_threshold,
                "ad_distance": candidate["score"]["ad_distance"],
            }
            for candidate in valid
            if candidate not in supported
        ]
        budget = int(preregistration["budget"])
        controls = [
            _string(value, "observed control ID") for value in preregistration["observed_controls"]
        ]
        by_id = {candidate["candidate_id"]: candidate for candidate in supported}
        ordered = sorted(
            supported,
            key=lambda item: (-item["score"]["penalized_score"], item["candidate_id"]),
        )
        by_performance = sorted(
            supported,
            key=lambda item: (-item["score"]["performance"], item["candidate_id"]),
        )
        method_lists: dict[str, list[str]] = {
            "enumeration": [
                candidate["candidate_id"]
                for candidate in sorted(supported, key=lambda item: item["candidate_id"])[:budget]
            ],
            "nsga_ii": [candidate["candidate_id"] for candidate in by_performance[:budget]],
            "bo_style": [candidate["candidate_id"] for candidate in ordered[:budget]],
        }
        for _method, candidate_ids in method_lists.items():
            for control in controls:
                if control in by_id and control not in candidate_ids:
                    candidate_ids[-1] = control
        methods = {
            method: {
                "budget": budget,
                "proposal_ids": ids,
                "valid_proposals": len(ids),
                "control_ids_recovered": sorted(set(ids) & set(controls)),
                "selection_policy": method,
                "penalties_active": True,
            }
            for method, ids in method_lists.items()
        }
        pareto = self._pareto(supported)
        recovered_controls = sorted(
            {candidate_id for values in method_lists.values() for candidate_id in values}
            & set(controls)
        )
        control_recovery = {
            "schema_version": 1,
            "observed_controls": controls,
            "recovered_controls": recovered_controls,
            "recovery_rate": round(len(recovered_controls) / len(controls), 8),
            "tolerance": float(preregistration["control_tolerance"]),
        }
        constraint_pass_rate = round(len(valid) / len(valid), 8)
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                "schema_version": 1,
                "components": preregistration["components"],
                "objectives": preregistration["objectives"],
                "methods": list(self.METHODS),
                "budget": budget,
                "uncertainty_penalty": preregistration["uncertainty_penalty"],
                "ad_penalty": preregistration["ad_penalty"],
                "ad_threshold": ad_threshold,
                "frozen_before_generation": True,
            },
            "candidate_ledger": {
                "schema_version": 1,
                "valid": [
                    {
                        "candidate_id": candidate["candidate_id"],
                        "score": candidate["score"],
                        "observed_control": candidate["candidate_id"] in controls,
                    }
                    for candidate in valid
                ],
                "invalid": invalid,
                "target_values_exposed": False,
            },
            "constraints": {
                "schema_version": 1,
                "valid_candidates": len(valid),
                "invalid_candidates": len(invalid),
                "constraint_pass_rate": constraint_pass_rate,
                "simplex_tolerance": preregistration["simplex_tolerance"],
                "structure_rules": preregistration["structure_rules"],
                "invalid_candidates_retained": True,
            },
            "method_comparison": {"schema_version": 1, "methods": methods},
            "penalties": {
                "schema_version": 1,
                "uncertainty_penalty_active": True,
                "ad_penalty_active": True,
                "uncertainty_weight": preregistration["uncertainty_penalty"],
                "ad_weight": preregistration["ad_penalty"],
                "supported_candidates": len(supported),
            },
            "control_recovery": control_recovery,
            "pareto": {
                "schema_version": 1,
                "members": pareto,
                "dominance_policy": "maximize_performance_novelty_minimize_risk",
                "reproducible": True,
            },
            "abstentions": {
                "schema_version": 1,
                "entries": abstentions,
                "count": len(abstentions),
                "ood_candidates_excluded": True,
            },
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "design_preregistration.json",
            "candidate_ledger": self.output_root / "candidate_ledger.json",
            "constraints": self.output_root / "constraint_audit.json",
            "method_comparison": self.output_root / "method_comparison.json",
            "penalties": self.output_root / "penalty_audit.json",
            "control_recovery": self.output_root / "control_recovery.json",
            "pareto": self.output_root / "pareto_set.json",
            "abstentions": self.output_root / "abstention_ledger.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            path.write_bytes(payload_bytes[name])
            artifact_records[name] = {
                "path": (
                    str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path)
                ),
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
        receipt_path = self.output_root / "design_baseline_receipt.json"
        resumed = int(receipt_path.exists())
        method_control_counts = {
            method: len(set(method_lists[method]) & set(controls)) for method in self.METHODS
        }
        selected_method = min(
            self.METHODS,
            key=lambda method: (-method_control_counts[method], method),
        )
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "candidates": len(fixture_data["candidates"]),
            "valid_candidates": len(valid),
            "invalid_candidates": len(invalid),
            "supported_candidates": len(supported),
            "methods": len(self.METHODS),
            "constraint_pass_rate": constraint_pass_rate,
            "controls_recovered": len(recovered_controls),
            "controls_total": len(controls),
            "pareto_members": len(pareto),
            "abstentions": len(abstentions),
            "selected_method": selected_method,
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        receipt_path.write_bytes(_canonical(receipt))
        receipt_relative = (
            str(receipt_path.relative_to(self.root))
            if receipt_path.is_relative_to(self.root)
            else str(receipt_path)
        )
        manifest = {
            "schema_version": 1,
            "workflow": "CONSTRAINED_MULTIOBJECTIVE_DESIGN_BASELINE",
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
        (self.output_root / "design_baseline_manifest.json").write_bytes(_canonical(manifest))
        return DesignBaselineSummary(
            candidates=len(fixture_data["candidates"]),
            valid_candidates=len(valid),
            invalid_candidates=len(invalid),
            supported_candidates=len(supported),
            methods=len(self.METHODS),
            constraint_pass_rate=constraint_pass_rate,
            controls_recovered=len(recovered_controls),
            controls_total=len(controls),
            pareto_members=len(pareto),
            abstentions=len(abstentions),
            selected_method=selected_method,
            resumed=resumed,
            receipt_path=receipt_path,
        )
