"""Deterministic fixture-backed label-free quantification workflow."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class QuantificationError(RuntimeError):
    """Raised when the bounded label-free fixture is invalid or unsafe."""


@dataclass(frozen=True)
class QuantificationSummary:
    """Summary of one deterministic LFQ run."""

    runs: int
    samples: int
    quantifiable_proteins: int
    groups: int
    missing_cells: int
    contaminant_groups: int
    ratios_passed: int
    ratios_total: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise QuantificationError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuantificationError(f"{label} must be a non-empty string")
    return value.strip()


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise QuantificationError(f"{label} must be an integer")
    return int(value)


def _float(value: Any, label: str) -> float:
    if value is None:
        raise QuantificationError(f"{label} must be numeric")
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise QuantificationError(f"{label} must be numeric")
    return float(value)


def _median(values: Sequence[float]) -> float:
    if not values:
        raise QuantificationError("cannot compute a median from no observed values")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


class QuantificationWorkflow:
    """Quantify accepted T054 proteins with explicit fixture normalization."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/quantification_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/quantification"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise QuantificationError(f"cannot load quantification fixture: {exc}") from exc
        data = _mapping(fixture, "quantification fixture")
        if data.get("schema_version") != 1:
            raise QuantificationError("quantification fixture schema_version must be 1")
        for key in ("search", "samples", "intensities", "protein_groups", "expected_ratios"):
            if key not in data:
                raise QuantificationError(f"quantification fixture missing {key}")
            list_keys = {"samples", "intensities", "protein_groups", "expected_ratios"}
            if not isinstance(data[key], list if key in list_keys else dict):
                raise QuantificationError(f"quantification fixture {key} has invalid type")
        return data

    def _verify_search(self, data: Mapping[str, Any]) -> set[str]:
        search = _mapping(data["search"], "search")
        receipt_relative = _string(search.get("receipt_path"), "search.receipt_path")
        receipt_path = (self.root / receipt_relative).resolve(strict=True)
        try:
            receipt_path.relative_to(self.root)
        except ValueError as exc:
            raise QuantificationError("search receipt must remain inside repository root") from exc
        expected_receipt_sha = _string(search.get("receipt_sha256"), "search.receipt_sha256")
        actual_receipt_sha = _sha256_path(receipt_path)
        if actual_receipt_sha != expected_receipt_sha:
            raise QuantificationError("T054 search receipt checksum differs from fixture")
        receipt = _mapping(json.loads(receipt_path.read_text(encoding="utf-8")), "search receipt")
        if receipt.get("status") != "COMPLETED":
            raise QuantificationError("T054 search receipt is not completed")
        artifacts = _mapping(receipt["artifacts"], "search artifacts")
        proteins_artifact = _mapping(artifacts["proteins"], "proteins artifact")
        proteins_path = (
            self.root / _string(proteins_artifact.get("path"), "proteins path")
        ).resolve(strict=True)
        if _sha256_path(proteins_path) != _string(
            proteins_artifact.get("sha256"), "proteins sha256"
        ):
            raise QuantificationError("T054 protein output checksum differs from receipt")
        proteins = _mapping(json.loads(proteins_path.read_text(encoding="utf-8")), "protein output")
        rows = proteins.get("rows")
        if not isinstance(rows, list) or not rows:
            raise QuantificationError("T054 protein output has no accepted proteins")
        accessions: set[str] = set()
        for row_value in rows:
            row = _mapping(row_value, "protein row")
            accession = _string(row.get("protein_accession"), "protein accession")
            if row.get("is_decoy") is not False:
                raise QuantificationError("quantification cannot consume decoy proteins")
            accessions.add(accession)
        return accessions

    def _load_samples(
        self, data: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        samples: list[dict[str, Any]] = []
        runs: dict[str, dict[str, Any]] = {}
        seen_replicates: set[tuple[str, int]] = set()
        for value in cast(list[Any], data["samples"]):
            row = _mapping(value, "sample")
            run_id = _string(row.get("run_id"), "sample.run_id")
            sample_id = _string(row.get("sample_id"), "sample.sample_id")
            condition = _string(row.get("condition"), "sample.condition")
            replicate = _int(row.get("biological_replicate"), "sample.biological_replicate")
            factor = _float(row.get("normalization_factor"), "sample.normalization_factor")
            if run_id in runs or (sample_id, replicate) in seen_replicates:
                raise QuantificationError("sample run or biological replicate is duplicated")
            if replicate < 1 or factor <= 0:
                raise QuantificationError("sample replicate/factor is invalid")
            record = {
                "run_id": run_id,
                "sample_id": sample_id,
                "condition": condition,
                "biological_replicate": replicate,
                "normalization_factor": factor,
            }
            samples.append(record)
            runs[run_id] = record
            seen_replicates.add((sample_id, replicate))
        if len(samples) < 2:
            raise QuantificationError("at least two independent runs are required")
        condition_replicates: dict[str, set[int]] = {}
        for row in samples:
            condition_replicates.setdefault(row["condition"], set()).add(
                row["biological_replicate"]
            )
        if any(len(replicates) < 2 for replicates in condition_replicates.values()):
            raise QuantificationError("each condition requires two biological replicates")
        return samples, runs

    def _load_intensities(
        self,
        data: Mapping[str, Any],
        runs: Mapping[str, Mapping[str, Any]],
        accepted_proteins: set[str],
    ) -> tuple[list[dict[str, Any]], set[str]]:
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        proteins: set[str] = set()
        for value in cast(list[Any], data["intensities"]):
            row = _mapping(value, "intensity")
            run_id = _string(row.get("run_id"), "intensity.run_id")
            protein = _string(row.get("protein_accession"), "intensity.protein_accession")
            if run_id not in runs or (run_id, protein) in seen:
                raise QuantificationError("intensity run/protein is unknown or duplicated")
            contaminant = row.get("is_contaminant")
            if not isinstance(contaminant, bool):
                raise QuantificationError("intensity is_contaminant must be boolean")
            if not contaminant and protein not in accepted_proteins:
                raise QuantificationError("intensity protein was not accepted by T054")
            intensity = row.get("intensity")
            observed = row.get("observed")
            if not isinstance(observed, bool):
                raise QuantificationError("intensity observed must be boolean")
            if observed:
                value_float = _float(intensity, "intensity.value")
                if value_float <= 0:
                    raise QuantificationError("observed intensity must be positive")
            elif intensity is not None:
                raise QuantificationError("missing intensity must be null")
            normalized = {
                "run_id": run_id,
                "protein_accession": protein,
                "intensity": float(intensity) if intensity is not None else None,
                "observed": observed,
                "is_contaminant": contaminant,
            }
            rows.append(normalized)
            proteins.add(protein)
            seen.add((run_id, protein))
        if not rows:
            raise QuantificationError("quantification fixture has no intensity rows")
        return rows, proteins

    @staticmethod
    def _matrix(
        rows: Sequence[Mapping[str, Any]],
        runs: Sequence[Mapping[str, Any]],
        *,
        factors: Mapping[str, float],
    ) -> list[dict[str, Any]]:
        by_protein: dict[str, dict[str, Any]] = {}
        for row in rows:
            protein = str(row["protein_accession"])
            record = by_protein.setdefault(
                protein,
                {
                    "protein_accession": protein,
                    "is_contaminant": bool(row["is_contaminant"]),
                    "values": {},
                    "observed": {},
                },
            )
            run_id = str(row["run_id"])
            value = row["intensity"]
            record["values"][run_id] = (
                round(float(value) / factors[run_id], 8) if value is not None else None
            )
            record["observed"][run_id] = bool(row["observed"])
        run_ids = [str(run["run_id"]) for run in runs]
        for record in by_protein.values():
            for run_id in run_ids:
                record["values"].setdefault(run_id, None)
                record["observed"].setdefault(run_id, False)
        return sorted(by_protein.values(), key=lambda record: record["protein_accession"])

    def _groups(
        self, data: Mapping[str, Any], proteins: set[str], accepted_proteins: set[str]
    ) -> tuple[list[dict[str, Any]], int]:
        groups: list[dict[str, Any]] = []
        seen: set[str] = set()
        contaminants = 0
        for value in cast(list[Any], data["protein_groups"]):
            row = _mapping(value, "protein group")
            group_id = _string(row.get("group_id"), "protein group_id")
            members_value = row.get("members")
            if group_id in seen or not isinstance(members_value, list) or not members_value:
                raise QuantificationError("protein group is duplicated or has no members")
            members = [_string(member, "protein group member") for member in members_value]
            is_contaminant = row.get("is_contaminant")
            if not isinstance(is_contaminant, bool):
                raise QuantificationError("protein group is_contaminant must be boolean")
            if is_contaminant:
                contaminants += 1
            elif not set(members).issubset(accepted_proteins):
                raise QuantificationError("quantifiable group contains an unaccepted protein")
            if not set(members).issubset(proteins | accepted_proteins):
                raise QuantificationError("protein group member has no declared intensity/evidence")
            unique_peptides = row.get("unique_peptides", [])
            shared_peptides = row.get("shared_peptides", [])
            if not isinstance(unique_peptides, list) or not isinstance(shared_peptides, list):
                raise QuantificationError("protein group peptide fields must be lists")
            groups.append(
                {
                    "group_id": group_id,
                    "members": sorted(members),
                    "unique_peptides": sorted(str(item) for item in unique_peptides),
                    "shared_peptides": sorted(str(item) for item in shared_peptides),
                    "is_contaminant": is_contaminant,
                    "quantifiable": bool(row.get("quantifiable", not shared_peptides)),
                }
            )
            seen.add(group_id)
        if not groups:
            raise QuantificationError("protein group table is empty")
        return sorted(groups, key=lambda row: row["group_id"]), contaminants

    @staticmethod
    def _ratio_recovery(
        expected: Sequence[Mapping[str, Any]],
        matrix: Sequence[Mapping[str, Any]],
        samples: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        by_protein = {str(row["protein_accession"]): row for row in matrix}
        sample_conditions: dict[str, list[str]] = {}
        for sample in samples:
            sample_conditions.setdefault(str(sample["condition"]), []).append(str(sample["run_id"]))
        results: list[dict[str, Any]] = []
        for value in expected:
            row = _mapping(value, "expected ratio")
            protein = _string(row.get("protein_accession"), "expected ratio protein")
            numerator = _string(row.get("numerator_condition"), "expected ratio numerator")
            denominator = _string(row.get("denominator_condition"), "expected ratio denominator")
            expected_ratio = _float(row.get("expected_ratio"), "expected ratio value")
            tolerance = _float(row.get("tolerance"), "expected ratio tolerance")
            protein_row = by_protein.get(protein)
            if protein_row is None:
                raise QuantificationError(f"expected ratio protein is missing: {protein}")
            numerator_values = [
                float(protein_row["values"][run_id])
                for run_id in sample_conditions.get(numerator, [])
                if protein_row["values"].get(run_id) is not None
            ]
            denominator_values = [
                float(protein_row["values"][run_id])
                for run_id in sample_conditions.get(denominator, [])
                if protein_row["values"].get(run_id) is not None
            ]
            if not numerator_values or not denominator_values:
                raise QuantificationError(
                    f"expected ratio has insufficient observations: {protein}"
                )
            observed_ratio = round(_median(numerator_values) / _median(denominator_values), 8)
            results.append(
                {
                    "protein_accession": protein,
                    "numerator_condition": numerator,
                    "denominator_condition": denominator,
                    "expected_ratio": expected_ratio,
                    "observed_ratio": observed_ratio,
                    "tolerance": tolerance,
                    "passed": abs(observed_ratio - expected_ratio) <= tolerance,
                    "numerator_observations": len(numerator_values),
                    "denominator_observations": len(denominator_values),
                }
            )
        passed = sum(bool(row["passed"]) for row in results)
        return {
            "schema_version": 1,
            "method": "median_of_normalized_observed_intensities",
            "results": results,
            "passed": passed == len(results) and bool(results),
            "passed_count": passed,
            "total_count": len(results),
        }

    @staticmethod
    def _write_json(path: Path, value: Any) -> bytes:
        payload = _canonical(value)
        path.write_bytes(payload)
        return payload

    def run(self, *, fixture: bool = False) -> QuantificationSummary:
        """Run LFQ and resume identical outputs."""
        if not fixture:
            raise QuantificationError("--fixture is required for the bounded LFQ workflow")
        data = self._load_fixture()
        accepted_proteins = self._verify_search(data)
        samples, runs = self._load_samples(data)
        intensities, intensity_proteins = self._load_intensities(data, runs, accepted_proteins)
        groups, contaminant_groups = self._groups(data, intensity_proteins, accepted_proteins)
        primary_factors = {
            run_id: float(row["normalization_factor"]) for run_id, row in runs.items()
        }
        raw_factors = {run_id: 1.0 for run_id in runs}
        raw_matrix = self._matrix(intensities, samples, factors=raw_factors)
        normalized_matrix = self._matrix(intensities, samples, factors=primary_factors)
        non_contaminant = [row for row in raw_matrix if not row["is_contaminant"]]
        run_medians = {
            run_id: _median(
                [
                    float(row["values"][run_id])
                    for row in non_contaminant
                    if row["values"].get(run_id) is not None
                ]
            )
            for run_id in runs
        }
        reference_median = _median(list(run_medians.values()))
        median_centering_factors = {
            run_id: round(median / reference_median, 8) for run_id, median in run_medians.items()
        }
        median_centered_matrix = self._matrix(
            intensities, samples, factors=median_centering_factors
        )
        ratios = self._ratio_recovery(
            cast(list[Any], data["expected_ratios"]), normalized_matrix, samples
        )
        if not ratios["passed"]:
            raise QuantificationError("synthetic ratio recovery failed")
        missing_rows = [row for row in normalized_matrix if not row["is_contaminant"]]
        missing_by_protein = {
            str(row["protein_accession"]): sum(value is None for value in row["values"].values())
            for row in missing_rows
        }
        missing_by_run = {
            str(run["run_id"]): sum(
                row["values"].get(run["run_id"]) is None for row in missing_rows
            )
            for run in samples
        }
        missing_total = sum(missing_by_protein.values())
        resume_material = {
            "samples": samples,
            "intensities": intensities,
            "groups": groups,
            "primary_factors": primary_factors,
            "ratios": ratios,
        }
        resume_key = _sha256_bytes(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "samples": self.output_root / "sample_manifest.json",
            "raw": self.output_root / "raw_matrix.json",
            "normalized": self.output_root / "normalized_matrix.json",
            "median_centered": self.output_root / "median_centered_matrix.json",
            "groups": self.output_root / "protein_groups.json",
            "missingness": self.output_root / "missingness_report.json",
            "qc": self.output_root / "quantification_qc.json",
            "ratios": self.output_root / "ratio_recovery.json",
            "receipt": self.output_root / "quantification_receipt.json",
            "log": self.output_root / "quantification_log.json",
            "manifest": self.output_root / "quantification_manifest.json",
        }
        raw_payloads = {
            "samples": {"schema_version": 1, "runs": samples, "resume_key": resume_key},
            "raw": {"schema_version": 1, "method": "raw_observed_intensity", "rows": raw_matrix},
            "normalized": {
                "schema_version": 1,
                "method": "declared_run_scaling",
                "run_factors": primary_factors,
                "rows": normalized_matrix,
            },
            "median_centered": {
                "schema_version": 1,
                "method": "median_centering_comparison",
                "run_factors": median_centering_factors,
                "rows": median_centered_matrix,
            },
            "groups": {"schema_version": 1, "groups": groups},
            "missingness": {
                "schema_version": 1,
                "missing_cells": missing_total,
                "by_protein": missing_by_protein,
                "by_run": missing_by_run,
                "no_imputation": True,
            },
            "qc": {
                "schema_version": 1,
                "primary_normalization": "declared_run_scaling",
                "comparison_normalization": "median_centering",
                "run_medians": run_medians,
                "reference_median": reference_median,
                "contaminant_groups": contaminant_groups,
                "quantifiable_proteins": len(non_contaminant),
                "replicate_counts": {
                    condition: len(
                        {
                            run["biological_replicate"]
                            for run in samples
                            if run["condition"] == condition
                        }
                    )
                    for condition in sorted({run["condition"] for run in samples})
                },
            },
            "ratios": {**ratios, "resume_key": resume_key},
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root))
                if path.is_relative_to(self.root)
                else str(path),
                "sha256": _sha256_bytes(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "input_search_receipt": "reports/omics/search/search_receipt.json",
            "normalization": {
                "primary": "declared_run_scaling",
                "comparison": "median_centering",
                "no_imputation": True,
            },
            "replicates": {
                "runs": len(samples),
                "sample_ids": sorted({run["sample_id"] for run in samples}),
                "biological_replicates": sorted({run["biological_replicate"] for run in samples}),
            },
            "protein_inference": {
                "groups": len(groups),
                "quantifiable_proteins": len(non_contaminant),
                "contaminant_groups": contaminant_groups,
                "ambiguous_groups": sum(
                    not bool(group["quantifiable"]) and not bool(group["is_contaminant"])
                    for group in groups
                ),
            },
            "missingness": {"missing_cells": missing_total, "no_imputation": True},
            "ratios": ratios,
            "raw_downloaded": False,
            "locked_payload_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "search_input_verified", "path": receipt["input_search_receipt"]},
                {"event": "replicates_validated", "runs": len(samples)},
                {
                    "event": "normalization_compared",
                    "routes": ["declared_run_scaling", "median_centering"],
                },
                {"event": "protein_groups_inferred", "groups": len(groups)},
                {"event": "ratio_recovery_verified", "passed": True},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "runs": len(samples),
            "samples": len({run["sample_id"] for run in samples}),
            "quantifiable_proteins": len(non_contaminant),
            "groups": len(groups),
            "missing_cells": missing_total,
            "ratios_passed": ratios["passed_count"],
            "ratios_total": ratios["total_count"],
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path),
                    "sha256": _sha256_bytes(payload_bytes[name]),
                    "bytes": len(payload_bytes[name]),
                }
                for name, path in paths.items()
                if name in payload_bytes
            },
        }
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise QuantificationError("existing quantification receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise QuantificationError(f"existing quantification artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return QuantificationSummary(
            runs=len(samples),
            samples=len({run["sample_id"] for run in samples}),
            quantifiable_proteins=len(non_contaminant),
            groups=len(groups),
            missing_cells=missing_total,
            contaminant_groups=contaminant_groups,
            ratios_passed=int(ratios["passed_count"]),
            ratios_total=int(ratios["total_count"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
