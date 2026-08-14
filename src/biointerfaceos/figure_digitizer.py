"""Fixture-backed figure digitization with calibration and uncertainty evidence."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class FigureDigitizationError(ValueError):
    """Raised when a digitization fixture violates its contract."""


@dataclass(frozen=True)
class AxisCalibration:
    """Inverse pixel-to-data calibration for one axis."""

    axis_id: str
    orientation: str
    label: str
    scale_type: str
    tick_positions: tuple[float, ...]
    tick_values: tuple[float, ...]
    locator: str
    max_residual: float
    confidence: float


@dataclass(frozen=True)
class DigitizedPoint:
    """One calibrated point with optional propagated uncertainty."""

    point_id: str
    series_id: str
    series_type: str
    x_position: float
    y_position: float
    x_value: float
    y_value: float
    x_error: float | None
    y_error: float | None
    error_type: str | None
    source_locator: str
    detector_locator: str
    confidence: float


@dataclass(frozen=True)
class DigitizedSeries:
    """One recovered curve/bar/scatter series."""

    series_id: str
    series_type: str
    detector_locator: str
    quality_score: float
    calibration_ids: tuple[str, ...]
    points: tuple[DigitizedPoint, ...]


@dataclass(frozen=True)
class FigureDigitizationSummary:
    """Counts and output paths from one fixture run."""

    figures: int
    panels: int
    series_seen: int
    digitized_series: int
    excluded_series: int
    points: int
    uncertainty_records: int
    review_items: int
    normalized_path: Path
    review_path: Path
    overlay_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise FigureDigitizationError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise FigureDigitizationError(f"{name} must be finite")
    return result


def _normalized_pair(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise FigureDigitizationError(f"{name} must contain two coordinates")
    pair = (_float(value[0], f"{name}[0]"), _float(value[1], f"{name}[1]"))
    if any(not 0.0 <= item <= 1.0 for item in pair):
        raise FigureDigitizationError(f"{name} must be normalized to [0, 1]")
    return pair


def _calibrate_value(
    position: float,
    positions: tuple[float, ...],
    values: tuple[float, ...],
    scale_type: str,
) -> float:
    if position < positions[0] - 1e-9 or position > positions[-1] + 1e-9:
        raise FigureDigitizationError("point falls outside calibration ticks")
    for index in range(len(positions) - 1):
        left_position = positions[index]
        right_position = positions[index + 1]
        if position <= right_position or index == len(positions) - 2:
            fraction = (position - left_position) / (right_position - left_position)
            left_value = values[index]
            right_value = values[index + 1]
            if scale_type == "log":
                return 10 ** (math.log10(left_value) + fraction * (math.log10(right_value) - math.log10(left_value)))
            return left_value + fraction * (right_value - left_value)
    return values[-1]


def _calibration(raw_axis: Mapping[str, Any], panel_id: str) -> AxisCalibration:
    orientation = _text(raw_axis.get("orientation")).lower()
    if orientation not in {"x", "y"}:
        raise FigureDigitizationError("axis orientation must be x or y")
    scale_type = _text(raw_axis.get("scale_type")).lower()
    if scale_type not in {"linear", "log"}:
        raise FigureDigitizationError("axis scale_type must be linear or log")
    raw_ticks = raw_axis.get("ticks")
    if not isinstance(raw_ticks, list) or len(raw_ticks) < 2:
        raise FigureDigitizationError("calibration requires at least two ticks")
    pairs: list[tuple[float, float, str]] = []
    for tick in raw_ticks:
        if not isinstance(tick, Mapping):
            raise FigureDigitizationError("calibration tick must be an object")
        position = _float(tick.get("position"), "tick position")
        value = _float(tick.get("value"), "tick value")
        label = _text(tick.get("label")) or str(value)
        if not 0.0 <= position <= 1.0:
            raise FigureDigitizationError("tick position must be normalized")
        if scale_type == "log" and value <= 0.0:
            raise FigureDigitizationError("log calibration values must be positive")
        pairs.append((position, value, label))
    pairs.sort(key=lambda item: item[0])
    positions = tuple(pair[0] for pair in pairs)
    values = tuple(pair[1] for pair in pairs)
    if len(set(positions)) != len(positions):
        raise FigureDigitizationError("calibration tick positions must be unique")
    if any(right <= left for left, right in zip(positions, positions[1:], strict=False)):
        raise FigureDigitizationError("calibration tick positions must increase")
    residuals = [
        abs(_calibrate_value(position, positions, values, scale_type) - value)
        for position, value in zip(positions, values, strict=True)
    ]
    confidence = 0.96 if len(pairs) >= 3 else 0.84
    axis_id = f"{panel_id}:{orientation}"
    locator = _text(raw_axis.get("locator"))
    if not locator:
        raise FigureDigitizationError("axis locator is required")
    return AxisCalibration(
        axis_id=axis_id,
        orientation=orientation,
        label=_text(raw_axis.get("label")) or orientation,
        scale_type=scale_type,
        tick_positions=positions,
        tick_values=values,
        locator=locator,
        max_residual=max(residuals),
        confidence=confidence,
    )


class FigureDigitizer:
    """Digitize eligible vector-like candidates with explicit calibration."""

    SUPPORTED_SERIES_TYPES = frozenset({"curve", "bar", "scatter"})

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        normalized_path: Path | None = None,
        review_path: Path | None = None,
        overlay_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/figures/digitization.json")
        self.normalized_path = normalized_path or (self.root / "registry/digitized_figure_points.json")
        self.review_path = review_path or (self.root / "registry/digitization_review_queue.jsonl")
        self.overlay_path = overlay_path or (self.root / "reports/digitization_qc_overlay.json")
        self.report_path = report_path or self.root / "reports/figure_digitization.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FigureDigitizationError(f"cannot load digitization fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "figures"}:
            raise FigureDigitizationError("digitization fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["figures"], list):
            raise FigureDigitizationError("digitization fixture schema is invalid")
        figures: list[dict[str, Any]] = []
        for raw_figure in value["figures"]:
            if not isinstance(raw_figure, Mapping) or set(raw_figure) != {
                "figure_id",
                "source_asset_id",
                "panels",
            }:
                raise FigureDigitizationError("digitization figure fields are invalid")
            raw_panels = raw_figure["panels"]
            if not isinstance(raw_panels, list) or not raw_panels:
                raise FigureDigitizationError("digitization figure requires panels")
            panels: list[dict[str, Any]] = []
            for raw_panel in raw_panels:
                if not isinstance(raw_panel, Mapping) or set(raw_panel) != {
                    "panel_id",
                    "bbox",
                    "panel_type",
                    "axes",
                    "series",
                }:
                    raise FigureDigitizationError("digitization panel fields are invalid")
                if not isinstance(raw_panel["axes"], list) or not raw_panel["axes"]:
                    raise FigureDigitizationError("digitization panel requires axes")
                if not isinstance(raw_panel["series"], list):
                    raise FigureDigitizationError("digitization panel series must be a list")
                panels.append(dict(raw_panel))
            figure = dict(raw_figure)
            figure["panels"] = panels
            figures.append(figure)
        return figures

    @staticmethod
    def _review(
        review_id: str,
        reason: str,
        source_asset_id: str,
        figure_id: str,
        panel_id: str,
        series_id: str | None,
        locator: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "review_id": review_id,
            "reason": reason,
            "source_asset_id": source_asset_id,
            "figure_id": figure_id,
            "panel_id": panel_id,
            "series_id": series_id,
            "locator": locator,
            "confidence": confidence,
            "resolution": "MANUAL_REVIEW",
        }

    def _digitize_series(
        self,
        figure: Mapping[str, Any],
        panel: Mapping[str, Any],
        calibrations: Mapping[str, AxisCalibration],
        raw_series: Mapping[str, Any],
        reviews: list[dict[str, Any]],
    ) -> DigitizedSeries | None:
        source_asset_id = _text(figure["source_asset_id"])
        figure_id = _text(figure["figure_id"])
        panel_id = _text(panel["panel_id"])
        series_id = _text(raw_series.get("series_id"))
        series_type = _text(raw_series.get("series_type")).lower()
        detector_locator = _text(raw_series.get("detector_locator"))
        quality_score = _float(raw_series.get("quality_score"), "quality_score")
        if not series_id or not detector_locator:
            raise FigureDigitizationError("series_id and detector_locator are required")
        if series_type not in self.SUPPORTED_SERIES_TYPES:
            raise FigureDigitizationError(f"unsupported series type: {series_type}")
        if not 0.0 <= quality_score <= 1.0:
            raise FigureDigitizationError("quality_score must be normalized")
        series_locator = f"asset:{source_asset_id}/figure:{figure_id}/panel:{panel_id}/series:{series_id}"
        if quality_score < 0.75:
            reviews.append(
                self._review(
                    f"low-quality:{figure_id}:{panel_id}:{series_id}",
                    "LOW_RESOLUTION_CANDIDATE_EXCLUDED",
                    source_asset_id,
                    figure_id,
                    panel_id,
                    series_id,
                    series_locator,
                    quality_score,
                )
            )
            return None
        raw_points = raw_series.get("points")
        if not isinstance(raw_points, list) or not raw_points:
            raise FigureDigitizationError("series points must be a non-empty list")
        uncertainty = raw_series.get("uncertainty")
        if not isinstance(uncertainty, list) or len(uncertainty) != len(raw_points):
            raise FigureDigitizationError("uncertainty list must match point count")
        x_axis = calibrations.get("x")
        y_axis = calibrations.get("y")
        if x_axis is None or y_axis is None:
            raise FigureDigitizationError("both x and y calibrations are required")
        points: list[DigitizedPoint] = []
        for index, raw_point in enumerate(raw_points, 1):
            x_position, y_position = _normalized_pair(raw_point, f"{series_id} point {index}")
            x_value = _calibrate_value(
                x_position,
                x_axis.tick_positions,
                x_axis.tick_values,
                x_axis.scale_type,
            )
            y_value = _calibrate_value(
                y_position,
                y_axis.tick_positions,
                y_axis.tick_values,
                y_axis.scale_type,
            )
            raw_uncertainty = uncertainty[index - 1]
            x_error: float | None = None
            y_error: float | None = None
            error_type: str | None = None
            if raw_uncertainty is not None:
                if not isinstance(raw_uncertainty, Mapping):
                    raise FigureDigitizationError("uncertainty entry must be an object or null")
                half_range = _float(
                    raw_uncertainty.get("half_range"),
                    f"{series_id} uncertainty {index}",
                )
                if not 0.0 < half_range <= 0.5:
                    raise FigureDigitizationError("uncertainty half_range is invalid")
                if y_position - half_range < 0.0 or y_position + half_range > 1.0:
                    raise FigureDigitizationError("uncertainty interval leaves calibration range")
                low = _calibrate_value(
                    y_position + half_range,
                    y_axis.tick_positions,
                    y_axis.tick_values,
                    y_axis.scale_type,
                )
                high = _calibrate_value(
                    y_position - half_range,
                    y_axis.tick_positions,
                    y_axis.tick_values,
                    y_axis.scale_type,
                )
                y_error = abs(high - low) / 2.0
                error_type = _text(raw_uncertainty.get("kind")) or "ERROR"
            point_locator = f"{series_locator}/point[{index}]"
            points.append(
                DigitizedPoint(
                    point_id=f"{series_id}:point:{index}",
                    series_id=series_id,
                    series_type=series_type,
                    x_position=x_position,
                    y_position=y_position,
                    x_value=x_value,
                    y_value=y_value,
                    x_error=x_error,
                    y_error=y_error,
                    error_type=error_type,
                    source_locator=point_locator,
                    detector_locator=detector_locator,
                    confidence=min(0.98, quality_score * 0.9 + 0.08),
                )
            )
        return DigitizedSeries(
            series_id=series_id,
            series_type=series_type,
            detector_locator=detector_locator,
            quality_score=quality_score,
            calibration_ids=(x_axis.axis_id, y_axis.axis_id),
            points=tuple(points),
        )

    def run(self) -> FigureDigitizationSummary:
        """Calibrate and digitize eligible fixture candidates."""
        figures = self._load_fixture(self.fixture_path)
        figure_outputs: list[dict[str, Any]] = []
        overlays: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []
        panels_count = 0
        series_seen = 0
        digitized_series_count = 0
        excluded_series_count = 0
        points_count = 0
        uncertainty_count = 0

        for figure in figures:
            source_asset_id = _text(figure["source_asset_id"])
            figure_id = _text(figure["figure_id"])
            panel_outputs: list[dict[str, Any]] = []
            for panel in figure["panels"]:
                panels_count += 1
                panel_id = _text(panel["panel_id"])
                panel_type = _text(panel["panel_type"]).lower()
                bbox = panel["bbox"]
                if panel_type not in {"plot", "line", "bar", "scatter"}:
                    locator = f"asset:{source_asset_id}/figure:{figure_id}/panel:{panel_id}"
                    reviews.append(
                        self._review(
                            f"unsupported-panel:{figure_id}:{panel_id}",
                            f"UNSUPPORTED_PANEL_TYPE_{panel_type.upper()}",
                            source_asset_id,
                            figure_id,
                            panel_id,
                            None,
                            locator,
                            0.9,
                        )
                    )
                    panel_outputs.append(
                        {
                            "panel_id": panel_id,
                            "panel_type": panel_type,
                            "supported": False,
                            "bbox": bbox,
                            "calibrations": [],
                            "series": [],
                            "excluded_series": [],
                            "review_items": reviews[-1:],
                        }
                    )
                    continue
                raw_axes = panel["axes"]
                if not isinstance(raw_axes, list):
                    raise FigureDigitizationError("panel axes must be a list")
                calibration_list = [_calibration(axis, panel_id) for axis in raw_axes if isinstance(axis, Mapping)]
                calibrations = {axis.orientation: axis for axis in calibration_list}
                panel_series: list[DigitizedSeries] = []
                excluded: list[str] = []
                raw_series_list = panel["series"]
                if not isinstance(raw_series_list, list):
                    raise FigureDigitizationError("panel series must be a list")
                for raw_series in raw_series_list:
                    if not isinstance(raw_series, Mapping):
                        raise FigureDigitizationError("series must be an object")
                    series_seen += 1
                    series = self._digitize_series(figure, panel, calibrations, raw_series, reviews)
                    if series is None:
                        excluded.append(_text(raw_series.get("series_id")))
                        excluded_series_count += 1
                        continue
                    panel_series.append(series)
                    digitized_series_count += 1
                    points_count += len(series.points)
                    uncertainty_count += sum(point.y_error is not None for point in series.points)
                panel_outputs.append(
                    {
                        "panel_id": panel_id,
                        "panel_type": panel_type,
                        "supported": True,
                        "bbox": bbox,
                        "calibrations": [asdict(axis) for axis in calibration_list],
                        "series": [asdict(series) for series in panel_series],
                        "excluded_series": excluded,
                        "review_items": [
                            review
                            for review in reviews
                            if review["figure_id"] == figure_id and review["panel_id"] == panel_id
                        ],
                    }
                )
                overlays.append(
                    {
                        "figure_id": figure_id,
                        "panel_id": panel_id,
                        "source_asset_id": source_asset_id,
                        "series": [
                            {
                                "series_id": series.series_id,
                                "detector_locator": series.detector_locator,
                                "normalized_points": [[point.x_position, point.y_position] for point in series.points],
                                "digitized_point_locators": [point.source_locator for point in series.points],
                            }
                            for series in panel_series
                        ],
                    }
                )
            figure_outputs.append(
                {
                    "figure_id": figure_id,
                    "source_asset_id": source_asset_id,
                    "panels": panel_outputs,
                }
            )

        normalized = {
            "schema_version": 1,
            "fixture": True,
            "figures": figure_outputs,
            "summary": {
                "figures": len(figures),
                "panels": panels_count,
                "series_seen": series_seen,
                "digitized_series": digitized_series_count,
                "excluded_series": excluded_series_count,
                "points": points_count,
                "uncertainty_records": uncertainty_count,
                "review_items": len(reviews),
            },
            "review_items": reviews,
        }
        self.normalized_path.parent.mkdir(parents=True, exist_ok=True)
        self.normalized_path.write_text(
            json.dumps(normalized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.overlay_path.parent.mkdir(parents=True, exist_ok=True)
        self.overlay_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "fixture": True,
                    "purpose": "review overlay mapping detector candidates to calibrated points",
                    "overlays": overlays,
                },
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
                    "# Figure Digitization Report",
                    "",
                    "Fixture-backed calibration and digitization with explicit uncertainty.",
                    "",
                    f"- figures: {len(figures)}",
                    f"- panels: {panels_count}",
                    f"- series seen: {series_seen}",
                    f"- digitized series: {digitized_series_count}",
                    f"- excluded series: {excluded_series_count}",
                    f"- digitized points: {points_count}",
                    f"- uncertainty records: {uncertainty_count}",
                    f"- review items: {len(reviews)}",
                    "",
                    "QC overlay coordinates and source locators are stored in reports/digitization_qc_overlay.json.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return FigureDigitizationSummary(
            figures=len(figures),
            panels=panels_count,
            series_seen=series_seen,
            digitized_series=digitized_series_count,
            excluded_series=excluded_series_count,
            points=points_count,
            uncertainty_records=uncertainty_count,
            review_items=len(reviews),
            normalized_path=self.normalized_path,
            review_path=self.review_path,
            overlay_path=self.overlay_path,
            report_path=self.report_path,
        )
