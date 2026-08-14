"""Fixture-backed table-to-experiment semantic mapping."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class TableSemanticsError(ValueError):
    """Raised when semantic table input violates its contract."""


@dataclass(frozen=True)
class ExperimentArm:
    """One experiment arm with source evidence."""

    arm_id: str
    label: str
    sample_size: int | None
    sample_size_locator: str | None
    source_cell_locators: tuple[str, ...]
    confidence: str


@dataclass(frozen=True)
class ExperimentMeasurement:
    """One arm/outcome measurement with mean/error/unit evidence."""

    measurement_id: str
    arm_id: str
    outcome: str
    mean: float | None
    error: float | None
    error_type: str | None
    unit: str | None
    footnotes: tuple[str, ...]
    source_cell_locators: tuple[str, ...]
    confidence: str


@dataclass(frozen=True)
class SemanticTableResult:
    """Normalized semantic output for one table."""

    table_id: str
    source_asset_id: str
    header_hierarchy: Mapping[str, tuple[str, ...]]
    arms: tuple[ExperimentArm, ...]
    measurements: tuple[ExperimentMeasurement, ...]
    review_items: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class TableSemanticsSummary:
    """Counts and output paths from one fixture run."""

    tables: int
    arms: int
    measurements: int
    review_items: int
    normalized_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _number(value: str) -> float | None:
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"


class TableSemanticsParser:
    """Map normalized fixture cells to experiment semantics without coercion."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        normalized_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/semantics/table_semantics.json")
        self.normalized_path = normalized_path or (self.root / "registry/experiment_table_semantics.json")
        self.review_path = review_path or self.root / "registry/table_review_queue.jsonl"
        self.report_path = report_path or self.root / "reports/table_semantics.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TableSemanticsError(f"cannot load table fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "tables"}:
            raise TableSemanticsError("table semantics fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["tables"], list):
            raise TableSemanticsError("table semantics fixture schema is invalid")
        tables: list[dict[str, Any]] = []
        for raw in value["tables"]:
            if not isinstance(raw, Mapping):
                raise TableSemanticsError("table fixture entry is invalid")
            required = {"table_id", "source_asset_id", "header_rows", "cells", "footnotes"}
            if set(raw) != required:
                raise TableSemanticsError("table fixture fields are invalid")
            if not isinstance(raw["header_rows"], int) or raw["header_rows"] <= 0:
                raise TableSemanticsError("header_rows must be positive")
            if not isinstance(raw["cells"], list) or not isinstance(raw["footnotes"], list):
                raise TableSemanticsError("table cells or footnotes are invalid")
            tables.append(dict(raw))
        return tables

    @staticmethod
    def _cell_locator(table: Mapping[str, Any], coordinate: str) -> str:
        return f"asset:{table['source_asset_id']}/table:{table['table_id']}/cell:{coordinate}"

    def _parse_table(self, table: Mapping[str, Any]) -> SemanticTableResult:
        raw_cells = table["cells"]
        cells: dict[str, dict[str, Any]] = {}
        by_row: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for raw in raw_cells:
            if not isinstance(raw, Mapping) or set(raw) != {
                "coordinate",
                "row",
                "column",
                "raw_value",
                "unit",
            }:
                raise TableSemanticsError(f"cell schema is invalid in {table['table_id']}")
            coordinate = str(raw["coordinate"])
            row = int(raw["row"])
            column = int(raw["column"])
            cell = {
                "coordinate": coordinate,
                "row": row,
                "column": column,
                "raw_value": _text(raw["raw_value"]),
                "unit": raw["unit"] if raw["unit"] is None else _text(raw["unit"]),
            }
            cells[coordinate] = cell
            by_row[row].append(cell)
        header_rows = int(table["header_rows"])
        max_row = max((cell["row"] for cell in cells.values()), default=0)
        if max_row <= header_rows:
            raise TableSemanticsError(f"table {table['table_id']} has no data rows")
        columns = sorted({cell["column"] for cell in cells.values()})
        hierarchy: dict[str, tuple[str, ...]] = {}
        for column in columns:
            values = tuple(
                cells_by_column["raw_value"]
                for header in range(1, header_rows + 1)
                for cells_by_column in sorted(
                    (cell for cell in cells.values() if cell["column"] == column and cell["row"] == header),
                    key=lambda value: value["row"],
                )
            )
            hierarchy[str(column)] = values
        combined = {column: " ".join(value for value in hierarchy[str(column)] if value).lower() for column in columns}
        arm_column = next(
            (column for column in columns if any(token in combined[column] for token in ("arm", "group", "treatment"))),
            columns[0],
        )
        n_column = next(
            (
                column
                for column in columns
                if (
                    combined[column].strip() in {"n", "sample size", "n sample"}
                    or combined[column].strip().endswith(" n")
                )
            ),
            None,
        )
        outcome_columns = [
            column
            for column in columns
            if column not in {arm_column, n_column}
            and any(token in combined[column] for token in ("mean", "outcome", "value"))
            and not any(token in combined[column] for token in ("sd", "se", "error", "stderr", "unit"))
        ]
        if not outcome_columns:
            outcome_columns = [column for column in columns if column not in {arm_column, n_column}]
        error_columns = [
            column for column in columns if any(token in combined[column] for token in ("sd", "se", "error", "stderr"))
        ]
        unit_columns = [column for column in columns if any(token in combined[column] for token in ("unit", "units"))]
        reviews: list[dict[str, Any]] = []
        if len(outcome_columns) > 1:
            reviews.append(
                {
                    "review_id": f"incompatible-outcomes:{table['table_id']}",
                    "reason": "MULTIPLE_OUTCOME_COLUMNS_REQUIRES_REVIEW",
                    "table_id": table["table_id"],
                    "source_asset_id": table["source_asset_id"],
                    "resolution": "MANUAL_REVIEW",
                }
            )
        if not unit_columns:
            reviews.append(
                {
                    "review_id": f"missing-unit:{table['table_id']}",
                    "reason": "UNIT_MISSING",
                    "table_id": table["table_id"],
                    "source_asset_id": table["source_asset_id"],
                    "resolution": "MANUAL_REVIEW",
                }
            )
        arms: list[ExperimentArm] = []
        measurements: list[ExperimentMeasurement] = []
        data_rows = sorted(row for row in by_row if row > header_rows)
        for row_number in data_rows:
            row_cells = {cell["column"]: cell for cell in by_row[row_number]}
            arm_cell = row_cells.get(arm_column)
            if arm_cell is None or not arm_cell["raw_value"]:
                reviews.append(
                    {
                        "review_id": f"missing-arm:{table['table_id']}:{row_number}",
                        "reason": "ARM_LABEL_MISSING",
                        "table_id": table["table_id"],
                        "row": row_number,
                        "resolution": "MANUAL_REVIEW",
                    }
                )
                continue
            label = arm_cell["raw_value"]
            arm_id = f"{_slug(str(table['table_id']))}:{_slug(label)}"
            n_cell = row_cells.get(n_column) if n_column is not None else None
            n_value = int(float(n_cell["raw_value"])) if n_cell and _number(n_cell["raw_value"]) is not None else None
            confidence = "HIGH" if n_value is not None else "LOW"
            arms.append(
                ExperimentArm(
                    arm_id=arm_id,
                    label=label,
                    sample_size=n_value,
                    sample_size_locator=(self._cell_locator(table, n_cell["coordinate"]) if n_cell else None),
                    source_cell_locators=(self._cell_locator(table, arm_cell["coordinate"]),),
                    confidence=confidence,
                )
            )
            for outcome_column in outcome_columns:
                outcome_cell = row_cells.get(outcome_column)
                if outcome_cell is None:
                    continue
                outcome_header = " ".join(h for h in hierarchy[str(outcome_column)] if h)
                mean_value = _number(outcome_cell["raw_value"])
                error_cell = next(
                    (row_cells[column] for column in error_columns if column in row_cells),
                    None,
                )
                unit_cell = next(
                    (row_cells[column] for column in unit_columns if column in row_cells),
                    None,
                )
                error_value = _number(error_cell["raw_value"]) if error_cell else None
                error_type = (
                    "SD"
                    if error_cell and "sd" in combined.get(error_cell["column"], "")
                    else "SE"
                    if error_cell and "se" in combined.get(error_cell["column"], "")
                    else "ERROR"
                    if error_cell
                    else None
                )
                unit = unit_cell["raw_value"] if unit_cell and unit_cell["raw_value"] else outcome_cell["unit"]
                measurement_confidence = "HIGH" if mean_value is not None and unit else "LOW"
                if mean_value is None:
                    reviews.append(
                        {
                            "review_id": (f"mean-missing:{table['table_id']}:{outcome_cell['coordinate']}"),
                            "reason": "MEAN_NOT_NUMERIC",
                            "table_id": table["table_id"],
                            "cell_locator": self._cell_locator(table, outcome_cell["coordinate"]),
                            "resolution": "MANUAL_REVIEW",
                        }
                    )
                measurements.append(
                    ExperimentMeasurement(
                        measurement_id=f"{arm_id}:{_slug(outcome_header)}",
                        arm_id=arm_id,
                        outcome=outcome_header,
                        mean=mean_value,
                        error=error_value,
                        error_type=error_type,
                        unit=unit,
                        footnotes=tuple(str(value) for value in table["footnotes"]),
                        source_cell_locators=tuple(
                            self._cell_locator(table, cell["coordinate"])
                            for cell in (arm_cell, outcome_cell, error_cell, unit_cell)
                            if cell is not None
                        ),
                        confidence=measurement_confidence,
                    )
                )
        return SemanticTableResult(
            table_id=str(table["table_id"]),
            source_asset_id=str(table["source_asset_id"]),
            header_hierarchy=hierarchy,
            arms=tuple(arms),
            measurements=tuple(measurements),
            review_items=tuple(reviews),
        )

    def run(self) -> TableSemanticsSummary:
        """Parse fixture tables and write normalized output/review evidence."""
        results = tuple(self._parse_table(table) for table in self._load_fixture(self.fixture_path))
        all_arms = [asdict(arm) for result in results for arm in result.arms]
        all_measurements = [asdict(measurement) for result in results for measurement in result.measurements]
        reviews = [dict(review) for result in results for review in result.review_items]
        normalized = {
            "schema_version": 1,
            "fixture": True,
            "tables": [
                {
                    "table_id": result.table_id,
                    "source_asset_id": result.source_asset_id,
                    "header_hierarchy": {key: list(value) for key, value in result.header_hierarchy.items()},
                    "arms": [asdict(arm) for arm in result.arms],
                    "measurements": [asdict(measurement) for measurement in result.measurements],
                    "review_items": list(result.review_items),
                }
                for result in results
            ],
            "arms": all_arms,
            "measurements": all_measurements,
            "review_items": reviews,
        }
        self.normalized_path.parent.mkdir(parents=True, exist_ok=True)
        self.normalized_path.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n",
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
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        report = (
            "\n".join(
                [
                    "# Table Semantics Report",
                    "",
                    "Fixture-backed semantic mapping; formulas are preserved as reported values and not recomputed.",
                    "",
                    f"- tables: {len(results)}",
                    f"- arms: {len(all_arms)}",
                    f"- measurements: {len(all_measurements)}",
                    f"- review items: {len(reviews)}",
                    "",
                    "Low-confidence or incompatible semantics remain in registry/table_review_queue.jsonl.",
                ]
            )
            + "\n"
        )
        self.report_path.write_text(report, encoding="utf-8")
        return TableSemanticsSummary(
            tables=len(results),
            arms=len(all_arms),
            measurements=len(all_measurements),
            review_items=len(reviews),
            normalized_path=self.normalized_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
