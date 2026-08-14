"""Deterministic unit normalization with basis and uncertainty firewalls."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class UnitNormalizationError(ValueError):
    """Raised when a unit fixture violates its contract."""


@dataclass(frozen=True)
class UnitDefinition:
    """One registered unit and its multiplier to a dimension base."""

    symbol: str
    dimension: str
    to_base: float
    base_symbol: str


@dataclass(frozen=True)
class NormalizedAssertion:
    """Raw and normalized quantity with uncertainty provenance."""

    assertion_id: str
    quantity: str
    raw_value: float
    raw_unit: str
    raw_uncertainty: float | None
    target_unit: str
    normalized_value: float | None
    normalized_uncertainty: float | None
    relative_uncertainty: float | None
    dimension: str | None
    conversion_factor: float | None
    status: str
    clarification_reason: str | None
    evidence_locator: str


@dataclass(frozen=True)
class UnitNormalizationSummary:
    """Counts and output paths from one fixture run."""

    assertions: int
    normalized: int
    review_items: int
    uncertainty_records: int
    output_path: Path
    review_path: Path
    report_path: Path


UNIT_REGISTRY: tuple[UnitDefinition, ...] = (
    UnitDefinition("m", "length", 1.0, "m"),
    UnitDefinition("um", "length", 1e-6, "m"),
    UnitDefinition("nm", "length", 1e-9, "m"),
    UnitDefinition("s", "time", 1.0, "s"),
    UnitDefinition("min", "time", 60.0, "s"),
    UnitDefinition("h", "time", 3600.0, "s"),
    UnitDefinition("g/L", "concentration", 1.0, "g/L"),
    UnitDefinition("mg/mL", "concentration", 1.0, "g/L"),
    UnitDefinition("ug/mL", "concentration", 1e-3, "g/L"),
    UnitDefinition("mg", "mass", 1e-3, "g"),
    UnitDefinition("mg/kg", "dose", 1.0, "mg/kg"),
    UnitDefinition("ug/kg", "dose", 1e-3, "mg/kg"),
    UnitDefinition("mV", "zeta", 1.0, "mV"),
    UnitDefinition("pdi", "pdi", 1.0, "pdi"),
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise UnitNormalizationError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise UnitNormalizationError(f"{name} must be finite")
    return result


class UnitNormalizer:
    """Normalize registered units without guessing dimensions or basis."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/normalize/units.json")
        self.output_path = output_path or self.root / "registry/normalized_units.json"
        self.review_path = review_path or (self.root / "registry/unit_clarification_queue.jsonl")
        self.report_path = report_path or self.root / "reports/unit_normalization.md"
        self.units = {definition.symbol: definition for definition in UNIT_REGISTRY}

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise UnitNormalizationError(f"cannot load unit fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "assertions"}:
            raise UnitNormalizationError("unit fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["assertions"], list):
            raise UnitNormalizationError("unit fixture schema is invalid")
        required = {
            "assertion_id",
            "quantity",
            "value",
            "unit",
            "uncertainty",
            "target_unit",
            "basis",
            "evidence_locator",
        }
        assertions: list[dict[str, Any]] = []
        for raw in value["assertions"]:
            if not isinstance(raw, Mapping) or set(raw) != required:
                raise UnitNormalizationError("unit assertion fields are invalid")
            assertions.append(dict(raw))
        return assertions

    def _normalize(self, raw: Mapping[str, Any]) -> NormalizedAssertion:
        assertion_id = _text(raw["assertion_id"])
        quantity = _text(raw["quantity"])
        raw_unit = _text(raw["unit"])
        target_unit = _text(raw["target_unit"])
        locator = _text(raw["evidence_locator"])
        raw_value = _float(raw["value"], f"{assertion_id}.value")
        raw_uncertainty = (
            None if raw["uncertainty"] is None else _float(raw["uncertainty"], f"{assertion_id}.uncertainty")
        )
        if not assertion_id or not quantity or not raw_unit or not target_unit:
            raise UnitNormalizationError("assertion identifiers and units are required")
        if not locator.startswith("asset:"):
            raise UnitNormalizationError(f"{assertion_id} evidence locator is invalid")
        if raw_uncertainty is not None and raw_uncertainty < 0.0:
            raise UnitNormalizationError(f"{assertion_id} uncertainty cannot be negative")

        source = self.units.get(raw_unit)
        target = self.units.get(target_unit)
        if source is None or target is None:
            status = "REVIEW_REQUIRED"
            reason = "UNSUPPORTED_UNIT"
            dimension = source.dimension if source else None
            factor = None
        elif source.dimension == target.dimension:
            status = "NORMALIZED"
            reason = None
            dimension = source.dimension
            factor = source.to_base / target.to_base
        elif target.dimension == "dose" and source.dimension == "mass":
            status = "REVIEW_REQUIRED"
            reason = "UNKNOWN_BASIS_FOR_DOSE"
            dimension = None
            factor = None
        else:
            status = "REVIEW_REQUIRED"
            reason = "INCOMPATIBLE_DIMENSIONS"
            dimension = None
            factor = None

        normalized_value = raw_value * factor if factor is not None else None
        normalized_uncertainty = (
            raw_uncertainty * abs(factor) if raw_uncertainty is not None and factor is not None else None
        )
        relative_uncertainty = (
            abs(normalized_uncertainty / normalized_value)
            if (normalized_uncertainty is not None and normalized_value is not None and normalized_value != 0.0)
            else None
        )
        return NormalizedAssertion(
            assertion_id=assertion_id,
            quantity=quantity,
            raw_value=raw_value,
            raw_unit=raw_unit,
            raw_uncertainty=raw_uncertainty,
            target_unit=target_unit,
            normalized_value=normalized_value,
            normalized_uncertainty=normalized_uncertainty,
            relative_uncertainty=relative_uncertainty,
            dimension=dimension,
            conversion_factor=factor,
            status=status,
            clarification_reason=reason,
            evidence_locator=locator,
        )

    def run(self) -> UnitNormalizationSummary:
        """Normalize fixture assertions and write clarification records."""
        assertions = [self._normalize(raw) for raw in self._load_fixture(self.fixture_path)]
        reviews = [
            {
                "review_id": f"unit-review:{assertion.assertion_id}",
                "reason": assertion.clarification_reason,
                "assertion_id": assertion.assertion_id,
                "raw_unit": assertion.raw_unit,
                "target_unit": assertion.target_unit,
                "evidence_locator": assertion.evidence_locator,
                "resolution": "MANUAL_REVIEW",
            }
            for assertion in assertions
            if assertion.status != "NORMALIZED"
        ]
        payload = {
            "schema_version": 1,
            "fixture": True,
            "unit_registry": [asdict(definition) for definition in UNIT_REGISTRY],
            "assertions": [asdict(assertion) for assertion in assertions],
            "summary": {
                "assertions": len(assertions),
                "normalized": sum(assertion.status == "NORMALIZED" for assertion in assertions),
                "review_items": len(reviews),
                "uncertainty_records": sum(assertion.raw_uncertainty is not None for assertion in assertions),
            },
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
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

        normalized_count = sum(assertion.status == "NORMALIZED" for assertion in assertions)
        uncertainty_count = sum(assertion.raw_uncertainty is not None for assertion in assertions)
        report = (
            "\n".join(
                [
                    "# Unit Normalization Report",
                    "",
                    "Raw values and locators are preserved; unknown bases are not converted.",
                    "",
                    f"- assertions: {len(assertions)}",
                    f"- normalized: {normalized_count}",
                    f"- review items: {len(reviews)}",
                    f"- uncertainty records: {uncertainty_count}",
                    "",
                    "Conversions are dimension-checked against the committed unit registry.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return UnitNormalizationSummary(
            assertions=len(assertions),
            normalized=sum(assertion.status == "NORMALIZED" for assertion in assertions),
            review_items=len(reviews),
            uncertainty_records=sum(assertion.raw_uncertainty is not None for assertion in assertions),
            output_path=self.output_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
