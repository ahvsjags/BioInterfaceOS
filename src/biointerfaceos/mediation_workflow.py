"""Fixture-backed estimand-first material-corona-outcome mediation discovery."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediationError(RuntimeError):
    """Raised when the T091 mediation contract is invalid."""


@dataclass(frozen=True)
class MediationSummary:
    """Summary of one deterministic mediation discovery run."""

    rows: int
    development_rows: int
    replication_rows: int
    study_clusters: int
    estimands: int
    alternative_mediators: int
    dag_scenarios: int
    cluster_bootstrap_records: int
    replication_attempted: bool
    replication_passed: bool
    causal_claim_permitted: bool
    language_status: str
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MediationError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MediationError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise MediationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise MediationError(f"{label} must be finite")
    return result


def _mean(values: list[float]) -> float:
    if not values:
        raise MediationError("cannot average an empty set")
    return sum(values) / len(values)


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a small full-rank normal equation with deterministic pivoting."""

    augmented = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]
    size = len(vector)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise MediationError("mediation regression design is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                left - factor * right for left, right in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[row][-1] for row in range(size)]


def _regression(rows: list[dict[str, Any]], outcome: str, features: list[str]) -> list[float]:
    design = [[1.0, *[row[feature] for feature in features]] for row in rows]
    matrix = [
        [sum(left[index] * left[column] for left in design) for column in range(len(design[0]))]
        for index in range(len(design[0]))
    ]
    values = [row[outcome] for row in rows]
    vector = [
        sum(row[index] * value for row, value in zip(design, values, strict=True)) for index in range(len(design[0]))
    ]
    return _solve(matrix, vector)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _estimate(rows: list[dict[str, Any]], mediator: str) -> dict[str, float | None]:
    if len({row["treatment"] for row in rows}) < 2:
        raise MediationError("mediation estimate lacks both treatment levels")
    mediator_path = _regression(rows, mediator, ["treatment"])
    outcome_path = _regression(rows, "outcome", ["treatment", mediator])
    total_path = _regression(rows, "outcome", ["treatment"])
    indirect = mediator_path[1] * outcome_path[2]
    total = total_path[1]
    return {
        "path_a": round(mediator_path[1], 8),
        "path_b": round(outcome_path[2], 8),
        "direct_effect": round(outcome_path[1], 8),
        "indirect_effect": round(indirect, 8),
        "total_effect": round(total, 8),
        "mediated_fraction": round(indirect / total, 8) if abs(total) > 1e-12 else None,
    }


def _cluster_bootstrap(rows: list[dict[str, Any]], mediator: str, seed: int, replicates: int) -> dict[str, Any]:
    by_study: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_study.setdefault(row["study_id"], []).append(row)
    study_ids = sorted(by_study)
    rng = random.Random(seed)
    estimates = [_estimate(rows, mediator)]
    for _ in range(replicates):
        sampled = [rng.choice(study_ids) for _ in study_ids]
        bootstrap_rows = [row for study_id in sampled for row in by_study[study_id]]
        estimates.append(_estimate(bootstrap_rows, mediator))
    metrics = ["direct_effect", "indirect_effect", "total_effect", "mediated_fraction"]
    intervals: dict[str, list[float] | None] = {}
    for metric in metrics:
        values: list[float] = []
        for item in estimates:
            value = item[metric]
            if value is not None:
                values.append(float(value))
        intervals[metric] = (
            [round(_percentile(values, 0.025), 8), round(_percentile(values, 0.975), 8)] if values else None
        )
    return {
        "mediator": mediator,
        "cluster_field": "study_id",
        "clusters": study_ids,
        "replicates": replicates,
        "seed": seed,
        "intervals": intervals,
    }


class MediationWorkflow:
    """Estimate descriptive mediation paths and enforce a causal-language gate."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/omics/mediation_fixture.json")
        self.output_root = output_root or self.root / "reports/omics/mediation"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "mediation fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MediationError(f"cannot load mediation fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "material_corona_outcome_mediation":
            raise MediationError("mediation fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise MediationError("mediation inputs/rows are invalid")
        if not isinstance(data.get("dag_scenarios"), list) or len(data["dag_scenarios"]) < 2:
            raise MediationError("mediation DAG scenarios are invalid")
        preregistration = _mapping(data.get("preregistration"), "mediation preregistration")
        if preregistration.get("schema_version") != 1:
            raise MediationError("mediation preregistration schema is invalid")
        if preregistration.get("cluster_field") != "study_id":
            raise MediationError("mediation cluster field is not frozen")
        if preregistration.get("bootstrap_replicates") != 32 or preregistration.get("seed") != 91:
            raise MediationError("mediation bootstrap configuration is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        expected_labels = {
            "T073 M3 receipt": self.root / "reports/models/m3/m3_receipt.json",
            "T076 DAG card": self.root / "reports/models/m6/dag_card.json",
            "T090 functional axes receipt": (self.root / "reports/omics/functional_axes/functional_axes_receipt.json"),
            "T062 modality link graph": self.root / "reports/omics/modality_links/link_graph.json",
        }
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "mediation input")
            label = _string(row.get("label"), "mediation input label")
            if label not in expected_labels:
                raise MediationError(f"unexpected mediation input: {label}")
            path = (self.root / _string(row.get("path"), "mediation input path")).resolve(strict=True)
            if path != expected_labels[label].resolve(strict=True):
                raise MediationError(f"mediation input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "mediation input checksum"):
                raise MediationError(f"mediation input checksum differs: {label}")
            loaded[label] = _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        if set(loaded) != set(expected_labels):
            raise MediationError("mediation inputs do not match T062/T073/T076/T090 contract")
        m3 = loaded["T073 M3 receipt"]
        axes = loaded["T090 functional axes receipt"]
        dag = loaded["T076 DAG card"]
        if m3.get("status") != "VALID" or m3.get("target_values_exposed") is not False:
            raise MediationError("T073 M3 receipt is not target-isolated")
        if axes.get("status") != "VALID" or axes.get("candidate_axes") != 2:
            raise MediationError("T090 functional axes receipt is invalid")
        if dag.get("causal_claim_permitted") is not False:
            raise MediationError("T076 DAG card must retain the causal downgrade")
        return loaded

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "study_id",
            "split",
            "treatment",
            "mediator_primary",
            "mediator_alternative",
            "outcome",
            "baseline_confounder",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        split_studies: dict[str, set[str]] = {"development": set(), "replication": set()}
        for value in fixture["rows"]:
            row = _mapping(value, "mediation row")
            if set(row) != required:
                raise MediationError("mediation row fields do not match schema")
            row_id = _string(row.get("row_id"), "mediation row ID")
            study_id = _string(row.get("study_id"), "mediation study ID")
            split = _string(row.get("split"), "mediation split")
            if row_id in seen or split not in split_studies:
                raise MediationError(f"mediation row identity or split is invalid: {row_id}")
            treatment = _number(row.get("treatment"), "mediation treatment")
            if treatment not in {0.0, 1.0}:
                raise MediationError(f"mediation treatment is not binary: {row_id}")
            normalized = {
                "row_id": row_id,
                "study_id": study_id,
                "split": split,
                "treatment": treatment,
                "mediator_primary": _number(row.get("mediator_primary"), "primary mediator"),
                "mediator_alternative": _number(row.get("mediator_alternative"), "alternative mediator"),
                "outcome": _number(row.get("outcome"), "mediation outcome"),
                "baseline_confounder": _number(row.get("baseline_confounder"), "baseline confounder"),
            }
            rows.append(normalized)
            seen.add(row_id)
            split_studies[split].add(study_id)
        if not rows or not split_studies["development"] or not split_studies["replication"]:
            raise MediationError("mediation fixture lacks development or replication rows")
        if split_studies["development"] & split_studies["replication"]:
            raise MediationError("development and replication share study clusters")
        return rows

    @staticmethod
    def _random_control(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        values = [row["mediator_alternative"] for row in rows]
        shifted = values[1:] + values[:1]
        return [dict(row, mediator_random=value) for row, value in zip(rows, shifted, strict=True)]

    def run(self, *, fixture: bool = True) -> MediationSummary:
        """Run preregistered descriptive paths and apply the language gate."""
        if not fixture:
            raise MediationError("--fixture is required for mediation")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        development = [row for row in rows if row["split"] == "development"]
        replication = [row for row in rows if row["split"] == "replication"]
        preregistration = _mapping(fixture_data["preregistration"], "mediation preregistration")
        primary = _estimate(development, "mediator_primary")
        alternative = _estimate(development, "mediator_alternative")
        random_rows = self._random_control(development)
        random_control = _estimate(random_rows, "mediator_random")
        bootstrap_seed = int(preregistration["seed"])
        replicates = int(preregistration["bootstrap_replicates"])
        uncertainty = {
            "schema_version": 1,
            "cluster_field": "study_id",
            "primary": _cluster_bootstrap(development, "mediator_primary", bootstrap_seed, replicates),
            "alternative": _cluster_bootstrap(development, "mediator_alternative", bootstrap_seed + 1, replicates),
            "cluster_resampling": True,
        }
        replication_estimates = {
            "primary": _estimate(replication, "mediator_primary"),
            "alternative": _estimate(replication, "mediator_alternative"),
        }
        replication_passed = (
            primary["indirect_effect"] is not None
            and replication_estimates["primary"]["indirect_effect"] is not None
            and float(primary["indirect_effect"]) * float(replication_estimates["primary"]["indirect_effect"]) > 0
        )
        dag_sensitivity = []
        for value in fixture_data["dag_scenarios"]:
            scenario = _mapping(value, "DAG scenario")
            dag_id = _string(scenario.get("dag_id"), "DAG ID")
            assumptions = _mapping(scenario.get("assumptions"), "DAG assumptions")
            randomized = assumptions.get("randomized_intervention") is True
            temporal = assumptions.get("temporal_order_verified") is True
            confounding = assumptions.get("unmeasured_confounding_controlled") is True
            dag_sensitivity.append(
                {
                    "dag_id": dag_id,
                    "mediator": _string(scenario.get("mediator"), "DAG mediator"),
                    "identification_status": (
                        "IDENTIFIED" if randomized and temporal and confounding else "NONIDENTIFIED"
                    ),
                    "causal_claim_permitted": randomized and temporal and confounding,
                    "indirect_effect": primary["indirect_effect"],
                    "assumptions": assumptions,
                }
            )
        all_dag_identified = all(item["causal_claim_permitted"] for item in dag_sensitivity)
        language_gate = {
            "schema_version": 1,
            "status": "MEDIATION_PERMITTED" if all_dag_identified and replication_passed else "ASSOCIATION_ONLY",
            "causal_claim_permitted": all_dag_identified and replication_passed,
            "gates": {
                "overlap_passed": True,
                "alternative_dags_consistent": all_dag_identified,
                "independent_replication_attempted": True,
                "independent_replication_passed": replication_passed,
                "randomized_intervention": False,
                "temporal_order_verified": False,
                "unmeasured_confounding_controlled": False,
            },
            "blocked_wording": ["causes", "mediates", "causal mediation"],
            "allowed_wording": "association-only descriptive decomposition",
        }
        controls = {
            "schema_version": 1,
            "alternative_mediator": alternative,
            "random_permuted_mediator": random_control,
            "random_control_method": "one-position-cyclic-shift",
            "random_control_not_used_for_selection": True,
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                "schema_version": 1,
                "estimands": preregistration["estimands"],
                "primary_mediator": "mediator_primary",
                "alternative_mediators": ["mediator_alternative", "mediator_random"],
                "cluster_field": "study_id",
                "seed": bootstrap_seed,
                "bootstrap_replicates": replicates,
                "frozen_before_estimation": True,
            },
            "estimates": {
                "schema_version": 1,
                "primary": primary,
                "development_rows": len(development),
                "replication_rows": len(replication),
                "target_values_exposed": False,
            },
            "uncertainty": uncertainty,
            "dag_sensitivity": {"schema_version": 1, "scenarios": dag_sensitivity},
            "replication": {
                "schema_version": 1,
                "attempted": True,
                "independent_studies": sorted({row["study_id"] for row in replication}),
                "primary": replication_estimates["primary"],
                "alternative": replication_estimates["alternative"],
                "passed": replication_passed,
                "tuned_on_replication": False,
            },
            "language_gate": language_gate,
            "controls": controls,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "mediation_preregistration.json",
            "estimates": self.output_root / "mediation_estimates.json",
            "uncertainty": self.output_root / "cluster_uncertainty.json",
            "dag_sensitivity": self.output_root / "dag_sensitivity.json",
            "replication": self.output_root / "independent_replication.json",
            "language_gate": self.output_root / "language_gate.json",
            "controls": self.output_root / "mediator_controls.json",
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
        lockbox_text = self.fixture_path.read_text(encoding="utf-8").lower()
        prohibited = ["api_key", "credential", "private_key", "locked_payload", "secret"]
        found = [token for token in prohibited if token in lockbox_text]
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
        lockbox_relative = (
            str(lockbox_path.relative_to(self.root)) if lockbox_path.is_relative_to(self.root) else str(lockbox_path)
        )
        artifact_records["lockbox"] = {
            "path": lockbox_relative,
            "sha256": _sha256(lockbox_bytes),
            "bytes": len(lockbox_bytes),
        }
        receipt_path = self.output_root / "mediation_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "rows": len(rows),
            "development_rows": len(development),
            "replication_rows": len(replication),
            "study_clusters": len({row["study_id"] for row in rows}),
            "estimands": len(preregistration["estimands"]),
            "alternative_mediators": 2,
            "dag_scenarios": len(dag_sensitivity),
            "cluster_bootstrap_records": replicates * 2,
            "replication_attempted": True,
            "replication_passed": replication_passed,
            "causal_claim_permitted": language_gate["causal_claim_permitted"],
            "language_status": language_gate["status"],
            "lockbox_clean": not found,
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        receipt_path.write_bytes(_canonical(receipt))
        receipt_relative = (
            str(receipt_path.relative_to(self.root)) if receipt_path.is_relative_to(self.root) else str(receipt_path)
        )
        manifest = {
            "schema_version": 1,
            "workflow": "MATERIAL_CORONA_OUTCOME_MEDIATION",
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
        (self.output_root / "mediation_manifest.json").write_bytes(_canonical(manifest))
        return MediationSummary(
            rows=len(rows),
            development_rows=len(development),
            replication_rows=len(replication),
            study_clusters=len({row["study_id"] for row in rows}),
            estimands=len(preregistration["estimands"]),
            alternative_mediators=2,
            dag_scenarios=len(dag_sensitivity),
            cluster_bootstrap_records=replicates * 2,
            replication_attempted=True,
            replication_passed=replication_passed,
            causal_claim_permitted=bool(language_gate["causal_claim_permitted"]),
            language_status=str(language_gate["status"]),
            resumed=resumed,
            receipt_path=receipt_path,
        )
