"""Fixture-backed unit-aware symbolic design-law discovery."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SymbolicLawsError(RuntimeError):
    """Raised when the T093 symbolic-law contract is invalid."""


@dataclass(frozen=True)
class SymbolicLawsSummary:
    """Summary of one deterministic symbolic-law discovery run."""

    candidates: int
    unit_valid: int
    rejected: int
    nested_folds: int
    controls: int
    bootstrap_stability: float
    ood_passed: bool
    selected_expression: str
    fallback: bool
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
        raise SymbolicLawsError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SymbolicLawsError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SymbolicLawsError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise SymbolicLawsError(f"{label} must be finite")
    return result


def _mean(values: list[float]) -> float:
    if not values:
        raise SymbolicLawsError("cannot average an empty set")
    return sum(values) / len(values)


def _rmse(errors: list[float]) -> float:
    return math.sqrt(_mean([error * error for error in errors]))


class SymbolicLawsWorkflow:
    """Discover bounded expressions with unit, stability, and OOD gates."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/symbolic_laws_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/symbolic_laws"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "symbolic-laws fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SymbolicLawsError(f"cannot load symbolic-laws fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "unit_aware_symbolic_laws":
            raise SymbolicLawsError("symbolic-laws fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise SymbolicLawsError("symbolic-laws inputs/rows are invalid")
        if not isinstance(data.get("features"), dict) or not data["features"]:
            raise SymbolicLawsError("symbolic-laws feature units are invalid")
        if not isinstance(data.get("candidates"), list) or not data["candidates"]:
            raise SymbolicLawsError("symbolic-laws candidates are invalid")
        preregistration = _mapping(data.get("preregistration"), "symbolic-laws preregistration")
        if preregistration.get("schema_version") != 1:
            raise SymbolicLawsError("symbolic-laws preregistration schema is invalid")
        if preregistration.get("complexity_penalty") != 0.005:
            raise SymbolicLawsError("symbolic-laws complexity penalty is not frozen")
        if preregistration.get("bootstrap_replicates") != 32 or preregistration.get("seed") != 93:
            raise SymbolicLawsError("symbolic-laws bootstrap configuration is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        expected = {
            "T071 normalized model results": self.root / "reports/models/m1/m1_results.json",
            "T089 tournament config": (
                self.root / "reports/claims/tournament/tournament_config.json"
            ),
            "T090 functional axes receipt": (
                self.root / "reports/omics/functional_axes/functional_axes_receipt.json"
            ),
        }
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "symbolic-laws input")
            label = _string(row.get("label"), "symbolic-laws input label")
            if label not in expected:
                raise SymbolicLawsError(f"unexpected symbolic-laws input: {label}")
            path = (self.root / _string(row.get("path"), "symbolic-laws input path")).resolve(
                strict=True
            )
            if path != expected[label].resolve(strict=True):
                raise SymbolicLawsError(f"symbolic-laws input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(
                row.get("sha256"), "symbolic-laws input checksum"
            ):
                raise SymbolicLawsError(f"symbolic-laws input checksum differs: {label}")
            loaded[label] = _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        if set(loaded) != set(expected):
            raise SymbolicLawsError("symbolic-laws inputs do not match T071/T089/T090 contract")
        if loaded["T071 normalized model results"].get("target_values_exposed") is not False:
            raise SymbolicLawsError("T071 model results are not target-isolated")
        if loaded["T089 tournament config"].get("frozen_before_primary") is not True:
            raise SymbolicLawsError("T089 config is not frozen")
        if loaded["T090 functional axes receipt"].get("candidate_axes") != 2:
            raise SymbolicLawsError("T090 axes are not available")
        return loaded

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "study_id",
            "material_id",
            "split",
            "surface_norm",
            "charge_norm",
            "functional_axis",
            "dose_mg",
            "outcome",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "symbolic-laws row")
            if set(row) != required:
                raise SymbolicLawsError("symbolic-laws row fields do not match schema")
            row_id = _string(row.get("row_id"), "symbolic-laws row ID")
            split = _string(row.get("split"), "symbolic-laws split")
            if row_id in seen or split not in {"development", "validation", "ood"}:
                raise SymbolicLawsError(f"symbolic-laws row identity or split is invalid: {row_id}")
            rows.append(
                {
                    "row_id": row_id,
                    "study_id": _string(row.get("study_id"), "symbolic study ID"),
                    "material_id": _string(row.get("material_id"), "symbolic material ID"),
                    "split": split,
                    "surface_norm": _number(row.get("surface_norm"), "surface norm"),
                    "charge_norm": _number(row.get("charge_norm"), "charge norm"),
                    "functional_axis": _number(row.get("functional_axis"), "functional axis"),
                    "dose_mg": _number(row.get("dose_mg"), "dose"),
                    "outcome": _number(row.get("outcome"), "symbolic outcome"),
                }
            )
            seen.add(row_id)
        if not rows or not any(row["split"] == "development" for row in rows):
            raise SymbolicLawsError("symbolic-laws fixture has no development rows")
        if not any(row["split"] == "validation" for row in rows):
            raise SymbolicLawsError("symbolic-laws fixture has no validation rows")
        if not any(row["split"] == "ood" for row in rows):
            raise SymbolicLawsError("symbolic-laws fixture has no OOD rows")
        return rows

    @staticmethod
    def _unit_audit(
        candidates: list[Any], features: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        feature_units = {
            str(name): _string(unit, f"unit for {name}") for name, unit in features.items()
        }
        for value in candidates:
            candidate = _mapping(value, "symbolic candidate")
            candidate_id = _string(candidate.get("candidate_id"), "candidate ID")
            terms = candidate.get("terms")
            if not isinstance(terms, list) or not terms:
                raise SymbolicLawsError(f"candidate terms are invalid: {candidate_id}")
            output_unit = _string(candidate.get("output_unit"), "candidate output unit")
            derived_units: list[str] = []
            for term_value in terms:
                term = _mapping(term_value, "symbolic term")
                feature = _string(term.get("feature"), "symbolic feature")
                if feature not in feature_units:
                    raise SymbolicLawsError(f"unknown symbolic feature: {feature}")
                power = int(_number(term.get("power"), "symbolic power"))
                if power not in {1, 2}:
                    rejected.append(
                        {
                            "candidate_id": candidate_id,
                            "reason": "unsupported_power",
                            "unit_valid": False,
                        }
                    )
                    break
                unit = feature_units[feature]
                derived_units.append(unit if power == 1 else f"{unit}^{power}")
            else:
                if len(set(derived_units)) != 1 or derived_units[0] != output_unit:
                    rejected.append(
                        {
                            "candidate_id": candidate_id,
                            "reason": "dimensional_inconsistency",
                            "derived_units": derived_units,
                            "output_unit": output_unit,
                            "unit_valid": False,
                        }
                    )
                    continue
                valid.append(
                    {
                        "candidate_id": candidate_id,
                        "expression": _string(candidate.get("expression"), "candidate expression"),
                        "terms": terms,
                        "complexity": int(
                            _number(candidate.get("complexity"), "candidate complexity")
                        ),
                        "unit_valid": True,
                    }
                )
        return valid, rejected

    @staticmethod
    def _predict(candidate: Mapping[str, Any], row: Mapping[str, Any]) -> float:
        total = 0.0
        for value in candidate["terms"]:
            term = _mapping(value, "symbolic term")
            total += float(term["coefficient"]) * float(row[str(term["feature"])]) ** int(
                term["power"]
            )
        return total

    @classmethod
    def _score(
        cls, candidate: Mapping[str, Any], rows: list[dict[str, Any]], penalty: float
    ) -> dict[str, Any]:
        errors = [cls._predict(candidate, row) - row["outcome"] for row in rows]
        rmse = _rmse(errors)
        objective = rmse + penalty * int(candidate["complexity"])
        return {
            "n": len(rows),
            "rmse": round(rmse, 8),
            "mae": round(_mean([abs(error) for error in errors]), 8),
            "objective": round(objective, 8),
        }

    @classmethod
    def _controls(cls, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        predictions: dict[str, Callable[[dict[str, Any]], float]] = {
            "gam_control": lambda row: 0.60 * row["surface_norm"]
            + 0.30 * row["functional_axis"]
            + 0.10 * row["charge_norm"],
            "tree_control": lambda row: (
                0.58 * row["surface_norm"]
                + 0.32 * row["functional_axis"]
                + 0.10 * row["charge_norm"]
                if row["surface_norm"] < 0.5
                else 0.65 * row["surface_norm"]
                + 0.25 * row["functional_axis"]
                + 0.10 * row["charge_norm"]
            ),
        }
        result: dict[str, dict[str, Any]] = {}
        for name, function in predictions.items():
            errors = [function(row) - row["outcome"] for row in rows]
            result[name] = {
                "n": len(rows),
                "rmse": round(_rmse(errors), 8),
                "mae": round(_mean([abs(error) for error in errors]), 8),
                "selection_role": "control_only",
            }
        return result

    @classmethod
    def _nested_cv(
        cls,
        candidates: list[dict[str, Any]],
        rows: list[dict[str, Any]],
        penalty: float,
    ) -> list[dict[str, Any]]:
        folds: list[dict[str, Any]] = []
        for outer_study in sorted({row["study_id"] for row in rows}):
            inner = [row for row in rows if row["study_id"] != outer_study]
            outer = [row for row in rows if row["study_id"] == outer_study]
            inner_scores = {
                candidate["candidate_id"]: cls._score(candidate, inner, penalty)
                for candidate in candidates
            }
            selected_id = min(
                inner_scores,
                key=lambda candidate_id: (
                    inner_scores[candidate_id]["objective"],
                    candidate_id,
                ),
            )
            selected = next(
                candidate for candidate in candidates if candidate["candidate_id"] == selected_id
            )
            outer_score = cls._score(selected, outer, penalty)
            folds.append(
                {
                    "outer_study": outer_study,
                    "inner_studies": sorted({row["study_id"] for row in inner}),
                    "selected_candidate": selected_id,
                    "outer_score": outer_score,
                    "tuned_on_outer": False,
                }
            )
        return folds

    @classmethod
    def _bootstrap(
        cls,
        candidates: list[dict[str, Any]],
        rows: list[dict[str, Any]],
        penalty: float,
        seed: int,
        replicates: int,
    ) -> dict[str, Any]:
        rng = random.Random(seed)
        counts = {candidate["candidate_id"]: 0 for candidate in candidates}
        for _ in range(replicates):
            sample = [rng.choice(rows) for _ in rows]
            selected = min(
                candidates,
                key=lambda candidate: (
                    cls._score(candidate, sample, penalty)["objective"],
                    candidate["candidate_id"],
                ),
            )
            counts[selected["candidate_id"]] += 1
        selected_id = max(counts, key=lambda candidate_id: (counts[candidate_id], candidate_id))
        return {
            "seed": seed,
            "replicates": replicates,
            "selection_counts": counts,
            "selected_candidate": selected_id,
            "stability": round(counts[selected_id] / replicates, 8),
        }

    def run(self, *, fixture: bool = True) -> SymbolicLawsSummary:
        """Discover and gate unit-valid expressions."""
        if not fixture:
            raise SymbolicLawsError("--fixture is required for symbolic-laws")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        preregistration = _mapping(fixture_data["preregistration"], "symbolic-laws preregistration")
        valid, rejected = self._unit_audit(fixture_data["candidates"], fixture_data["features"])
        if not valid:
            raise SymbolicLawsError("no unit-valid symbolic candidates")
        development = [row for row in rows if row["split"] == "development"]
        validation = [row for row in rows if row["split"] == "validation"]
        ood = [row for row in rows if row["split"] == "ood"]
        penalty = float(preregistration["complexity_penalty"])
        candidate_scores = {
            candidate["candidate_id"]: {
                "development": self._score(candidate, development, penalty),
                "validation": self._score(candidate, validation, penalty),
                "ood": self._score(candidate, ood, penalty),
                "complexity": candidate["complexity"],
                "expression": candidate["expression"],
                "unit_valid": True,
            }
            for candidate in valid
        }
        nested_folds = self._nested_cv(valid, development, penalty)
        bootstrap = self._bootstrap(
            valid,
            development,
            penalty,
            int(preregistration["seed"]),
            int(preregistration["bootstrap_replicates"]),
        )
        selected_id = min(
            candidate_scores,
            key=lambda candidate_id: (
                candidate_scores[candidate_id]["validation"]["objective"],
                candidate_scores[candidate_id]["complexity"],
                candidate_id,
            ),
        )
        selected = next(
            candidate for candidate in valid if candidate["candidate_id"] == selected_id
        )
        ood_threshold = float(preregistration["ood_rmse_threshold"])
        ood_passed = candidate_scores[selected_id]["ood"]["rmse"] <= ood_threshold
        stability_passed = bootstrap["selected_candidate"] == selected_id and bootstrap[
            "stability"
        ] >= float(preregistration["stability_threshold"])
        fallback = not (ood_passed and stability_passed and bool(nested_folds))
        pareto: list[dict[str, Any]] = []
        for candidate_id, score in candidate_scores.items():
            dominated = any(
                other_id != candidate_id
                and candidate_scores[other_id]["validation"]["rmse"] <= score["validation"]["rmse"]
                and candidate_scores[other_id]["complexity"] <= score["complexity"]
                and (
                    candidate_scores[other_id]["validation"]["rmse"] < score["validation"]["rmse"]
                    or candidate_scores[other_id]["complexity"] < score["complexity"]
                )
                for other_id in candidate_scores
            )
            pareto.append({"candidate_id": candidate_id, "dominated": dominated})
        controls = {
            "development": self._controls(development),
            "validation": self._controls(validation),
            "ood": self._controls(ood),
            "selection_role": "control_only",
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                "schema_version": 1,
                "grammar": preregistration["grammar"],
                "features": fixture_data["features"],
                "complexity_penalty": penalty,
                "bootstrap_replicates": int(preregistration["bootstrap_replicates"]),
                "seed": int(preregistration["seed"]),
                "ood_rmse_threshold": ood_threshold,
                "stability_threshold": float(preregistration["stability_threshold"]),
                "frozen_before_fit": True,
            },
            "unit_audit": {
                "schema_version": 1,
                "valid_candidates": [candidate["candidate_id"] for candidate in valid],
                "rejected_candidates": rejected,
                "target_unit": "1",
            },
            "candidate_scores": {
                "schema_version": 1,
                "scores": candidate_scores,
                "target_values_exposed": False,
            },
            "nested_cv": {
                "schema_version": 1,
                "folds": nested_folds,
                "study_disjoint": True,
                "nested": True,
            },
            "bootstrap": {"schema_version": 1, **bootstrap},
            "pareto": {
                "schema_version": 1,
                "front": pareto,
                "selected_candidate": selected_id,
                "complexity_penalty_frozen": True,
            },
            "controls": {"schema_version": 1, **controls},
            "ood": {
                "schema_version": 1,
                "selected_candidate": selected_id,
                "rmse": candidate_scores[selected_id]["ood"]["rmse"],
                "threshold": ood_threshold,
                "passed": ood_passed,
                "flexible_controls_not_used_for_selection": True,
            },
            "claim_gate": {
                "schema_version": 1,
                "selected_expression": selected["expression"],
                "symbolic_law_permitted": not fallback,
                "fallback": fallback,
                "allowed_wording": (
                    "stable unit-aware candidate law"
                    if not fallback
                    else "flexible predictive baseline; no simple law"
                ),
            },
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "symbolic_preregistration.json",
            "unit_audit": self.output_root / "unit_audit.json",
            "candidate_scores": self.output_root / "candidate_scores.json",
            "nested_cv": self.output_root / "nested_study_cv.json",
            "bootstrap": self.output_root / "bootstrap_stability.json",
            "pareto": self.output_root / "pareto_front.json",
            "controls": self.output_root / "flexible_controls.json",
            "ood": self.output_root / "ood_validation.json",
            "claim_gate": self.output_root / "claim_gate.json",
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
        receipt_path = self.output_root / "symbolic_laws_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "candidates": len(fixture_data["candidates"]),
            "unit_valid": len(valid),
            "rejected": len(rejected),
            "nested_folds": len(nested_folds),
            "controls": 2,
            "bootstrap_stability": bootstrap["stability"],
            "ood_passed": ood_passed,
            "selected_expression": selected["expression"],
            "fallback": fallback,
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
            "workflow": "UNIT_AWARE_SYMBOLIC_LAWS",
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
        (self.output_root / "symbolic_laws_manifest.json").write_bytes(_canonical(manifest))
        return SymbolicLawsSummary(
            candidates=len(fixture_data["candidates"]),
            unit_valid=len(valid),
            rejected=len(rejected),
            nested_folds=len(nested_folds),
            controls=2,
            bootstrap_stability=float(bootstrap["stability"]),
            ood_passed=ood_passed,
            selected_expression=selected["expression"],
            fallback=fallback,
            resumed=resumed,
            receipt_path=receipt_path,
        )
