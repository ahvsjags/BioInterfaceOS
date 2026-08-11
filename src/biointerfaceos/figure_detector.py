"""Fixture-backed scientific figure panel and axis detector."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class FigureDetectionError(ValueError):
    """Raised when a figure fixture violates the detector contract."""


@dataclass(frozen=True)
class FigureAxis:
    """One detected axis with ticks and a classified scale."""

    source_asset_id: str
    panel_id: str
    axis_id: str
    orientation: str
    label: str | None
    scale_type: str
    tick_labels: tuple[str, ...]
    tick_positions: tuple[float, ...]
    locator: str
    confidence: float
    confidence_band: str


@dataclass(frozen=True)
class LegendEntry:
    """One legend label/style candidate."""

    source_asset_id: str
    panel_id: str
    legend_id: str
    label: str
    style: str
    locator: str
    confidence: float
    confidence_band: str


@dataclass(frozen=True)
class CurveCandidate:
    """One qualitative curve candidate; no digitized numeric values are emitted."""

    source_asset_id: str
    panel_id: str
    candidate_id: str
    label: str | None
    legend_key: str | None
    style: str | None
    path_point_count: int
    path_bbox: tuple[float, float, float, float]
    locator: str
    confidence: float
    confidence_band: str


@dataclass(frozen=True)
class UncertaintyCue:
    """One detected uncertainty/error-bar cue."""

    source_asset_id: str
    panel_id: str
    cue_id: str
    curve_label: str | None
    cue_type: str
    locator: str
    confidence: float
    confidence_band: str


@dataclass(frozen=True)
class DetectedPanel:
    """One panel with nested detector evidence."""

    source_asset_id: str
    figure_id: str
    panel_id: str
    label: str | None
    panel_type: str
    bbox: tuple[float, float, float, float]
    locator: str
    confidence: float
    confidence_band: str
    supported: bool
    axes: tuple[FigureAxis, ...]
    legend_entries: tuple[LegendEntry, ...]
    curve_candidates: tuple[CurveCandidate, ...]
    uncertainty_cues: tuple[UncertaintyCue, ...]
    review_items: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class FigureDetectionSummary:
    """Counts and output paths from one fixture run."""

    figures: int
    panels: int
    supported_panels: int
    unsupported_panels: int
    axes: int
    legend_entries: int
    curve_candidates: int
    uncertainty_cues: int
    review_items: int
    normalized_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _confidence_band(value: float) -> str:
    if value >= 0.85:
        return "HIGH"
    if value >= 0.65:
        return "MEDIUM"
    return "LOW"


def _bbox(value: Any, name: str) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise FigureDetectionError(f"{name} must contain four coordinates")
    try:
        coordinates = (
            float(value[0]),
            float(value[1]),
            float(value[2]),
            float(value[3]),
        )
    except (TypeError, ValueError) as exc:
        raise FigureDetectionError(f"{name} contains non-numeric coordinates") from exc
    if any(not 0.0 <= item <= 1.0 for item in coordinates):
        raise FigureDetectionError(f"{name} coordinates must be normalized to [0, 1]")
    left, top, right, bottom = coordinates
    if right <= left or bottom <= top:
        raise FigureDetectionError(f"{name} must have positive area")
    return coordinates


def _points(value: Any, name: str) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) < 2:
        raise FigureDetectionError(f"{name} must contain at least two points")
    points: list[tuple[float, float]] = []
    for index, point in enumerate(value):
        if not isinstance(point, list) or len(point) != 2:
            raise FigureDetectionError(f"{name}[{index}] must contain two coordinates")
        try:
            coordinates = (float(point[0]), float(point[1]))
        except (TypeError, ValueError) as exc:
            raise FigureDetectionError(f"{name}[{index}] is non-numeric") from exc
        if any(not 0.0 <= item <= 1.0 for item in coordinates):
            raise FigureDetectionError(f"{name}[{index}] must be normalized to [0, 1]")
        points.append(coordinates)
    return points


def _path_bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    return (min(x_values), min(y_values), max(x_values), max(y_values))


def _infer_scale(tick_labels: list[str], explicit: Any) -> str:
    if explicit is not None:
        scale = _text(explicit).lower()
        if scale not in {"linear", "log"}:
            raise FigureDetectionError(f"unsupported scale type: {scale}")
        return scale
    try:
        values = [float(label) for label in tick_labels]
    except ValueError:
        return "linear"
    if len(values) < 3 or any(value <= 0 for value in values):
        return "linear"
    ratios = [right / left for left, right in zip(values, values[1:], strict=False)]
    if min(ratios) >= 5.0 and max(ratios) / min(ratios) <= 1.25:
        return "log"
    return "linear"


class FigureDetector:
    """Detect panel and plot features from a validated vector-like fixture."""

    SUPPORTED_PANEL_TYPES = frozenset({"plot", "line", "bar", "scatter"})
    UNSUPPORTED_PANEL_TYPES = frozenset({"3d", "heatmap", "image_assay"})

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
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/figures/figure_detection.json"
        )
        self.normalized_path = normalized_path or self.root / "registry/figure_detection.json"
        self.review_path = review_path or self.root / "registry/figure_review_queue.jsonl"
        self.report_path = report_path or self.root / "reports/figure_detection.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FigureDetectionError(f"cannot load figure fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "figures"}:
            raise FigureDetectionError("figure detection fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["figures"], list):
            raise FigureDetectionError("figure detection fixture schema is invalid")
        figures: list[dict[str, Any]] = []
        for raw in value["figures"]:
            if not isinstance(raw, Mapping) or set(raw) != {
                "figure_id",
                "source_asset_id",
                "caption",
                "width",
                "height",
                "panels",
            }:
                raise FigureDetectionError("figure fixture fields are invalid")
            if not isinstance(raw["panels"], list) or not raw["panels"]:
                raise FigureDetectionError("figure fixture must contain panels")
            if int(raw["width"]) <= 0 or int(raw["height"]) <= 0:
                raise FigureDetectionError("figure dimensions must be positive")
            panels: list[dict[str, Any]] = []
            for panel in raw["panels"]:
                if not isinstance(panel, Mapping) or set(panel) != {
                    "panel_id",
                    "label",
                    "bbox",
                    "panel_type",
                    "elements",
                }:
                    raise FigureDetectionError("panel fixture fields are invalid")
                if not isinstance(panel["elements"], list):
                    raise FigureDetectionError("panel elements must be a list")
                for element in panel["elements"]:
                    if not isinstance(element, Mapping) or "kind" not in element:
                        raise FigureDetectionError("figure element must have a kind")
                panels.append(dict(panel))
            figure = dict(raw)
            figure["panels"] = panels
            figures.append(figure)
        return figures

    @staticmethod
    def _locator(
        source_asset_id: str,
        figure_id: str,
        panel_id: str,
        feature: str,
        ordinal: int | None = None,
    ) -> str:
        suffix = f"[{ordinal}]" if ordinal is not None else ""
        return f"asset:{source_asset_id}/figure:{figure_id}/panel:{panel_id}/{feature}{suffix}"

    def _parse_panel(
        self,
        figure: Mapping[str, Any],
        panel: Mapping[str, Any],
    ) -> DetectedPanel:
        source_asset_id = _text(figure["source_asset_id"])
        figure_id = _text(figure["figure_id"])
        panel_id = _text(panel["panel_id"])
        if not source_asset_id or not figure_id or not panel_id:
            raise FigureDetectionError("figure, asset, and panel identifiers are required")
        panel_type = _text(panel["panel_type"]).lower()
        if panel_type not in self.SUPPORTED_PANEL_TYPES | self.UNSUPPORTED_PANEL_TYPES:
            raise FigureDetectionError(f"unsupported panel classification: {panel_type}")
        label = _text(panel["label"]) or None
        bbox = _bbox(panel["bbox"], f"panel {panel_id} bbox")
        locator = self._locator(source_asset_id, figure_id, panel_id, "panel")
        supported = panel_type in self.SUPPORTED_PANEL_TYPES
        panel_confidence = 0.96 if label and supported else 0.90 if supported else 0.94
        elements = panel["elements"]
        if not isinstance(elements, list):
            raise FigureDetectionError(f"panel {panel_id} elements are invalid")

        axes: list[FigureAxis] = []
        legend_entries: list[LegendEntry] = []
        curve_candidates: list[CurveCandidate] = []
        uncertainty_cues: list[UncertaintyCue] = []
        reviews: list[Mapping[str, Any]] = []

        if not supported:
            reviews.append(
                {
                    "review_id": f"unsupported:{figure_id}:{panel_id}",
                    "reason": f"UNSUPPORTED_PANEL_TYPE_{panel_type.upper()}",
                    "source_asset_id": source_asset_id,
                    "figure_id": figure_id,
                    "panel_id": panel_id,
                    "locator": locator,
                    "confidence": panel_confidence,
                    "resolution": "MANUAL_REVIEW",
                }
            )

        for ordinal, raw_element in enumerate(elements, 1):
            if not isinstance(raw_element, Mapping):
                raise FigureDetectionError(f"panel {panel_id} element is invalid")
            kind = _text(raw_element["kind"]).lower()
            feature_locator = self._locator(source_asset_id, figure_id, panel_id, kind, ordinal)
            if kind == "axis":
                orientation = _text(raw_element.get("orientation")).lower()
                if orientation not in {"x", "y"}:
                    raise FigureDetectionError("axis orientation must be x or y")
                raw_ticks = raw_element.get("ticks")
                if not isinstance(raw_ticks, list) or len(raw_ticks) < 2:
                    raise FigureDetectionError("axis requires at least two ticks")
                tick_labels: list[str] = []
                tick_positions: list[float] = []
                for tick in raw_ticks:
                    if not isinstance(tick, Mapping):
                        raise FigureDetectionError("axis tick must be an object")
                    label_value = _text(tick.get("label"))
                    if not label_value:
                        raise FigureDetectionError("axis tick label is required")
                    try:
                        position = float(tick["position"])
                    except (KeyError, TypeError, ValueError) as exc:
                        raise FigureDetectionError("axis tick position is invalid") from exc
                    if not 0.0 <= position <= 1.0:
                        raise FigureDetectionError("axis tick position must be normalized")
                    tick_labels.append(label_value)
                    tick_positions.append(position)
                axis_label = _text(raw_element.get("label")) or None
                scale_type = _infer_scale(tick_labels, raw_element.get("scale_hint"))
                confidence = min(
                    0.99,
                    0.62 + (0.12 if axis_label else 0.0) + min(len(tick_labels), 3) * 0.08,
                )
                axes.append(
                    FigureAxis(
                        source_asset_id=source_asset_id,
                        panel_id=panel_id,
                        axis_id=f"{panel_id}:{orientation}",
                        orientation=orientation,
                        label=axis_label,
                        scale_type=scale_type,
                        tick_labels=tuple(tick_labels),
                        tick_positions=tuple(tick_positions),
                        locator=feature_locator,
                        confidence=confidence,
                        confidence_band=_confidence_band(confidence),
                    )
                )
            elif kind == "legend":
                raw_entries = raw_element.get("entries")
                if not isinstance(raw_entries, list) or not raw_entries:
                    raise FigureDetectionError("legend requires entries")
                for entry_ordinal, raw_entry in enumerate(raw_entries, 1):
                    if not isinstance(raw_entry, Mapping):
                        raise FigureDetectionError("legend entry must be an object")
                    entry_label = _text(raw_entry.get("label"))
                    if not entry_label:
                        raise FigureDetectionError("legend entry label is required")
                    style = _text(raw_entry.get("style")) or "unspecified"
                    entry_locator = f"{feature_locator}/entry[{entry_ordinal}]"
                    confidence = 0.93 if style != "unspecified" else 0.75
                    legend_entries.append(
                        LegendEntry(
                            source_asset_id=source_asset_id,
                            panel_id=panel_id,
                            legend_id=f"{panel_id}:legend:{entry_ordinal}",
                            label=entry_label,
                            style=style,
                            locator=entry_locator,
                            confidence=confidence,
                            confidence_band=_confidence_band(confidence),
                        )
                    )
            elif kind == "curve":
                curve_label = _text(raw_element.get("label")) or None
                curve_legend_key = _text(raw_element.get("legend_key")) or None
                curve_style = _text(raw_element.get("style")) or None
                path = _points(raw_element.get("path"), f"{panel_id} curve path")
                confidence = min(
                    0.96,
                    0.70 + (0.08 if curve_label else 0.0) + (0.04 if len(path) >= 3 else 0.0),
                )
                curve_candidates.append(
                    CurveCandidate(
                        source_asset_id=source_asset_id,
                        panel_id=panel_id,
                        candidate_id=f"{panel_id}:curve:{len(curve_candidates) + 1}",
                        label=curve_label,
                        legend_key=curve_legend_key,
                        style=curve_style,
                        path_point_count=len(path),
                        path_bbox=_path_bbox(path),
                        locator=feature_locator,
                        confidence=confidence,
                        confidence_band=_confidence_band(confidence),
                    )
                )
            elif kind == "error_bar":
                curve_label = _text(raw_element.get("curve_label")) or None
                cue_type = _text(raw_element.get("cue_type")) or "error_bar"
                confidence = 0.88 if curve_label else 0.72
                uncertainty_cues.append(
                    UncertaintyCue(
                        source_asset_id=source_asset_id,
                        panel_id=panel_id,
                        cue_id=f"{panel_id}:uncertainty:{len(uncertainty_cues) + 1}",
                        curve_label=curve_label,
                        cue_type=cue_type,
                        locator=feature_locator,
                        confidence=confidence,
                        confidence_band=_confidence_band(confidence),
                    )
                )
            elif kind in {"text", "caption"}:
                continue
            else:
                raise FigureDetectionError(f"unsupported figure element kind: {kind}")

        if supported and not axes:
            reviews.append(
                {
                    "review_id": f"missing-axes:{figure_id}:{panel_id}",
                    "reason": "AXES_NOT_DETECTED",
                    "source_asset_id": source_asset_id,
                    "figure_id": figure_id,
                    "panel_id": panel_id,
                    "locator": locator,
                    "confidence": 0.45,
                    "resolution": "MANUAL_REVIEW",
                }
            )
        if supported and not curve_candidates and panel_type in {"plot", "line", "scatter"}:
            reviews.append(
                {
                    "review_id": f"missing-curves:{figure_id}:{panel_id}",
                    "reason": "CURVE_CANDIDATES_NOT_DETECTED",
                    "source_asset_id": source_asset_id,
                    "figure_id": figure_id,
                    "panel_id": panel_id,
                    "locator": locator,
                    "confidence": 0.45,
                    "resolution": "MANUAL_REVIEW",
                }
            )
        return DetectedPanel(
            source_asset_id=source_asset_id,
            figure_id=figure_id,
            panel_id=panel_id,
            label=label,
            panel_type=panel_type,
            bbox=bbox,
            locator=locator,
            confidence=panel_confidence,
            confidence_band=_confidence_band(panel_confidence),
            supported=supported,
            axes=tuple(axes),
            legend_entries=tuple(legend_entries),
            curve_candidates=tuple(curve_candidates),
            uncertainty_cues=tuple(uncertainty_cues),
            review_items=tuple(reviews),
        )

    def run(self) -> FigureDetectionSummary:
        """Detect fixture features and write normalized evidence."""
        raw_figures = self._load_fixture(self.fixture_path)
        figure_results: list[dict[str, Any]] = []
        panels: list[DetectedPanel] = []
        for raw_figure in raw_figures:
            detected_panels = tuple(
                self._parse_panel(raw_figure, panel) for panel in raw_figure["panels"]
            )
            panels.extend(detected_panels)
            figure_results.append(
                {
                    "figure_id": _text(raw_figure["figure_id"]),
                    "source_asset_id": _text(raw_figure["source_asset_id"]),
                    "caption": _text(raw_figure["caption"]),
                    "panels": [asdict(panel) for panel in detected_panels],
                }
            )

        reviews = [dict(review) for panel in panels for review in panel.review_items]
        normalized = {
            "schema_version": 1,
            "fixture": True,
            "confidence_calibration": {
                "HIGH": ">=0.85",
                "MEDIUM": ">=0.65 and <0.85",
                "LOW": "<0.65",
            },
            "figures": figure_results,
            "summary": {
                "figures": len(raw_figures),
                "panels": len(panels),
                "supported_panels": sum(panel.supported for panel in panels),
                "unsupported_panels": sum(not panel.supported for panel in panels),
                "axes": sum(len(panel.axes) for panel in panels),
                "legend_entries": sum(len(panel.legend_entries) for panel in panels),
                "curve_candidates": sum(len(panel.curve_candidates) for panel in panels),
                "uncertainty_cues": sum(len(panel.uncertainty_cues) for panel in panels),
                "review_items": len(reviews),
            },
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
                    "# Figure Detection Report",
                    "",
                    "Fixture-backed detector output; no numeric digitization is performed.",
                    "",
                    f"- figures: {len(raw_figures)}",
                    f"- panels: {len(panels)}",
                    f"- supported panels: {sum(panel.supported for panel in panels)}",
                    f"- unsupported panels: {sum(not panel.supported for panel in panels)}",
                    f"- axes: {sum(len(panel.axes) for panel in panels)}",
                    f"- legend entries: {sum(len(panel.legend_entries) for panel in panels)}",
                    f"- curve candidates: {sum(len(panel.curve_candidates) for panel in panels)}",
                    f"- uncertainty cues: {sum(len(panel.uncertainty_cues) for panel in panels)}",
                    f"- review items: {len(reviews)}",
                    "",
                    "Unsupported 3D, heatmap, and image-assay panels are routed to "
                    "registry/figure_review_queue.jsonl.",
                ]
            )
            + "\n"
        )
        self.report_path.write_text(report, encoding="utf-8")
        return FigureDetectionSummary(
            figures=len(raw_figures),
            panels=len(panels),
            supported_panels=sum(panel.supported for panel in panels),
            unsupported_panels=sum(not panel.supported for panel in panels),
            axes=sum(len(panel.axes) for panel in panels),
            legend_entries=sum(len(panel.legend_entries) for panel in panels),
            curve_candidates=sum(len(panel.curve_candidates) for panel in panels),
            uncertainty_cues=sum(len(panel.uncertainty_cues) for panel in panels),
            review_items=len(reviews),
            normalized_path=self.normalized_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
