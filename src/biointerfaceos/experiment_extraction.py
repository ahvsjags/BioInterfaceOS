"""Offline dual-path structured experiment extraction."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class DualExtractionError(ValueError):
    """Raised when a dual-path experiment fixture violates its contract."""


@dataclass(frozen=True)
class FieldAssertion:
    """One path-specific field assertion with evidence."""

    record_id: str
    field_name: str
    value: Any
    value_type: str
    unit: str | None
    evidence_locators: tuple[str, ...]
    confidence: float
    path: str


@dataclass(frozen=True)
class PathOutput:
    """One normalized output path."""

    path: str
    backend: str
    schema_version: int
    fields: tuple[FieldAssertion, ...]


@dataclass(frozen=True)
class ConsensusField:
    """Field-level comparison and acceptance state."""

    record_id: str
    field_name: str
    status: str
    accepted_value: Any
    accepted_unit: str | None
    source_paths: tuple[str, ...]
    evidence_locators: tuple[str, ...]
    confidence: float
    review_id: str | None


@dataclass(frozen=True)
class DualExtractionSummary:
    """Counts and output paths from one fixture run."""

    records: int
    rule_fields: int
    mock_fields: int
    agreements: int
    disagreements: int
    accepted_fields: int
    review_items: int
    candidates_path: Path
    consensus_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _value_equal(left: FieldAssertion, right: FieldAssertion) -> bool:
    return (
        left.value_type == right.value_type
        and left.unit == right.unit
        and left.value == right.value
    )


class DualExperimentExtractor:
    """Compare deterministic and offline-mock paths without private APIs."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        candidates_path: Path | None = None,
        consensus_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/extract/dual_experiment.json"
        )
        self.candidates_path = candidates_path or (
            self.root / "registry/experiment_candidates.json"
        )
        self.consensus_path = consensus_path or (self.root / "registry/experiment_consensus.json")
        self.review_path = review_path or (self.root / "registry/consensus_review_queue.jsonl")
        self.report_path = report_path or self.root / "reports/dual_extraction.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DualExtractionError(f"cannot load dual extraction fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "records"}:
            raise DualExtractionError("dual extraction fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["records"], list):
            raise DualExtractionError("dual extraction fixture schema is invalid")
        records: list[dict[str, Any]] = []
        for raw_record in value["records"]:
            if not isinstance(raw_record, Mapping) or set(raw_record) != {
                "record_id",
                "source_asset_id",
                "rule_fields",
                "mock_fields",
            }:
                raise DualExtractionError("dual extraction record fields are invalid")
            if not isinstance(raw_record["rule_fields"], list) or not isinstance(
                raw_record["mock_fields"], list
            ):
                raise DualExtractionError("dual extraction paths must be lists")
            records.append(dict(raw_record))
        return records

    @staticmethod
    def _field(
        record_id: str,
        path: str,
        raw: Mapping[str, Any],
    ) -> FieldAssertion:
        if set(raw) != {
            "field_name",
            "value",
            "value_type",
            "unit",
            "evidence_locators",
            "confidence",
        }:
            raise DualExtractionError(f"{path} field schema is invalid")
        field_name = _text(raw["field_name"])
        value_type = _text(raw["value_type"]).lower()
        unit = None if raw["unit"] is None else _text(raw["unit"])
        locators = raw["evidence_locators"]
        if not field_name or value_type not in {"string", "integer", "number"}:
            raise DualExtractionError(f"{path} field name or type is invalid")
        if not isinstance(locators, list) or not locators:
            raise DualExtractionError(f"{path}.{field_name} requires evidence locators")
        normalized_locators = tuple(_text(locator) for locator in locators)
        if any(not locator.startswith("asset:") for locator in normalized_locators):
            raise DualExtractionError(f"{path}.{field_name} has an invalid evidence locator")
        value = raw["value"]
        if value_type == "string" and not isinstance(value, str):
            raise DualExtractionError(f"{path}.{field_name} must be a string")
        if value_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            raise DualExtractionError(f"{path}.{field_name} must be an integer")
        if value_type == "number" and (
            isinstance(value, bool) or not isinstance(value, int | float)
        ):
            raise DualExtractionError(f"{path}.{field_name} must be numeric")
        try:
            confidence = float(raw["confidence"])
        except (TypeError, ValueError) as exc:
            raise DualExtractionError(f"{path}.{field_name} confidence is invalid") from exc
        if not 0.0 <= confidence <= 1.0:
            raise DualExtractionError(f"{path}.{field_name} confidence is out of range")
        return FieldAssertion(
            record_id=record_id,
            field_name=field_name,
            value=value,
            value_type=value_type,
            unit=unit,
            evidence_locators=normalized_locators,
            confidence=confidence,
            path=path,
        )

    def _path(
        self,
        record_id: str,
        raw_fields: Any,
        *,
        path: str,
        backend: str,
    ) -> PathOutput:
        if not isinstance(raw_fields, list):
            raise DualExtractionError(f"{path} fields must be a list")
        fields = tuple(
            self._field(record_id, path, raw_field)
            for raw_field in raw_fields
            if isinstance(raw_field, Mapping)
        )
        if len(fields) != len(raw_fields):
            raise DualExtractionError(f"{path} contains a non-object field")
        names = [field.field_name for field in fields]
        if len(set(names)) != len(names):
            raise DualExtractionError(f"{path} contains duplicate field names")
        return PathOutput(path, backend, 1, fields)

    @staticmethod
    def _consensus(
        record_id: str,
        rule: PathOutput,
        mock: PathOutput,
    ) -> tuple[tuple[ConsensusField, ...], list[dict[str, Any]]]:
        rule_by_name = {field.field_name: field for field in rule.fields}
        mock_by_name = {field.field_name: field for field in mock.fields}
        if set(rule_by_name) != set(mock_by_name):
            raise DualExtractionError("dual paths do not expose the same field schema")
        consensus: list[ConsensusField] = []
        reviews: list[dict[str, Any]] = []
        for field_name in sorted(rule_by_name):
            left = rule_by_name[field_name]
            right = mock_by_name[field_name]
            locators = tuple(dict.fromkeys(left.evidence_locators + right.evidence_locators))
            if _value_equal(left, right):
                consensus.append(
                    ConsensusField(
                        record_id=record_id,
                        field_name=field_name,
                        status="AGREED",
                        accepted_value=left.value,
                        accepted_unit=left.unit,
                        source_paths=(left.path, right.path),
                        evidence_locators=locators,
                        confidence=min(left.confidence, right.confidence),
                        review_id=None,
                    )
                )
                continue
            review_id = f"field-disagreement:{record_id}:{field_name}"
            review = {
                "review_id": review_id,
                "reason": "DUAL_PATH_FIELD_DISAGREEMENT",
                "record_id": record_id,
                "field_name": field_name,
                "rule_value": left.value,
                "mock_value": right.value,
                "rule_unit": left.unit,
                "mock_unit": right.unit,
                "evidence_locators": list(locators),
                "resolution": "MANUAL_REVIEW",
            }
            reviews.append(review)
            consensus.append(
                ConsensusField(
                    record_id=record_id,
                    field_name=field_name,
                    status="REVIEW_REQUIRED",
                    accepted_value=None,
                    accepted_unit=None,
                    source_paths=(left.path, right.path),
                    evidence_locators=locators,
                    confidence=min(left.confidence, right.confidence),
                    review_id=review_id,
                )
            )
        return tuple(consensus), reviews

    def run(self) -> DualExtractionSummary:
        """Run both offline paths and write candidates, consensus, and review records."""
        records = self._load_fixture(self.fixture_path)
        candidate_records: list[dict[str, Any]] = []
        consensus_records: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []
        rule_fields = 0
        mock_fields = 0
        agreements = 0
        disagreements = 0
        accepted_fields = 0
        for raw_record in records:
            record_id = _text(raw_record["record_id"])
            source_asset_id = _text(raw_record["source_asset_id"])
            if not record_id or not source_asset_id:
                raise DualExtractionError("record_id and source_asset_id are required")
            rule = self._path(
                record_id,
                raw_record["rule_fields"],
                path="rule",
                backend="deterministic_rules",
            )
            mock = self._path(
                record_id,
                raw_record["mock_fields"],
                path="mock",
                backend="offline_fixture_mock",
            )
            consensus, record_reviews = self._consensus(record_id, rule, mock)
            rule_fields += len(rule.fields)
            mock_fields += len(mock.fields)
            agreements += sum(item.status == "AGREED" for item in consensus)
            disagreements += sum(item.status == "REVIEW_REQUIRED" for item in consensus)
            accepted_fields += sum(item.accepted_value is not None for item in consensus)
            reviews.extend(record_reviews)
            candidate_records.append(
                {
                    "record_id": record_id,
                    "source_asset_id": source_asset_id,
                    "rule_path": asdict(rule),
                    "mock_path": asdict(mock),
                    "schema_equal": True,
                    "network_accessed": False,
                }
            )
            consensus_records.append(
                {
                    "record_id": record_id,
                    "source_asset_id": source_asset_id,
                    "fields": [asdict(item) for item in consensus],
                }
            )

        candidates = {
            "schema_version": 1,
            "fixture": True,
            "paths": ["rule", "mock"],
            "records": candidate_records,
        }
        consensus_payload = {
            "schema_version": 1,
            "fixture": True,
            "records": consensus_records,
            "summary": {
                "records": len(records),
                "agreements": agreements,
                "disagreements": disagreements,
                "accepted_fields": accepted_fields,
                "review_items": len(reviews),
            },
        }
        self.candidates_path.parent.mkdir(parents=True, exist_ok=True)
        self.candidates_path.write_text(
            json.dumps(candidates, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.consensus_path.parent.mkdir(parents=True, exist_ok=True)
        self.consensus_path.write_text(
            json.dumps(consensus_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        review_ledger = AppendOnlyJSONL(self.review_path)
        review_ledger.initialize()
        existing = {
            json.loads(line).get("review_id")
            for line in review_ledger.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for review in reviews:
            if review["review_id"] not in existing:
                review_ledger.append(review)

        report = (
            "\n".join(
                [
                    "# Dual-Path Experiment Extraction Report",
                    "",
                    "Both paths are offline and emit the same versioned field schema.",
                    "",
                    f"- records: {len(records)}",
                    f"- rule fields: {rule_fields}",
                    f"- mock fields: {mock_fields}",
                    f"- agreements: {agreements}",
                    f"- disagreements: {disagreements}",
                    f"- accepted fields: {accepted_fields}",
                    f"- review items: {len(reviews)}",
                    "",
                    "Every field carries one or more asset locators. Disagreements retain "
                    "both values and are not accepted into consensus.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return DualExtractionSummary(
            records=len(records),
            rule_fields=rule_fields,
            mock_fields=mock_fields,
            agreements=agreements,
            disagreements=disagreements,
            accepted_fields=accepted_fields,
            review_items=len(reviews),
            candidates_path=self.candidates_path,
            consensus_path=self.consensus_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
