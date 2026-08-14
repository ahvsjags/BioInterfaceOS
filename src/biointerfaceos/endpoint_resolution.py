"""Endpoint and measurement ontology normalization."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class EndpointResolutionError(ValueError):
    """Raised when an endpoint fixture violates its contract."""


@dataclass(frozen=True)
class EndpointResolutionSummary:
    """Counts and output paths from one fixture run."""

    endpoints: int
    normalized: int
    families: int
    strata: int
    harmonized_strata: int
    review_items: int
    endpoints_path: Path
    strata_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise EndpointResolutionError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise EndpointResolutionError(f"{name} must be finite")
    return result


class EndpointResolver:
    """Normalize endpoint measurements and harmonize compatible strata only."""

    FAMILIES = frozenset(
        {
            "uptake",
            "viability",
            "complement",
            "inflammation",
            "coagulation",
            "biodistribution",
            "delivery",
        }
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        endpoints_path: Path | None = None,
        strata_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/endpoints/endpoint_resolution.json")
        self.endpoints_path = endpoints_path or (self.root / "registry/endpoint_entities.json")
        self.strata_path = strata_path or (self.root / "registry/endpoint_strata.json")
        self.review_path = review_path or (self.root / "registry/endpoint_review_queue.jsonl")
        self.report_path = report_path or self.root / "reports/endpoint_resolution.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EndpointResolutionError(f"cannot load endpoint fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "endpoints"}:
            raise EndpointResolutionError("endpoint fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["endpoints"], list):
            raise EndpointResolutionError("endpoint fixture schema is invalid")
        endpoints = [dict(item) for item in value["endpoints"] if isinstance(item, Mapping)]
        if len(endpoints) != len(value["endpoints"]):
            raise EndpointResolutionError("endpoint fixture contains a non-object")
        return endpoints

    @staticmethod
    def _time_seconds(value: Any, unit: str | None, endpoint_id: str) -> float | None:
        if value is None or unit is None:
            return None
        number = _float(value, f"{endpoint_id}.time_value")
        if unit == "s":
            return number
        if unit == "min":
            return number * 60.0
        if unit == "h":
            return number * 3600.0
        raise EndpointResolutionError(f"{endpoint_id} time unit is unsupported")

    def _normalize(
        self,
        raw: dict[str, Any],
        reviews: list[dict[str, Any]],
    ) -> dict[str, Any]:
        required = {
            "endpoint_id",
            "raw_label",
            "family",
            "assay",
            "basis",
            "time_value",
            "time_unit",
            "value",
            "value_unit",
            "source_locator",
            "effect_type",
        }
        if set(raw) != required:
            raise EndpointResolutionError("endpoint fields are invalid")
        endpoint_id = _text(raw["endpoint_id"])
        family = _text(raw["family"]).lower()
        assay = _text(raw["assay"])
        basis = _text(raw["basis"])
        locator = _text(raw["source_locator"])
        if not endpoint_id or family not in self.FAMILIES or not assay or not basis or not locator.startswith("asset:"):
            raise EndpointResolutionError(f"{endpoint_id} identity/family/locator invalid")
        time_unit = None if raw["time_unit"] is None else _text(raw["time_unit"])
        time_seconds = self._time_seconds(raw["time_value"], time_unit, endpoint_id)
        value = _float(raw["value"], f"{endpoint_id}.value")
        value_unit = _text(raw["value_unit"])
        normalized_value = value
        normalized_unit = value_unit
        if value_unit == "%":
            normalized_value = value / 100.0
            normalized_unit = "fraction"
        elif value_unit not in {"fraction", "pg/mL", "s", "x"}:
            raise EndpointResolutionError(f"{endpoint_id} value unit is unsupported")
        status = "NORMALIZED"
        reason: str | None = None
        if time_seconds is None:
            status = "REVIEW_REQUIRED"
            reason = "MISSING_ENDPOINT_TIMEPOINT"
            reviews.append(
                {
                    "review_id": f"endpoint-review:{endpoint_id}",
                    "reason": reason,
                    "endpoint_id": endpoint_id,
                    "source_locator": locator,
                    "resolution": "MANUAL_REVIEW",
                }
            )
        stratum_id = f"{family}|assay={assay}|basis={basis}|time_s={time_seconds}" if status == "NORMALIZED" else None
        return {
            "endpoint_id": endpoint_id,
            "raw_label": _text(raw["raw_label"]),
            "family": family,
            "assay": assay,
            "basis": basis,
            "time_value": raw["time_value"],
            "time_unit": time_unit,
            "time_seconds": time_seconds,
            "value": value,
            "value_unit": value_unit,
            "normalized_value": normalized_value if status == "NORMALIZED" else None,
            "normalized_unit": normalized_unit if status == "NORMALIZED" else None,
            "effect_type": _text(raw["effect_type"]),
            "stratum_id": stratum_id,
            "status": status,
            "resolution_reason": reason,
            "source_locator": locator,
        }

    @staticmethod
    def _build_strata(endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for endpoint in endpoints:
            stratum_id = endpoint["stratum_id"]
            if stratum_id is not None:
                grouped.setdefault(stratum_id, []).append(endpoint)
        strata: list[dict[str, Any]] = []
        for stratum_id, members in sorted(grouped.items()):
            values = [float(member["normalized_value"]) for member in members]
            strata.append(
                {
                    "stratum_id": stratum_id,
                    "family": members[0]["family"],
                    "assay": members[0]["assay"],
                    "basis": members[0]["basis"],
                    "time_seconds": members[0]["time_seconds"],
                    "member_endpoint_ids": [member["endpoint_id"] for member in members],
                    "harmonizable": len(members) > 1,
                    "harmonized_mean": sum(values) / len(values) if len(members) > 1 else None,
                    "member_count": len(members),
                }
            )
        return strata

    def run(self) -> EndpointResolutionSummary:
        """Normalize endpoints, preserve strata, and write review evidence."""
        raw_endpoints = self._load_fixture(self.fixture_path)
        reviews: list[dict[str, Any]] = []
        endpoints = [self._normalize(raw, reviews) for raw in raw_endpoints]
        strata = self._build_strata(endpoints)
        self.endpoints_path.parent.mkdir(parents=True, exist_ok=True)
        self.endpoints_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "endpoints": endpoints},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.strata_path.parent.mkdir(parents=True, exist_ok=True)
        self.strata_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "strata": strata},
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

        report = (
            "\n".join(
                [
                    "# Endpoint and Measurement Resolution Report",
                    "",
                    "Endpoints retain assay, basis, timepoint, and compatible-stratum provenance.",
                    "",
                    f"- endpoints: {len(endpoints)}",
                    f"- normalized: {sum(item['status'] == 'NORMALIZED' for item in endpoints)}",
                    f"- families: {len({item['family'] for item in endpoints})}",
                    f"- strata: {len(strata)}",
                    f"- harmonized strata: {sum(item['harmonizable'] for item in strata)}",
                    f"- review items: {len(reviews)}",
                    "",
                    "Incompatible endpoint bases remain separate strata.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return EndpointResolutionSummary(
            endpoints=len(endpoints),
            normalized=sum(item["status"] == "NORMALIZED" for item in endpoints),
            families=len({item["family"] for item in endpoints}),
            strata=len(strata),
            harmonized_strata=sum(item["harmonizable"] for item in strata),
            review_items=len(reviews),
            endpoints_path=self.endpoints_path,
            strata_path=self.strata_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
