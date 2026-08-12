"""Render field-mapped protocol figures and audit them for R2 submission safety."""

from __future__ import annotations

import hashlib
import html
import json
import math
import stat
import struct
import subprocess
import textwrap
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    forbidden_terms,
    require_metadata,
)


class SubmissionFigureQAError(RuntimeError):
    """Raised when an R2 figure cannot be rendered or audited safely."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SubmissionFigureQAError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SubmissionFigureQAError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise SubmissionFigureQAError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class RenderedFigure:
    """Immutable description of one checked R2 protocol figure."""

    figure_id: str
    figure_sha256: str
    svg_path: Path
    pdf_path: Path
    png_path: Path
    source_card_path: Path
    qa_path: Path


class SubmissionFigureQAWorkflow:
    """Create non-empirical, field-mapped protocol figures for the remediation record."""

    SUITE_ID = "bioif-submission-figure-qa-r2-v1.1.0"
    RENDERED_AT = "2026-08-12T00:00:00+00:00"
    SPECS_RELATIVE = "docs/figures/R2_FIGURE_SPECS.json"
    DATA_RELATIVE = "docs/figures/R2_PROTOCOL_FIGURE_DATA.json"
    REQUIRED_MAPPINGS = {
        "node_id": "nodes[].node_id",
        "node_label": "nodes[].label_lines[]",
        "node_geometry": "nodes[].x,y,width,height",
        "edge_source": "edges[].source",
        "edge_target": "edges[].target",
    }
    REQUIRED_DENOMINATOR = {
        "independent_unit": "NOT_APPLICABLE",
        "n": "NOT_APPLICABLE",
        "interval_method": "NOT_APPLICABLE",
    }
    WIDTH = 960
    HEIGHT = 540
    MARGIN = 24
    FONT_SIZE = 16
    TITLE_SIZE = 25
    SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"

    def __init__(
        self,
        root: Path,
        *,
        specs_path: Path | None = None,
        output_root: Path | None = None,
        converter: str = "rsvg-convert",
    ) -> None:
        self.root = root.resolve(strict=True)
        self.specs_path = specs_path or self.root / self.SPECS_RELATIVE
        self.output_root = output_root or (
            self.root / "reports/review_round_2/submission_figures/v1.1.0"
        )
        self.converter = converter

    def _path(self, relative_path: str, label: str) -> Path:
        path = (self.root / relative_path).resolve(strict=False)
        if not path.is_relative_to(self.root):
            raise SubmissionFigureQAError(f"{label} escaped repository")
        if "data/locked_test" in path.as_posix():
            raise SubmissionFigureQAError(f"protected payload path is forbidden: {label}")
        if not path.is_file():
            raise SubmissionFigureQAError(f"{label} is missing: {relative_path}")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SubmissionFigureQAError(f"cannot parse {label}") from exc
        return _mapping(value, label)

    def _load_specs(self) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
        specs_path = self.specs_path.resolve(strict=False)
        if not specs_path.is_relative_to(self.root) or not specs_path.is_file():
            raise SubmissionFigureQAError("R2 figure specification is missing")
        specs = self._json(specs_path, "R2 figure specification")
        if specs.get("schema_version") != 1 or specs.get("suite_id") != self.SUITE_ID:
            raise SubmissionFigureQAError("R2 figure specification identity is invalid")
        try:
            evidence_class, claim_level = require_metadata(specs, "R2 figure specification")
        except EvidenceSemanticsError as exc:
            raise SubmissionFigureQAError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.SOFTWARE_REPLAY
            or claim_level is not AllowedClaimLevel.SOFTWARE_REPLAY
        ):
            raise SubmissionFigureQAError("R2 figure suite must be software-replay only")
        figures = specs.get("figures")
        if not isinstance(figures, list) or len(figures) != 3:
            raise SubmissionFigureQAError("R2 figure suite must declare exactly three figures")
        return specs_path, specs, [_mapping(row, "R2 figure") for row in figures]

    def _load_data(self) -> tuple[Path, dict[str, Any], dict[str, dict[str, Any]]]:
        data_path = self._path(self.DATA_RELATIVE, "R2 protocol figure data")
        data = self._json(data_path, "R2 protocol figure data")
        if (
            data.get("schema_version") != 1
            or data.get("data_id") != "bioif-r2-protocol-flow-v1.1.0"
        ):
            raise SubmissionFigureQAError("R2 protocol figure data identity is invalid")
        try:
            evidence_class, claim_level = require_metadata(data, "R2 protocol figure data")
        except EvidenceSemanticsError as exc:
            raise SubmissionFigureQAError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.SOFTWARE_REPLAY
            or claim_level is not AllowedClaimLevel.SOFTWARE_REPLAY
        ):
            raise SubmissionFigureQAError("R2 protocol figure data must be software-replay only")
        flows = data.get("flows")
        if not isinstance(flows, dict) or len(flows) != 3:
            raise SubmissionFigureQAError("R2 protocol figure data must declare three flows")
        return data_path, data, {key: _mapping(value, "R2 flow") for key, value in flows.items()}

    @staticmethod
    def _bounded_number(value: Any, label: str) -> float:
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise SubmissionFigureQAError(f"{label} must be numeric")
        result = float(value)
        if not math.isfinite(result):
            raise SubmissionFigureQAError(f"{label} must be finite")
        return result

    def _validate_figure(
        self,
        figure: dict[str, Any],
        flows: dict[str, dict[str, Any]],
        data_path: Path,
    ) -> tuple[str, dict[str, Any]]:
        required = {
            "figure_id",
            "title",
            "caption",
            "publication_status",
            "evidence_class",
            "allowed_claim_level",
            "source",
            "field_mapping",
            "denominator",
            "axes",
        }
        if set(figure) != required:
            raise SubmissionFigureQAError("R2 figure fields are invalid")
        figure_id = _string(figure["figure_id"], "R2 figure ID")
        if figure["publication_status"] != "PROTOCOL_ONLY":
            raise SubmissionFigureQAError(f"{figure_id} is not protocol-only")
        try:
            evidence_class, claim_level = require_metadata(figure, figure_id)
        except EvidenceSemanticsError as exc:
            raise SubmissionFigureQAError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.SOFTWARE_REPLAY
            or claim_level is not AllowedClaimLevel.SOFTWARE_REPLAY
        ):
            raise SubmissionFigureQAError(f"{figure_id} evidence class is unsafe")
        semantic_text = " ".join(
            [_string(figure["title"], "R2 figure title"), _string(figure["caption"], "R2 caption")]
        )
        if len(textwrap.wrap(_string(figure["caption"], "R2 caption"), width=108)) > 2:
            raise SubmissionFigureQAError(f"{figure_id} caption would clip")
        prohibited = forbidden_terms(semantic_text, EvidenceClass.SOFTWARE_REPLAY)
        if prohibited:
            raise SubmissionFigureQAError(f"{figure_id} has forbidden evidence wording")
        source = _mapping(figure["source"], f"{figure_id} source")
        if set(source) != {"path", "sha256", "flow_id"}:
            raise SubmissionFigureQAError(f"{figure_id} source declaration is invalid")
        if _string(source["path"], f"{figure_id} source path") != self.DATA_RELATIVE:
            raise SubmissionFigureQAError(f"{figure_id} source path is not the R2 data card")
        if _string(source["sha256"], f"{figure_id} source checksum") != _sha256(data_path):
            raise SubmissionFigureQAError(f"{figure_id} source checksum differs")
        flow_id = _string(source["flow_id"], f"{figure_id} flow ID")
        if flow_id not in flows:
            raise SubmissionFigureQAError(f"{figure_id} flow is missing")
        mapping = _mapping(figure["field_mapping"], f"{figure_id} field mapping")
        if mapping != self.REQUIRED_MAPPINGS:
            raise SubmissionFigureQAError(f"{figure_id} field mapping is incomplete or implicit")
        denominator = _mapping(figure["denominator"], f"{figure_id} denominator")
        if denominator != self.REQUIRED_DENOMINATOR:
            raise SubmissionFigureQAError(
                f"{figure_id} denominator or interval declaration is invalid"
            )
        axes = _mapping(figure["axes"], f"{figure_id} axes")
        if axes != {"x_unit": "NOT_APPLICABLE", "y_unit": "NOT_APPLICABLE"}:
            raise SubmissionFigureQAError(f"{figure_id} axis units are invalid")
        return figure_id, flows[flow_id]

    def _geometry(self, figure_id: str, flow: dict[str, Any]) -> dict[str, Any]:
        if set(flow) != {"nodes", "edges"}:
            raise SubmissionFigureQAError(f"{figure_id} flow fields are invalid")
        nodes = flow["nodes"]
        edges = flow["edges"]
        if not isinstance(nodes, list) or not isinstance(edges, list) or not nodes:
            raise SubmissionFigureQAError(f"{figure_id} flow has no nodes or edges")
        boxes: dict[str, tuple[float, float, float, float]] = {}
        line_height = self.FONT_SIZE * 1.25
        for value in nodes:
            node = _mapping(value, f"{figure_id} node")
            if set(node) != {"node_id", "label_lines", "x", "y", "width", "height", "style"}:
                raise SubmissionFigureQAError(f"{figure_id} node fields are invalid")
            node_id = _string(node["node_id"], f"{figure_id} node ID")
            if node_id in boxes:
                raise SubmissionFigureQAError(f"{figure_id} node ID is duplicated")
            lines = node["label_lines"]
            if (
                not isinstance(lines, list)
                or not lines
                or not all(isinstance(item, str) for item in lines)
            ):
                raise SubmissionFigureQAError(f"{figure_id} node label lines are invalid")
            x = self._bounded_number(node["x"], f"{figure_id} node x")
            y = self._bounded_number(node["y"], f"{figure_id} node y")
            width = self._bounded_number(node["width"], f"{figure_id} node width")
            height = self._bounded_number(node["height"], f"{figure_id} node height")
            if (
                x < self.MARGIN
                or y < 92
                or width < 120
                or height < 56
                or x + width > self.WIDTH - self.MARGIN
                or y + height > self.HEIGHT - 76
            ):
                raise SubmissionFigureQAError(f"{figure_id} node geometry is out of bounds")
            if max(len(line) * self.FONT_SIZE * 0.56 for line in lines) > width - 20:
                raise SubmissionFigureQAError(f"{figure_id} node label would clip horizontally")
            if len(lines) * line_height > height - 18:
                raise SubmissionFigureQAError(f"{figure_id} node label would clip vertically")
            if _string(node["style"], f"{figure_id} node style") not in {
                "input",
                "process",
                "gate",
                "output",
                "blocked",
            }:
                raise SubmissionFigureQAError(f"{figure_id} node style is invalid")
            boxes[node_id] = (x, y, width, height)
        for first, second in combinations(boxes.items(), 2):
            first_id, (x1, y1, w1, h1) = first
            second_id, (x2, y2, w2, h2) = second
            if x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2:
                raise SubmissionFigureQAError(
                    f"{figure_id} nodes overlap: {first_id} and {second_id}"
                )
        seen_edges: set[tuple[str, str]] = set()
        for value in edges:
            edge = _mapping(value, f"{figure_id} edge")
            if set(edge) != {"source", "target", "label"}:
                raise SubmissionFigureQAError(f"{figure_id} edge fields are invalid")
            source = _string(edge["source"], f"{figure_id} edge source")
            target = _string(edge["target"], f"{figure_id} edge target")
            if source not in boxes or target not in boxes or source == target:
                raise SubmissionFigureQAError(f"{figure_id} edge endpoint is invalid")
            if (source, target) in seen_edges:
                raise SubmissionFigureQAError(f"{figure_id} edge is duplicated")
            if len(_string(edge["label"], f"{figure_id} edge label")) > 28:
                raise SubmissionFigureQAError(f"{figure_id} edge label is too long")
            seen_edges.add((source, target))
        if not seen_edges:
            raise SubmissionFigureQAError(f"{figure_id} flow has no edges")
        return {
            "status": "PASS_AUTOMATED_GEOMETRY",
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "margin": self.MARGIN,
            "font_size": self.FONT_SIZE,
            "node_count": len(boxes),
            "edge_count": len(seen_edges),
            "overlaps": 0,
            "out_of_bounds": 0,
            "label_clipping": 0,
        }

    @staticmethod
    def _style_color(style: str) -> tuple[str, str]:
        colors = {
            "input": ("#DCEAF7", "#0072B2"),
            "process": ("#E5F4E8", "#009E73"),
            "gate": ("#FFF1D4", "#E69F00"),
            "output": ("#EAE4F4", "#6A3D9A"),
            "blocked": ("#FBE2E2", "#D55E00"),
        }
        return colors[style]

    def _svg(self, figure: dict[str, Any], flow: dict[str, Any]) -> str:
        figure_id = _string(figure["figure_id"], "R2 figure ID")
        title = _string(figure["title"], "R2 figure title")
        caption = _string(figure["caption"], "R2 figure caption")
        caption_lines = textwrap.wrap(caption, width=108)
        nodes = [_mapping(item, "R2 node") for item in flow["nodes"]]
        edges = [_mapping(item, "R2 edge") for item in flow["edges"]]
        node_by_id = {str(node["node_id"]): node for node in nodes}
        body = [
            '<svg xmlns="http://www.w3.org/2000/svg" width="160mm" height="90mm" '
            f'viewBox="0 0 {self.WIDTH} {self.HEIGHT}" role="img">',
            f"<title>{html.escape(title)}</title>",
            (
                "<desc>Protocol-only diagram from declared nodes and edges; "
                "no empirical values.</desc>"
            ),
            '<rect x="0" y="0" width="960" height="540" fill="#FFFFFF"/>',
            self._text(32, 40, figure_id, 15, "#374151", "bold"),
            self._text(32, 70, title, self.TITLE_SIZE, "#111827", "bold"),
            self._text(
                928,
                38,
                "PROTOCOL / SOFTWARE REPLAY ONLY",
                13,
                "#374151",
                "bold",
                anchor="end",
            ),
            '<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" '
            'orient="auto"><path d="M0,0 L10,3.5 L0,7 z" fill="#374151"/></marker></defs>',
        ]
        for edge in edges:
            source = node_by_id[str(edge["source"])]
            target = node_by_id[str(edge["target"])]
            sx = float(source["x"]) + float(source["width"])
            sy = float(source["y"]) + float(source["height"]) / 2
            tx = float(target["x"])
            ty = float(target["y"]) + float(target["height"]) / 2
            if tx < sx:
                sx = float(source["x"]) + float(source["width"]) / 2
                sy = float(source["y"]) + float(source["height"])
                tx = float(target["x"]) + float(target["width"]) / 2
                ty = float(target["y"])
            label_x = (sx + tx) / 2
            label_y = (sy + ty) / 2 - 7
            body.append(
                f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                'stroke="#374151" stroke-width="2" marker-end="url(#arrow)"/>'
            )
            body.append(self._text(label_x, label_y, str(edge["label"]), 12, "#374151", "normal"))
        for node in nodes:
            fill, stroke = self._style_color(str(node["style"]))
            x = float(node["x"])
            y = float(node["y"])
            width = float(node["width"])
            height = float(node["height"])
            body.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
                f'rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            )
            lines = [str(item) for item in node["label_lines"]]
            first_y = y + height / 2 - (len(lines) - 1) * 10
            for index, line in enumerate(lines):
                body.append(
                    self._text(
                        x + width / 2,
                        first_y + index * 20 + 6,
                        line,
                        self.FONT_SIZE,
                        "#111827",
                        "bold" if index == 0 else "normal",
                        anchor="middle",
                    )
                )
        body.extend(
            [
                '<line x1="32" y1="474" x2="928" y2="474" stroke="#D1D5DB" stroke-width="1"/>',
            ]
        )
        for index, line in enumerate(caption_lines):
            body.append(self._text(32, 496 + index * 17, line, 13, "#374151", "normal"))
        body.extend(
            [
                self._text(
                    32,
                    533,
                    (
                        "Units, n and intervals: not applicable "
                        "(protocol diagram; no measured summary)."
                    ),
                    12,
                    "#4B5563",
                    "normal",
                ),
                "</svg>",
            ]
        )
        return "\n".join(body) + "\n"

    @staticmethod
    def _text(
        x: float,
        y: float,
        text: str,
        size: int,
        fill: str,
        weight: str,
        *,
        anchor: str = "start",
    ) -> str:
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size}px" '
            f'font-weight="{weight}" fill="{fill}">{html.escape(text)}</text>'
        )

    def _convert(self, svg: Path, png: Path, pdf: Path) -> None:
        try:
            subprocess.run(
                [self.converter, "--dpi-x", "600", "--dpi-y", "600", "-o", str(png), str(svg)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [self.converter, "-f", "pdf", "-o", str(pdf), str(svg)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SubmissionFigureQAError("SVG/PDF/PNG conversion failed") from exc

    @staticmethod
    def _png_dimensions(path: Path) -> tuple[int, int]:
        raw = path.read_bytes()
        if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
            raise SubmissionFigureQAError("PNG output is invalid")
        return struct.unpack(">II", raw[16:24])

    def _svg_geometry_audit(self, path: Path) -> dict[str, int]:
        try:
            root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ElementTree.ParseError) as exc:
            raise SubmissionFigureQAError("SVG output is invalid") from exc
        if root.attrib.get("viewBox") != f"0 0 {self.WIDTH} {self.HEIGHT}":
            raise SubmissionFigureQAError("SVG viewBox is invalid")
        rect_count = 0
        text_count = 0
        for rect in root.findall(f"{self.SVG_NAMESPACE}rect"):
            x = float(rect.attrib["x"])
            y = float(rect.attrib["y"])
            width = float(rect.attrib["width"])
            height = float(rect.attrib["height"])
            if x < 0 or y < 0 or width <= 0 or height <= 0:
                raise SubmissionFigureQAError("SVG has invalid rectangle geometry")
            if x + width > self.WIDTH or y + height > self.HEIGHT:
                raise SubmissionFigureQAError("SVG rectangle clips outside viewBox")
            rect_count += 1
        for text in root.findall(f"{self.SVG_NAMESPACE}text"):
            x = float(text.attrib["x"])
            y = float(text.attrib["y"])
            size = float(text.attrib["font-size"].removesuffix("px"))
            if not 0 <= x <= self.WIDTH or not size <= y <= self.HEIGHT:
                raise SubmissionFigureQAError("SVG text anchor clips outside viewBox")
            if size < 12:
                raise SubmissionFigureQAError("SVG text is below the minimum size")
            text_count += 1
        return {"rectangles": rect_count, "text_elements": text_count}

    def _audit_figure(
        self,
        figure: dict[str, Any],
        flow: dict[str, Any],
        svg: Path,
        png: Path,
        geometry: dict[str, Any],
    ) -> dict[str, Any]:
        figure_id = _string(figure["figure_id"], "R2 figure ID")
        svg_metrics = self._svg_geometry_audit(svg)
        png_width, png_height = self._png_dimensions(png)
        if png_width < 3000 or png_height < 1500:
            raise SubmissionFigureQAError(f"{figure_id} PNG is below submission raster dimensions")
        semantic_text = " ".join(
            [
                _string(figure["title"], "R2 title"),
                _string(figure["caption"], "R2 caption"),
                svg.read_text(encoding="utf-8"),
            ]
        )
        if forbidden_terms(semantic_text, EvidenceClass.SOFTWARE_REPLAY):
            raise SubmissionFigureQAError(f"{figure_id} semantic evidence audit failed")
        return {
            "schema_version": 1,
            "suite_id": self.SUITE_ID,
            "figure_id": figure_id,
            "status": "PASS_FIELD_MAPPED_PROTOCOL_FIGURE_QA",
            "geometry": {**geometry, **svg_metrics},
            "semantic": {
                "evidence_class": "SOFTWARE_REPLAY",
                "allowed_claim_level": "SOFTWARE_REPLAY",
                "publication_status": "PROTOCOL_ONLY",
                "forbidden_terms": [],
                "empirical_values_rendered": False,
                "statistical_summary_rendered": False,
            },
            "raster": {
                "png_width": png_width,
                "png_height": png_height,
                "dpi": 600,
                "minimum_submission_dimensions_passed": True,
            },
            "visual_review": {
                "automated_layout": "PASS",
                "manual_review_scope": "agent visual inspection required before T119 closeout",
                "human_submission_signoff": "NOT_APPLICABLE_TO_PROTOCOL_ONLY_R2_FIGURES",
            },
            "source_fields": self.REQUIRED_MAPPINGS,
            "flow_node_count": len(flow["nodes"]),
        }

    def _withdrawal_ledger(self) -> list[dict[str, str]]:
        ledger: list[dict[str, str]] = []
        for paper in ("paper_a", "paper_b", "paper_c_prelock"):
            manifest_path = self._path(
                f"release/manuscripts/{paper}/figure_manifest.json",
                f"{paper} legacy figure manifest",
            )
            manifest = self._json(manifest_path, f"{paper} legacy figure manifest")
            figures = manifest.get("figures")
            if not isinstance(figures, list):
                raise SubmissionFigureQAError(f"{paper} legacy figure manifest is invalid")
            for figure in figures:
                row = _mapping(figure, "legacy figure")
                ledger.append(
                    {
                        "legacy_figure": (
                            f"{paper}:{_string(row.get('figure_id'), 'legacy figure ID')}"
                        ),
                        "status": "WITHDRAWN_FROM_R2_SUBMISSION_SCOPE",
                        "reason": (
                            "Historical fixture specification lacks a field-mapped "
                            "empirical source, independent-unit denominator, interval declaration, "
                            "and R2 visual QA receipt."
                        ),
                        "replacement": (
                            "R2 protocol-only figures; real-data figures are deferred to T122-T124."
                        ),
                    }
                )
        if len(ledger) != 15:
            raise SubmissionFigureQAError("legacy withdrawal ledger coverage is incomplete")
        return ledger

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise SubmissionFigureQAError("T119 requires --strict")
        if self.output_root.exists():
            raise SubmissionFigureQAError("R2 figure suite already executed; overwrite refused")
        specs_path, specs, figures = self._load_specs()
        data_path, _, flows = self._load_data()
        self.output_root.mkdir(parents=True, exist_ok=False)
        figure_root = self.output_root / "figures"
        source_root = self.output_root / "source_cards"
        qa_root = self.output_root / "qa"
        rendered: list[RenderedFigure] = []
        output_paths: list[Path] = []
        seen_figure_ids: set[str] = set()
        for figure in figures:
            figure_id, flow = self._validate_figure(figure, flows, data_path)
            if figure_id in seen_figure_ids:
                raise SubmissionFigureQAError("R2 figure ID is duplicated")
            seen_figure_ids.add(figure_id)
            geometry = self._geometry(figure_id, flow)
            stem = figure_id.lower().replace(" ", "_")
            svg = figure_root / f"{stem}.svg"
            png = figure_root / f"{stem}.png"
            pdf = figure_root / f"{stem}.pdf"
            svg.parent.mkdir(parents=True, exist_ok=True)
            svg.write_text(self._svg(figure, flow), encoding="utf-8")
            self._convert(svg, png, pdf)
            source_card_path = source_root / f"{stem}.json"
            source_card_path.parent.mkdir(parents=True, exist_ok=True)
            source_card_path.write_bytes(
                _canonical(
                    {
                        "schema_version": 1,
                        "suite_id": self.SUITE_ID,
                        "figure_id": figure_id,
                        "spec_path": str(specs_path.relative_to(self.root)),
                        "spec_sha256": _sha256(specs_path),
                        "source_path": str(data_path.relative_to(self.root)),
                        "source_sha256": _sha256(data_path),
                        "flow_id": figure["source"]["flow_id"],
                        "field_mapping": figure["field_mapping"],
                        "denominator": figure["denominator"],
                        "axes": figure["axes"],
                    }
                )
            )
            qa_path = qa_root / f"{stem}.json"
            qa_path.parent.mkdir(parents=True, exist_ok=True)
            qa_path.write_bytes(_canonical(self._audit_figure(figure, flow, svg, png, geometry)))
            rendered.append(
                RenderedFigure(
                    figure_id=figure_id,
                    figure_sha256=_sha256(svg),
                    svg_path=svg,
                    pdf_path=pdf,
                    png_path=png,
                    source_card_path=source_card_path,
                    qa_path=qa_path,
                )
            )
            output_paths.extend([svg, png, pdf, source_card_path, qa_path])
        withdrawal_path = self.output_root / "withdrawal_ledger.json"
        withdrawal_path.write_bytes(
            _canonical({"schema_version": 1, "withdrawals": self._withdrawal_ledger()})
        )
        output_paths.append(withdrawal_path)
        manifest = {
            "schema_version": 1,
            "suite_id": self.SUITE_ID,
            "rendered_at": self.RENDERED_AT,
            "evidence_class": "SOFTWARE_REPLAY",
            "allowed_claim_level": "SOFTWARE_REPLAY",
            "publication_status": "PROTOCOL_ONLY",
            "figures": [
                {
                    "figure_id": item.figure_id,
                    "svg": str(item.svg_path.relative_to(self.output_root)),
                    "pdf": str(item.pdf_path.relative_to(self.output_root)),
                    "png_600dpi": str(item.png_path.relative_to(self.output_root)),
                    "source_card": str(item.source_card_path.relative_to(self.output_root)),
                    "qa": str(item.qa_path.relative_to(self.output_root)),
                    "svg_sha256": item.figure_sha256,
                }
                for item in rendered
            ],
            "withdrawn_historical_figure_count": 15,
            "scientific_submission_ready": False,
        }
        manifest_path = self.output_root / "figure_manifest.json"
        manifest_path.write_bytes(_canonical(manifest))
        output_paths.append(manifest_path)
        output_hashes = {
            str(path.relative_to(self.output_root)): _sha256(path) for path in sorted(output_paths)
        }
        receipt = {
            "schema_version": 1,
            "suite_id": self.SUITE_ID,
            "status": "PASS_R2_PROTOCOL_FIGURE_SUITE",
            "rendered_at": self.RENDERED_AT,
            "figure_count": len(rendered),
            "withdrawn_historical_figure_count": 15,
            "raster_dpi": 600,
            "field_mapped": True,
            "geometry_qa": "PASS",
            "semantic_qa": "PASS",
            "empirical_values_rendered": False,
            "scientific_submission_ready": False,
            "output_hashes": output_hashes,
        }
        receipt_path = self.output_root / "generation_receipt.json"
        receipt_path.write_bytes(_canonical(receipt))
        output_paths.append(receipt_path)
        for path in output_paths:
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        for directory in sorted({path.parent for path in output_paths}, reverse=True):
            directory.chmod(
                stat.S_IRUSR
                | stat.S_IXUSR
                | stat.S_IRGRP
                | stat.S_IXGRP
                | stat.S_IROTH
                | stat.S_IXOTH
            )
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return receipt

    def verify(self) -> dict[str, Any]:
        receipt_path = self.output_root / "generation_receipt.json"
        manifest_path = self.output_root / "figure_manifest.json"
        if not receipt_path.is_file() or not manifest_path.is_file():
            raise SubmissionFigureQAError("R2 figure receipt or manifest is missing")
        receipt = self._json(receipt_path, "R2 figure receipt")
        manifest = self._json(manifest_path, "R2 figure manifest")
        if (
            receipt.get("suite_id") != self.SUITE_ID
            or receipt.get("status") != "PASS_R2_PROTOCOL_FIGURE_SUITE"
            or receipt.get("figure_count") != 3
            or receipt.get("withdrawn_historical_figure_count") != 15
            or receipt.get("field_mapped") is not True
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise SubmissionFigureQAError("R2 figure receipt boundary is invalid")
        if (
            manifest.get("publication_status") != "PROTOCOL_ONLY"
            or len(manifest.get("figures", [])) != 3
        ):
            raise SubmissionFigureQAError("R2 figure manifest boundary is invalid")
        output_hashes = _mapping(receipt.get("output_hashes"), "R2 output hashes")
        for relative, expected in output_hashes.items():
            path = self.output_root / _string(relative, "R2 output path")
            if not path.is_file() or _sha256(path) != _string(expected, "R2 output checksum"):
                raise SubmissionFigureQAError(f"R2 figure output hash differs: {relative}")
        for item in manifest["figures"]:
            row = _mapping(item, "R2 manifest figure")
            qa_path = self.output_root / _string(row["qa"], "R2 QA path")
            qa = self._json(qa_path, "R2 QA report")
            if qa.get("status") != "PASS_FIELD_MAPPED_PROTOCOL_FIGURE_QA":
                raise SubmissionFigureQAError("R2 figure QA is not passing")
        return receipt
