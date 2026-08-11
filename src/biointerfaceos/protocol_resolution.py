"""Bioenvironment and protocol ontology normalization."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class ProtocolResolutionError(ValueError):
    """Raised when a protocol fixture violates its contract."""


@dataclass(frozen=True)
class ProtocolResolutionSummary:
    """Counts and output paths from one fixture run."""

    protocols: int
    fields: int
    observed_fields: int
    missing_fields: int
    clusters: int
    review_items: int
    protocols_path: Path
    clusters_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolResolutionError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ProtocolResolutionError(f"{name} must be finite")
    return result


class ProtocolResolver:
    """Normalize protocol fields and preserve missingness/severity features."""

    FIELD_TYPES = frozenset({"ontology", "quantity", "integer", "text"})
    ONTOLOGY = {
        "FBS": ("Fetal bovine serum", "NCIT:C120868"),
        "PBS": ("Phosphate-buffered saline", "CHEBI:48706"),
        "DLS": ("Dynamic light scattering", "OBI:0002091"),
        "TEM": ("Transmission electron microscopy", "OBI:0000185"),
    }

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        protocols_path: Path | None = None,
        clusters_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/protocols/protocol_resolution.json"
        )
        self.protocols_path = protocols_path or (self.root / "registry/protocol_entities.json")
        self.clusters_path = clusters_path or (self.root / "registry/protocol_clusters.json")
        self.review_path = review_path or (self.root / "registry/protocol_review_queue.jsonl")
        self.report_path = report_path or self.root / "reports/protocol_resolution.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolResolutionError(f"cannot load protocol fixture: {exc}") from exc
        if not isinstance(value, dict) or set(value) != {"schema_version", "protocols"}:
            raise ProtocolResolutionError("protocol fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["protocols"], list):
            raise ProtocolResolutionError("protocol fixture schema is invalid")
        protocols = [dict(item) for item in value["protocols"] if isinstance(item, dict)]
        if len(protocols) != len(value["protocols"]):
            raise ProtocolResolutionError("protocol fixture contains a non-object")
        return protocols

    def _normalize_field(
        self,
        protocol_id: str,
        raw: dict[str, Any],
        reviews: list[dict[str, Any]],
    ) -> dict[str, Any]:
        required = {
            "field_id",
            "name",
            "field_type",
            "raw_value",
            "raw_unit",
            "target_unit",
            "observed",
            "source_locator",
        }
        if set(raw) != required:
            raise ProtocolResolutionError("protocol field schema is invalid")
        field_id = _text(raw["field_id"])
        name = _text(raw["name"])
        field_type = _text(raw["field_type"]).lower()
        locator = _text(raw["source_locator"])
        observed = bool(raw["observed"])
        if (
            not field_id
            or not name
            or field_type not in self.FIELD_TYPES
            or not locator.startswith("asset:")
        ):
            raise ProtocolResolutionError(f"{protocol_id} field identifiers/type/locator invalid")
        raw_unit = None if raw["raw_unit"] is None else _text(raw["raw_unit"])
        target_unit = None if raw["target_unit"] is None else _text(raw["target_unit"])
        raw_value = raw["raw_value"]
        normalized_value: Any = None
        normalized_unit: str | None = None
        ontology_id: str | None = None
        status = "OBSERVED" if observed else "MISSING"
        reason: str | None = None
        if observed:
            if raw_value is None:
                raise ProtocolResolutionError(
                    f"{protocol_id}.{field_id} observed field has no value"
                )
            if field_type == "ontology":
                key = _text(raw_value).upper()
                if key not in self.ONTOLOGY:
                    status = "UNKNOWN"
                    reason = "ONTOLOGY_TERM_UNRESOLVED"
                else:
                    normalized_value, ontology_id = self.ONTOLOGY[key]
                    normalized_unit = None
            elif field_type == "quantity":
                value = _float(raw_value, f"{protocol_id}.{field_id}.raw_value")
                if raw_unit == "%" and target_unit == "fraction":
                    normalized_value, normalized_unit = value / 100.0, "fraction"
                elif raw_unit == "h" and target_unit == "s":
                    normalized_value, normalized_unit = value * 3600.0, "s"
                elif raw_unit == "min" and target_unit == "s":
                    normalized_value, normalized_unit = value * 60.0, "s"
                elif raw_unit == "C" and target_unit == "K":
                    normalized_value, normalized_unit = value + 273.15, "K"
                elif raw_unit == "K" and target_unit == "K":
                    normalized_value, normalized_unit = value, "K"
                elif raw_unit == "xg" and target_unit == "xg":
                    normalized_value, normalized_unit = value, "xg"
                elif raw_unit == target_unit and raw_unit is not None:
                    normalized_value, normalized_unit = value, raw_unit
                else:
                    status = "UNKNOWN"
                    reason = "PROTOCOL_UNIT_UNSUPPORTED"
            elif field_type == "integer":
                if isinstance(raw_value, bool) or not isinstance(raw_value, int):
                    raise ProtocolResolutionError(
                        f"{protocol_id}.{field_id} requires integer value"
                    )
                normalized_value, normalized_unit = raw_value, target_unit
            else:
                if not isinstance(raw_value, str):
                    raise ProtocolResolutionError(f"{protocol_id}.{field_id} requires text value")
                normalized_value, normalized_unit = raw_value, None
        if status in {"MISSING", "UNKNOWN"} and status == "UNKNOWN":
            reviews.append(
                {
                    "review_id": f"protocol-review:{protocol_id}:{field_id}",
                    "reason": reason,
                    "protocol_id": protocol_id,
                    "field_id": field_id,
                    "source_locator": locator,
                    "resolution": "MANUAL_REVIEW",
                }
            )
        return {
            "protocol_id": protocol_id,
            "field_id": field_id,
            "name": name,
            "field_type": field_type,
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "target_unit": target_unit,
            "normalized_value": normalized_value,
            "normalized_unit": normalized_unit,
            "ontology_id": ontology_id,
            "observed": observed,
            "status": status,
            "missingness": "OBSERVED" if observed else "MISSING",
            "resolution_reason": reason,
            "source_locator": locator,
        }

    @staticmethod
    def _severity_features(protocol_id: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
        by_name = {field["name"]: field for field in fields}

        def value(name: str) -> Any:
            field = by_name.get(name)
            return field["normalized_value"] if field else None

        return {
            "protocol_id": protocol_id,
            "source": value("bioenvironment_source"),
            "concentration_fraction": value("concentration"),
            "exposure_time_s": value("exposure_time"),
            "temperature_k": value("temperature"),
            "wash_count": value("wash_count"),
            "centrifugation_xg": value("centrifugation"),
            "assay": value("assay"),
            "replicate_count": value("replicate_count"),
            "missing_field_count": sum(field["status"] == "MISSING" for field in fields),
            "unknown_field_count": sum(field["status"] == "UNKNOWN" for field in fields),
        }

    def run(self) -> ProtocolResolutionSummary:
        """Normalize protocol fields, clusters, and review evidence."""
        protocols = self._load_fixture(self.fixture_path)
        reviews: list[dict[str, Any]] = []
        normalized_protocols: list[dict[str, Any]] = []
        clusters: list[dict[str, Any]] = []
        for raw_protocol in protocols:
            required = {"protocol_id", "source_locator", "fields"}
            if set(raw_protocol) != required:
                raise ProtocolResolutionError("protocol schema is invalid")
            protocol_id = _text(raw_protocol["protocol_id"])
            locator = _text(raw_protocol["source_locator"])
            raw_fields = raw_protocol["fields"]
            if (
                not protocol_id
                or not locator.startswith("asset:")
                or not isinstance(raw_fields, list)
            ):
                raise ProtocolResolutionError("protocol identifiers/fields are invalid")
            fields = [
                self._normalize_field(protocol_id, field, reviews)
                for field in raw_fields
                if isinstance(field, dict)
            ]
            if len(fields) != len(raw_fields):
                raise ProtocolResolutionError("protocol fields contain a non-object")
            severity = self._severity_features(protocol_id, fields)
            normalized_protocols.append(
                {
                    "protocol_id": protocol_id,
                    "source_locator": locator,
                    "fields": fields,
                    "severity_features": severity,
                }
            )
            clusters.append(
                {
                    "cluster_id": f"protocol-cluster:{protocol_id}",
                    "protocol_ids": [protocol_id],
                    "feature_vector": severity,
                    "missingness_explicit": True,
                }
            )

        self.protocols_path.parent.mkdir(parents=True, exist_ok=True)
        self.protocols_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "protocols": normalized_protocols},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.clusters_path.parent.mkdir(parents=True, exist_ok=True)
        self.clusters_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "clusters": clusters},
                indent=2,
                sort_keys=True,
            )
            + "\n",
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

        fields_count = sum(len(protocol["fields"]) for protocol in normalized_protocols)
        observed_count = sum(
            field["status"] == "OBSERVED"
            for protocol in normalized_protocols
            for field in protocol["fields"]
        )
        missing_count = sum(
            field["status"] == "MISSING"
            for protocol in normalized_protocols
            for field in protocol["fields"]
        )
        report = (
            "\n".join(
                [
                    "# Bioenvironment and Protocol Resolution Report",
                    "",
                    "Protocol fields retain raw values, normalized values, "
                    "locators, and missingness.",
                    "",
                    f"- protocols: {len(protocols)}",
                    f"- fields: {fields_count}",
                    f"- observed fields: {observed_count}",
                    f"- missing fields: {missing_count}",
                    f"- clusters: {len(clusters)}",
                    f"- review items: {len(reviews)}",
                    "",
                    "Severity feature vectors never impute missing observations.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return ProtocolResolutionSummary(
            protocols=len(protocols),
            fields=fields_count,
            observed_fields=observed_count,
            missing_fields=missing_count,
            clusters=len(clusters),
            review_items=len(reviews),
            protocols_path=self.protocols_path,
            clusters_path=self.clusters_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
