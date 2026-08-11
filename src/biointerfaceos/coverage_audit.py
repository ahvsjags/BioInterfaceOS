"""Fixture-backed data coverage and missingness audit."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

COVERAGE_FIXTURE = Path("tests/fixtures/coverage/data_coverage.json")
COVERAGE_ROOT = Path("reports/data_coverage")
SILVER_RELEASE = Path("release/silver/bioif-silver-b05bdbc371d43cae")


class DataCoverageError(RuntimeError):
    """Raised when coverage inputs violate the audit contract."""


@dataclass(frozen=True)
class CoverageSummary:
    """Summary and output paths from one coverage audit."""

    independent_studies: int
    admitted_candidates: int
    represented_candidates: int
    missing_values: int
    gaps: int
    bias_warnings: int
    coverage_path: Path
    missingness_path: Path
    warnings_path: Path
    receipt_path: Path


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DataCoverageError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DataCoverageError(f"JSON object required: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise DataCoverageError(f"cannot read JSONL {path}: {exc}") from exc
    records: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DataCoverageError(f"invalid JSONL {path} line {number}") from exc
        if not isinstance(value, Mapping):
            raise DataCoverageError(f"JSONL object required at {path}:{number}")
        records.append(dict(value))
    return records


def _load_silver(root: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], set[str]]:
    table_root = root / SILVER_RELEASE / "tables"
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    locators: set[str] = set()
    for path in sorted(table_root.glob("*.parquet")):
        try:
            table = pq.read_table(path)
        except (OSError, ValueError) as exc:
            raise DataCoverageError(f"cannot read Silver table {path}: {exc}") from exc
        for raw in table.to_pylist():
            row = dict(raw)
            primary_key = row.get("primary_key")
            source_locator = row.get("source_locator")
            evidence_locators = row.get("evidence_locators")
            if not isinstance(primary_key, str) or not isinstance(source_locator, str):
                raise DataCoverageError(f"Silver row identity is invalid: {path}")
            if not isinstance(evidence_locators, str):
                raise DataCoverageError(f"Silver evidence locators are invalid: {path}")
            try:
                locator_values = json.loads(evidence_locators)
            except json.JSONDecodeError as exc:
                raise DataCoverageError(f"Silver evidence JSON is invalid: {path}") from exc
            if not isinstance(locator_values, list) or not all(
                isinstance(locator, str) for locator in locator_values
            ):
                raise DataCoverageError(f"Silver evidence locator list is invalid: {path}")
            row["table"] = path.stem
            rows[(path.stem, primary_key)] = row
            locators.add(source_locator)
            locators.update(locator_values)
    if not rows:
        raise DataCoverageError("Silver release contains no parquet rows")
    return rows, locators


def _evidence_status(status: str) -> str:
    if status in {"NORMALIZED", "RESOLVED", "VALID"}:
        return "USABLE"
    if status == "REVIEW_REQUIRED":
        return "REVIEW_REQUIRED"
    return "UNUSABLE"


def _axis_values(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    counts: Counter[str] = Counter()
    for record in records:
        value = record.get(key)
        label = "__MISSING__" if value is None else str(value)
        counts[label] += 1
    total = len(records)
    return {
        label: {
            "independent_studies": count,
            "share": count / total if total else 0.0,
        }
        for label, count in sorted(counts.items())
    }


def _missingness_model(records: list[dict[str, Any]]) -> dict[str, Any]:
    fields = (
        "lab",
        "material",
        "species",
        "endpoint",
        "publication_year",
        "evidence_locators",
    )
    overall: dict[str, dict[str, Any]] = {}
    for field in fields:
        missing_ids = [
            str(record["study_id"]) for record in records if record.get(field) in (None, [], "")
        ]
        overall[field] = {
            "missing_count": len(missing_ids),
            "missing_rate": len(missing_ids) / len(records) if records else 0.0,
            "missing_study_ids": missing_ids,
        }
    predictors: dict[str, dict[str, Any]] = {}
    for predictor in ("source", "silver_status", "search_scope"):
        groups: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            groups.setdefault(str(record[predictor]), []).append(record)
        predictor_groups: dict[str, Any] = {}
        for group, members in sorted(groups.items()):
            predictor_groups[group] = {
                "independent_studies": len(members),
                "missingness": {
                    field: {
                        "missing_count": sum(
                            member.get(field) in (None, [], "") for member in members
                        ),
                        "missing_rate": sum(
                            member.get(field) in (None, [], "") for member in members
                        )
                        / len(members),
                    }
                    for field in fields
                },
            }
        predictors[predictor] = predictor_groups
    return {
        "schema_version": 1,
        "independent_unit": "study_id",
        "independent_studies": len(records),
        "overall": overall,
        "predictor_profiles": predictors,
        "method": "descriptive group-wise missingness rates; no causal inference or imputation",
        "no_imputation": True,
    }


class DataCoverageAuditor:
    """Audit independent-study coverage using Silver rows and search receipts."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / COVERAGE_FIXTURE
        self.output_root = output_root or self.root / COVERAGE_ROOT

    def _load_fixture(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        value = _read_json(self.fixture_path)
        required = {"schema_version", "independent_unit", "expected_axes", "records"}
        if set(value) != required or value.get("schema_version") != 1:
            raise DataCoverageError("coverage fixture envelope is invalid")
        if value.get("independent_unit") != "study_id":
            raise DataCoverageError("coverage fixture must use study_id as independent unit")
        expected_axes = value.get("expected_axes")
        records = value.get("records")
        if not isinstance(expected_axes, Mapping) or not isinstance(records, list):
            raise DataCoverageError("coverage fixture schema is invalid")
        if not expected_axes or not all(
            isinstance(key, str) and isinstance(axis_values, list) and axis_values
            for key, axis_values in expected_axes.items()
        ):
            raise DataCoverageError("coverage fixture expected axes are invalid")
        fields = {
            "study_id",
            "sample_key",
            "candidate_accession",
            "source",
            "lab",
            "material",
            "species",
            "endpoint",
            "publication_year",
            "silver_table",
            "silver_primary_key",
            "evidence_locators",
        }
        normalized: list[dict[str, Any]] = []
        for raw in records:
            if not isinstance(raw, Mapping) or set(raw) != fields:
                raise DataCoverageError("coverage fixture record fields are invalid")
            row = dict(raw)
            if (
                not isinstance(row["study_id"], str)
                or not isinstance(row["sample_key"], str)
                or not isinstance(row["candidate_accession"], str)
                or not isinstance(row["source"], str)
                or row["lab"] is not None
                and not isinstance(row["lab"], str)
                or row["material"] not in expected_axes["material"]
                or row["species"] is not None
                and not isinstance(row["species"], str)
                or row["endpoint"] not in expected_axes["endpoint"]
                or row["publication_year"] is not None
                and not isinstance(row["publication_year"], int)
                or not isinstance(row["silver_table"], str)
                or not isinstance(row["silver_primary_key"], str)
                or not isinstance(row["evidence_locators"], list)
                or not row["evidence_locators"]
                or not all(isinstance(locator, str) for locator in row["evidence_locators"])
            ):
                raise DataCoverageError(f"coverage fixture record values are invalid: {row}")
            normalized.append(row)
        if not normalized or len({row["study_id"] for row in normalized}) != len(normalized):
            raise DataCoverageError("coverage fixture study IDs are not unique")
        if len({row["sample_key"] for row in normalized}) != len(normalized):
            raise DataCoverageError("coverage fixture sample keys are not unique")
        return dict(value), normalized

    def run(self) -> CoverageSummary:
        """Build coverage tables, missingness profiles, warnings, and a receipt."""
        fixture, fixture_records = self._load_fixture()
        silver_rows, silver_locators = _load_silver(self.root)
        candidates = _read_jsonl(self.root / "registry/search_candidates.jsonl")
        candidate_by_accession: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            accession = candidate.get("accession")
            if not isinstance(accession, str) or not accession:
                raise DataCoverageError("search candidate accession is invalid")
            if accession in candidate_by_accession:
                raise DataCoverageError(f"duplicate search accession: {accession}")
            candidate_by_accession[accession] = candidate
        admitted_accessions = {
            accession
            for accession, candidate_row in candidate_by_accession.items()
            if candidate_row.get("decision") == "ADMIT_PUBLIC_REDISTRIBUTABLE"
        }
        represented_accessions: set[str] = set()
        records: list[dict[str, Any]] = []
        for row in fixture_records:
            accession = str(row["candidate_accession"])
            candidate_row = candidate_by_accession.get(accession)
            if candidate_row is None:
                raise DataCoverageError(
                    f"study candidate is absent from search registry: {accession}"
                )
            if candidate_row.get("decision") != "ADMIT_PUBLIC_REDISTRIBUTABLE":
                raise DataCoverageError(f"study candidate is not admitted: {accession}")
            represented_accessions.add(accession)
            silver_key = (str(row["silver_table"]), str(row["silver_primary_key"]))
            silver = silver_rows.get(silver_key)
            if silver is None:
                raise DataCoverageError(f"Silver row is absent: {silver_key}")
            locators = set(str(locator) for locator in row["evidence_locators"])
            if not locators <= silver_locators:
                missing = sorted(locators - silver_locators)
                raise DataCoverageError(f"evidence locators are absent from Silver: {missing}")
            silver_status = silver.get("status")
            if not isinstance(silver_status, str):
                raise DataCoverageError(f"Silver status is invalid: {silver_key}")
            scopes = candidate_row.get("scopes")
            search_scope = str(scopes[0]) if isinstance(scopes, list) and scopes else "__MISSING__"
            enriched = dict(row)
            enriched["silver_status"] = silver_status
            enriched["evidence_status"] = _evidence_status(silver_status)
            enriched["search_scope"] = search_scope
            records.append(enriched)

        expected_axes = dict(fixture["expected_axes"])
        axis_fields = {
            "study": "study_id",
            "lab": "lab",
            "material": "material",
            "species": "species",
            "endpoint": "endpoint",
            "date": "publication_year",
            "evidence": "evidence_status",
        }
        coverage: dict[str, Any] = {}
        for axis, field in axis_fields.items():
            coverage[axis] = {
                "expected": expected_axes.get(axis, []),
                "observed": _axis_values(records, field),
            }

        gaps: list[dict[str, Any]] = []
        for axis, expected in expected_axes.items():
            field_name = axis_fields.get(axis)
            if field_name is None:
                raise DataCoverageError(f"unsupported expected axis: {axis}")
            observed = {
                label for label in _axis_values(records, field_name) if label != "__MISSING__"
            }
            for value in expected:
                label = str(value)
                if label not in observed:
                    gaps.append(
                        {
                            "gap_id": f"{axis}:{label}",
                            "dimension": axis,
                            "missing_value": value,
                            "priority": (
                                "HIGH" if axis in {"material", "endpoint", "date"} else "MEDIUM"
                            ),
                            "action": "targeted_search_or_scope_reduction",
                            "no_pseudo_replicates": True,
                        }
                    )

        missingness = _missingness_model(records)
        warnings: list[dict[str, Any]] = []
        overall = missingness["overall"]
        for field, code, severity in (
            ("lab", "MISSING_LAB", "MEDIUM"),
            ("species", "MISSING_SPECIES", "MEDIUM"),
            ("publication_year", "MISSING_DATE", "MEDIUM"),
        ):
            missing_ids = overall[field]["missing_study_ids"]
            if missing_ids:
                warnings.append(
                    {
                        "warning_id": code,
                        "severity": severity,
                        "reason": f"{field} is absent for independent studies",
                        "affected_study_ids": missing_ids,
                        "action": "report_missingness_and_target_search",
                    }
                )
        for gap in gaps:
            warnings.append(
                {
                    "warning_id": f"COVERAGE_GAP:{gap['gap_id']}",
                    "severity": gap["priority"],
                    "reason": f"expected {gap['dimension']} value is not represented",
                    "affected_study_ids": [],
                    "gap_id": gap["gap_id"],
                    "action": gap["action"],
                }
            )
        if len(represented_accessions) < len(admitted_accessions):
            warnings.append(
                {
                    "warning_id": "SEARCH_CANDIDATE_COVERAGE",
                    "severity": "HIGH",
                    "reason": (
                        "admitted search candidates are not all represented by "
                        "independent study rows"
                    ),
                    "affected_study_ids": [],
                    "unrepresented_admitted_candidates": sorted(
                        admitted_accessions - represented_accessions
                    ),
                    "action": "resolve study identity or trigger targeted search",
                }
            )
        review_studies = [
            str(record["study_id"]) for record in records if record["evidence_status"] != "USABLE"
        ]
        if review_studies:
            warnings.append(
                {
                    "warning_id": "SILVER_REVIEW_ROWS",
                    "severity": "MEDIUM",
                    "reason": "coverage includes Silver rows that are not fully normalized",
                    "affected_study_ids": review_studies,
                    "action": "retain in review and do not promote automatically",
                }
            )

        manifest = _read_json(self.root / SILVER_RELEASE / "silver_manifest.json")
        release_id = SILVER_RELEASE.name
        registry_summary = {
            "candidate_rows": len(candidates),
            "unique_candidate_ids": len({str(row.get("candidate_id")) for row in candidates}),
            "unique_accessions": len(candidate_by_accession),
            "decision_counts": dict(
                sorted(Counter(str(row.get("decision")) for row in candidates).items())
            ),
            "admitted_candidates": len(admitted_accessions),
            "represented_admitted_candidates": len(represented_accessions),
            "unrepresented_admitted_candidates": sorted(
                admitted_accessions - represented_accessions
            ),
            "candidate_rows_are_not_independent_study_units": True,
        }
        coverage_report = {
            "schema_version": 1,
            "fixture": True,
            "independent_unit": "study_id",
            "independent_studies": len(records),
            "silver_release_id": release_id,
            "silver_manifest_hash": manifest.get("manifest_hash"),
            "search_registry": registry_summary,
            "coverage": coverage,
            "gaps": gaps,
            "no_imputation": True,
            "locked_test_accessed": False,
        }
        warnings_report = {
            "schema_version": 1,
            "warnings": warnings,
            "warning_count": len(warnings),
            "gap_count": len(gaps),
            "bias_interpretation": (
                "Warnings describe representation and missingness risks; "
                "they are not causal estimates."
            ),
            "no_imputation": True,
            "locked_test_accessed": False,
        }
        coverage_tables = {
            "schema_version": 1,
            "independent_unit": "study_id",
            "tables": coverage,
            "no_imputation": True,
        }
        input_hashes = {
            "coverage_fixture": _sha256(self.fixture_path.read_bytes()),
            "silver_manifest": _sha256(
                (self.root / SILVER_RELEASE / "silver_manifest.json").read_bytes()
            ),
            "search_registry": _sha256(
                (self.root / "registry/search_candidates.jsonl").read_bytes()
            ),
        }
        self.output_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "coverage_tables.json": coverage_tables,
            "coverage_report.json": coverage_report,
            "missingness_model.json": missingness,
            "bias_warnings.json": warnings_report,
        }
        serialized = {name: _canonical(value) for name, value in outputs.items()}
        receipt = {
            "schema_version": 1,
            "fixture": True,
            "independent_unit": "study_id",
            "independent_studies": len(records),
            "silver_release_id": release_id,
            "input_sha256": input_hashes,
            "output_sha256": {name: _sha256(content) for name, content in serialized.items()},
            "gap_count": len(gaps),
            "warning_count": len(warnings),
            "no_imputation": True,
            "locked_test_accessed": False,
        }
        serialized["data_coverage_receipt.json"] = _canonical(receipt)
        for name, content in serialized.items():
            (self.output_root / name).write_bytes(content)
        return CoverageSummary(
            independent_studies=len(records),
            admitted_candidates=len(admitted_accessions),
            represented_candidates=len(represented_accessions),
            missing_values=sum(
                int(details["missing_count"]) for details in missingness["overall"].values()
            ),
            gaps=len(gaps),
            bias_warnings=len(warnings),
            coverage_path=self.output_root / "coverage_report.json",
            missingness_path=self.output_root / "missingness_model.json",
            warnings_path=self.output_root / "bias_warnings.json",
            receipt_path=self.output_root / "data_coverage_receipt.json",
        )
