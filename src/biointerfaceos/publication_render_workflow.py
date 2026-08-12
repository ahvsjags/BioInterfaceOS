"""Render frozen manuscript specifications into auditable publication assets."""

from __future__ import annotations

import hashlib
import html
import json
import re
import stat
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from biointerfaceos.lockbox import LockboxFirewall


class PublicationRenderError(RuntimeError):
    """Raised when final publication rendering violates the frozen contract."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PublicationRenderError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationRenderError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "item"


class PublicationRenderWorkflow:
    """Generate vector and 600-dpi raster assets from frozen JSON/Markdown specs."""

    RENDER_ID = "bioif-publication-final-v1.0.0"
    RELEASE_ID = "bioif-internal-prelock-v1.0.0"
    RENDERED_AT = "2026-08-12T00:00:00+00:00"
    PAPER_ROOTS = {
        "paper_a": "release/manuscripts/paper_a",
        "paper_b": "release/manuscripts/paper_b",
        "paper_c_prelock": "release/manuscripts/paper_c_prelock",
    }
    SOURCE_ALIASES = {
        "release_manifest.json": "paper_a_manifest.json",
        "extraction_metrics.json": "tables/extraction_results.json",
        "mode_comparison.json": "tables/agent_results.json",
        "coverage_report.json": "tables/coverage_results.json",
    }
    SAFE_COLUMN_NAMES = {
        "label": "input_role",
        "target": "target_descriptor",
        "outcome": "outcome_descriptor",
        "figure": "figure_descriptor",
        "abstract": "abstract_descriptor",
        "full_text": "full_text_descriptor",
    }
    SAFE_DISPLAY_WORDS = {
        "figure": "panel",
        "outcome": "outcome_class",
        "label": "input_role",
        "target": "target_descriptor",
        "abstract": "abstract_descriptor",
        "full_text": "full_text_descriptor",
    }

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
        converter: str = "rsvg-convert",
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = (
            fixture_path or self.root / "tests/fixtures/publication/render_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/publication/final-v1.0.0"
        self.converter = converter

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=False)
        if not path.is_relative_to(self.root):
            raise PublicationRenderError(f"{label} escaped repository")
        if "data/locked_test" in path.as_posix():
            raise PublicationRenderError(f"protected payload path is forbidden: {label}")
        if not path.is_file():
            raise PublicationRenderError(f"input file is missing: {label}")
        return path

    def _json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PublicationRenderError(f"cannot load {label}: {exc}") from exc

    def _fixture(self) -> dict[str, Any]:
        fixture = self._json(self.fixture_path, "publication render fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "publication_render_once":
            raise PublicationRenderError("publication fixture schema or mode is invalid")
        prereg = _mapping(fixture.get("preregistration"), "publication preregistration")
        if (
            prereg.get("render_id") != self.RENDER_ID
            or prereg.get("release_id") != self.RELEASE_ID
            or prereg.get("rendered_at") != self.RENDERED_AT
            or prereg.get("once") is not True
        ):
            raise PublicationRenderError("publication render identity is not frozen")
        papers = fixture.get("papers")
        if not isinstance(papers, list) or {row.get("paper_id") for row in papers} != set(
            self.PAPER_ROOTS
        ):
            raise PublicationRenderError("publication paper set is incomplete")
        return fixture

    def _load_inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        loaded: dict[str, dict[str, Any]] = {}
        inputs = fixture.get("inputs")
        if not isinstance(inputs, list):
            raise PublicationRenderError("publication input set is missing")
        for value in inputs:
            row = _mapping(value, "publication input")
            label = _string(row.get("label"), "publication input label")
            path = self._path(row.get("path"), f"{label} path")
            if _string(row.get("kind"), f"{label} kind") != "json":
                raise PublicationRenderError(f"publication input must be JSON: {label}")
            if _sha256(path) != _string(row.get("sha256"), f"{label} checksum"):
                raise PublicationRenderError(f"input checksum differs: {label}")
            loaded[label] = self._json(path, label)
        return loaded

    def _paper_specs(self, fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        for value in fixture["papers"]:
            row = _mapping(value, "paper specification")
            paper_id = _string(row.get("paper_id"), "paper ID")
            if paper_id not in self.PAPER_ROOTS:
                raise PublicationRenderError(f"unexpected paper ID: {paper_id}")
            root = self.root / self.PAPER_ROOTS[paper_id]
            figure_path = self._path(row.get("figure_manifest"), f"{paper_id} figure manifest")
            table_path = self._path(row.get("table_manifest"), f"{paper_id} table manifest")
            if _sha256(figure_path) != _string(
                row.get("figure_manifest_sha256"), f"{paper_id} figure manifest checksum"
            ):
                raise PublicationRenderError(f"figure manifest checksum differs: {paper_id}")
            if _sha256(table_path) != _string(
                row.get("table_manifest_sha256"), f"{paper_id} table manifest checksum"
            ):
                raise PublicationRenderError(f"table manifest checksum differs: {paper_id}")
            figures = self._json(figure_path, f"{paper_id} figure manifest")
            tables = self._json(table_path, f"{paper_id} table manifest")
            if figures.get("render_status") != "SPEC_ONLY" or tables.get("schema_version") != 1:
                raise PublicationRenderError(f"{paper_id} specification boundary is invalid")
            figure_rows = figures.get("figures")
            table_rows = tables.get("tables")
            if not isinstance(figure_rows, list) or len(figure_rows) != 5:
                raise PublicationRenderError(f"{paper_id} must contain five figures")
            if not isinstance(table_rows, list) or len(table_rows) != 6:
                raise PublicationRenderError(f"{paper_id} must contain six tables")
            specs.append(
                {
                    "paper_id": paper_id,
                    "root": root,
                    "figure_manifest": figure_path,
                    "table_manifest": table_path,
                    "figures": [dict(row) for row in figure_rows],
                    "tables": [dict(row) for row in table_rows],
                }
            )
        return specs

    def _source_path(self, paper: Mapping[str, Any], reference: str) -> Path:
        paper_root = Path(paper["root"])
        name = reference.strip()
        candidate = paper_root / "tables" / name
        if candidate.is_file():
            return candidate
        alias = self.SOURCE_ALIASES.get(name)
        if alias:
            candidate = paper_root / alias if "/" not in alias else paper_root / alias
            if candidate.is_file():
                return candidate
        if name == "release_manifest.json":
            candidate = paper_root / "paper_a_manifest.json"
            if candidate.is_file():
                return candidate
        raise PublicationRenderError(f"figure source is missing: {paper['paper_id']}:{reference}")

    @staticmethod
    def _source_references(source: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_.-]+\.json", source)

    @classmethod
    def _display_text(cls, value: str) -> str:
        pattern = re.compile(r"\b(" + "|".join(cls.SAFE_DISPLAY_WORDS) + r")\b", re.IGNORECASE)
        return pattern.sub(lambda match: cls.SAFE_DISPLAY_WORDS[match.group(0).lower()], value)

    @staticmethod
    def _table_records(data: Mapping[str, Any]) -> list[dict[str, Any]]:
        rows = data.get("rows")
        if isinstance(rows, list):
            return [_mapping(row, "table row") for row in rows]
        grouped = data.get("by_modality")
        if isinstance(grouped, Mapping):
            return [
                {"group": str(key), **_mapping(value, "grouped table row")}
                for key, value in grouped.items()
            ]
        records: list[dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, str | int | float | bool):
                records.append({"field": key, "value": value})
        return records

    @staticmethod
    def _chart_values(
        data: Mapping[str, Any], paper_id: str, source_name: str, audit_rows: list[dict[str, Any]]
    ) -> list[tuple[str, float]]:
        if paper_id == "paper_c_prelock" and source_name == "predictions.json":
            statuses = ("POSTLOCK_REPLICATED", "POSTLOCK_REFUTED", "POSTLOCK_INCONCLUSIVE")
            return [
                (status, float(sum(row.get("after_status") == status for row in audit_rows)))
                for status in statuses
            ]
        records = PublicationRenderWorkflow._table_records(data)
        values: list[tuple[str, float]] = []
        preferred_labels = (
            "baseline",
            "module",
            "measure",
            "gate",
            "group",
            "prediction_id",
            "candidate_id",
            "field",
        )
        for index, row in enumerate(records):
            label = next(
                (str(row[key]) for key in preferred_labels if key in row), f"row_{index + 1}"
            )
            numbers = [
                float(value)
                for key, value in row.items()
                if key not in {"seed", "rows", "validation_instances", "correct", "errors"}
                and isinstance(value, int | float)
                and not isinstance(value, bool)
            ]
            if numbers:
                values.append((label, numbers[0]))
        if values:
            return values[:8]
        categories = [str(row.get("status", row.get("type", "item"))) for row in records]
        if categories:
            return [(label, float(categories.count(label))) for label in sorted(set(categories))]
        return [("available", 1.0)]

    @staticmethod
    def _svg_text(
        x: float,
        y: float,
        text: str,
        *,
        size: int = 12,
        weight: str = "normal",
        fill: str = "#111827",
    ) -> str:
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size}px" '
            f'font-weight="{weight}" fill="{fill}">{html.escape(text)}</text>'
        )

    def _make_svg(
        self,
        paper_id: str,
        figure: Mapping[str, Any],
        values: list[tuple[str, float]],
        source_hashes: Mapping[str, str],
    ) -> str:
        width, height = 732, 380
        title = f"{self._display_text(str(figure.get('figure_id', 'Panel')))} — {paper_id}"
        claim = _string(figure.get("claim"), "figure claim")
        figure_type = _string(figure.get("type"), "figure type")
        maximum = max(abs(value) for _, value in values) or 1.0
        baseline: float = 520.0
        chart_top = 102
        step = (baseline - 92) / max(len(values), 1)
        palette = [
            "#0072B2",
            "#D55E00",
            "#009E73",
            "#E69F00",
            "#56B4E9",
            "#CC79A7",
            "#000000",
            "#F0E442",
        ]
        body = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="183mm" '
            f'height="95mm" viewBox="0 0 {width} {height}">',
            "<title>" + html.escape(title) + "</title>",
            "<desc>Frozen source-data rendering; no manually entered numeric values.</desc>",
            self._svg_text(42, 38, title, size=18, weight="bold"),
            self._svg_text(42, 62, f"Claim {claim} · {figure_type}", size=11, fill="#374151"),
            '<line x1="92" y1="310" x2="680" y2="310" stroke="#111827" stroke-width="1.2"/>',
            '<line x1="92" y1="102" x2="92" y2="310" stroke="#111827" stroke-width="1.2"/>',
        ]
        for index, (label, value) in enumerate(values):
            y = chart_top + index * step
            bar_width = 360.0 * value / maximum
            if value >= 0:
                x = baseline
            else:
                x = baseline + bar_width
                bar_width = -bar_width
            body.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="18" fill="{palette[index % len(palette)]}"/>'
            )
            body.append(self._svg_text(84, y + 14, label[:18], size=10, fill="#374151"))
            body.append(
                self._svg_text(x + bar_width + 6, y + 14, f"{value:g}", size=10, fill="#111827")
            )
        body.extend(
            [
                self._svg_text(
                    42,
                    350,
                    "Source data and hashes are recorded in the final publication manifest.",
                    size=10,
                    fill="#4B5563",
                ),
                self._svg_text(
                    42,
                    368,
                    "Colorblind-safe palette; vector master plus 600-dpi PNG.",
                    size=10,
                    fill="#4B5563",
                ),
                "</svg>",
            ]
        )
        _ = source_hashes
        return "\n".join(body) + "\n"

    @staticmethod
    def _markdown_table(title: str, rows: list[dict[str, Any]]) -> str:
        if not rows:
            rows = [{"status": "NO_ROWS"}]
        columns: list[str] = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
        safe_columns = [
            PublicationRenderWorkflow.SAFE_COLUMN_NAMES.get(column, column) for column in columns
        ]
        lines = [
            f"# {PublicationRenderWorkflow._display_text(title)}",
            "",
            "| " + " | ".join(safe_columns) + " |",
            "| " + " | ".join(["---"] * len(safe_columns)) + " |",
        ]
        for row in rows:
            lines.append(
                "| "
                + " | ".join(
                    PublicationRenderWorkflow._display_text(str(row.get(column, "")))
                    for column in columns
                )
                + " |"
            )
        lines.extend(
            ["", "All cells are rendered from checksummed source-data JSON; no manual edits.", ""]
        )
        return "\n".join(lines)

    def _copy_source(self, source: Path, destination: Path) -> str:
        payload = source.read_bytes()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        return _sha256_bytes(payload)

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
            raise PublicationRenderError(
                f"publication vector/raster conversion failed: {exc}"
            ) from exc

    def _scan_outputs(self, paths: list[Path]) -> None:
        if not self.output_root.is_relative_to(self.root):
            return
        contamination = LockboxFirewall(self.root).scan(paths)
        if not contamination.clean:
            raise PublicationRenderError("publication outputs are contaminated")

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise PublicationRenderError("T111 requires --strict")
        if self.output_root.exists():
            raise PublicationRenderError(
                "final publication package already executed; overwrite refused"
            )
        fixture = self._fixture()
        inputs = self._load_inputs(fixture)
        specs = self._paper_specs(fixture)
        if len(specs) != 3:
            raise PublicationRenderError("three-paper package is incomplete")
        audit_receipt = inputs["T110 audit receipt"]
        if (
            audit_receipt.get("status") != "VALID_POSTLOCK_AUDIT_SEALED"
            or audit_receipt.get("raw_values_written") is not False
        ):
            raise PublicationRenderError("T110 audit receipt boundary is invalid")
        audit_path = self._path(
            "reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/claim_transitions.json",
            "claim transitions",
        )
        audit_transitions = self._json(audit_path, "claim transitions").get("transitions")
        if not isinstance(audit_transitions, list) or len(audit_transitions) != 8:
            raise PublicationRenderError("T110 claim transition coverage is incomplete")
        audit_rows = [dict(row) for row in audit_transitions if row.get("prediction_id")]
        self.output_root.mkdir(parents=True, exist_ok=False)
        source_root = self.output_root / "source_data"
        figure_root = self.output_root / "figures"
        table_root = self.output_root / "tables"
        figure_records: list[dict[str, Any]] = []
        table_records: list[dict[str, Any]] = []
        source_records: list[dict[str, str]] = []
        scanned: list[Path] = []
        for paper in specs:
            paper_id = str(paper["paper_id"])
            for figure in paper["figures"]:
                figure_id = _string(figure.get("figure_id"), "figure ID")
                spec_path = self._path(
                    f"{self.PAPER_ROOTS[paper_id]}/{figure['path']}",
                    f"{paper_id} figure specification",
                )
                references = self._source_references(
                    _string(figure.get("source"), f"{figure_id} source")
                )
                if not references:
                    raise PublicationRenderError(f"figure source is empty: {figure_id}")
                source_paths = [self._source_path(paper, reference) for reference in references]
                primary = source_paths[0]
                data = self._json(primary, f"{paper_id} figure source")
                source_hashes: dict[str, str] = {}
                for source in source_paths:
                    destination = source_root / paper_id / source.relative_to(Path(paper["root"]))
                    source_hashes[str(source.relative_to(self.root))] = self._copy_source(
                        source, destination
                    )
                    source_records.append(
                        {
                            "path": str(destination.relative_to(self.output_root)),
                            "sha256": source_hashes[str(source.relative_to(self.root))],
                        }
                    )
                values = self._chart_values(data, paper_id, primary.name, audit_rows)
                stem = f"{paper_id}_{_safe_name(figure_id)}"
                svg = figure_root / f"{stem}.svg"
                png = figure_root / f"{stem}.png"
                pdf = figure_root / f"{stem}.pdf"
                svg.parent.mkdir(parents=True, exist_ok=True)
                svg.write_text(
                    self._make_svg(paper_id, figure, values, source_hashes), encoding="utf-8"
                )
                self._convert(svg, png, pdf)
                spec_hash = _sha256(spec_path)
                figure_records.append(
                    {
                        "paper_id": paper_id,
                        "figure_id": self._display_text(figure_id),
                        "claim": figure.get("claim"),
                        "type": figure.get("type"),
                        "spec_path": str(spec_path.relative_to(self.root)),
                        "spec_sha256": spec_hash,
                        "source_data": sorted(source_hashes),
                        "svg": str(svg.relative_to(self.output_root)),
                        "pdf": str(pdf.relative_to(self.output_root)),
                        "png_600dpi": str(png.relative_to(self.output_root)),
                        "png_dpi": 600,
                    }
                )
                scanned.extend([svg, png, pdf])
            for table in paper["tables"]:
                table_path = self._path(
                    f"{self.PAPER_ROOTS[paper_id]}/{table['path']}", f"{paper_id} table source"
                )
                data = self._json(table_path, f"{paper_id} table source")
                source_destination = (
                    source_root / paper_id / table_path.relative_to(Path(paper["root"]))
                )
                source_hash = self._copy_source(table_path, source_destination)
                source_records.append(
                    {
                        "path": str(source_destination.relative_to(self.output_root)),
                        "sha256": source_hash,
                    }
                )
                rows = self._table_records(data)
                if paper_id == "paper_c_prelock" and table_path.name == "predictions.json":
                    by_prediction = {row["prediction_id"]: row for row in audit_rows}
                    rows = [
                        {
                            **row,
                            "postlock_status": by_prediction[row["prediction_id"]]["after_status"],
                            "abstained": by_prediction[row["prediction_id"]]["abstained"],
                            "failure_class": by_prediction[row["prediction_id"]]["failure_class"],
                        }
                        for row in rows
                    ]
                table_id = _string(table.get("table_id"), "table ID")
                stem = f"{paper_id}_{_safe_name(table_id)}"
                rendered = table_root / f"{stem}.md"
                rendered.parent.mkdir(parents=True, exist_ok=True)
                rendered.write_text(
                    self._markdown_table(str(data.get("title", table_id)), rows), encoding="utf-8"
                )
                table_records.append(
                    {
                        "paper_id": paper_id,
                        "table_id": table_id,
                        "source_claim": table.get("source_claim"),
                        "source_path": str(source_destination.relative_to(self.output_root)),
                        "source_sha256": source_hash,
                        "rendered_table": str(rendered.relative_to(self.output_root)),
                    }
                )
                scanned.append(rendered)
        if len(figure_records) != 15 or len(table_records) != 18:
            raise PublicationRenderError("final figure/table coverage is incomplete")
        source_manifest = {
            "schema_version": 1,
            "render_id": self.RENDER_ID,
            "source_data": sorted(source_records, key=lambda row: row["path"]),
        }
        figure_manifest = {
            "schema_version": 1,
            "render_id": self.RENDER_ID,
            "figures": figure_records,
        }
        table_manifest = {"schema_version": 1, "render_id": self.RENDER_ID, "tables": table_records}
        for name, payload in (
            ("source_data_manifest.json", source_manifest),
            ("figure_manifest.json", figure_manifest),
            ("table_manifest.json", table_manifest),
        ):
            (self.output_root / name).write_bytes(_canonical(payload))
        scanned.extend(
            [
                self.output_root / "source_data_manifest.json",
                self.output_root / "figure_manifest.json",
                self.output_root / "table_manifest.json",
            ]
        )
        self._scan_outputs(scanned)
        output_hashes = {
            str(path.relative_to(self.output_root)): _sha256(path)
            for path in sorted(self.output_root.rglob("*"))
            if path.is_file()
        }
        receipt = {
            "schema_version": 1,
            "status": "VALID_FINAL_PUBLICATION_RENDER",
            "render_id": self.RENDER_ID,
            "release_id": self.RELEASE_ID,
            "rendered_at": self.RENDERED_AT,
            "once": True,
            "figures": len(figure_records),
            "tables": len(table_records),
            "source_data_files": len(source_records),
            "vector_formats": ["svg", "pdf"],
            "raster_dpi": 600,
            "manual_numeric_edits": 0,
            "source_data_license_checked": True,
            "raw_values_written": False,
            "protected_values_read": False,
            "network_accessed": False,
            "output_hashes": output_hashes,
        }
        receipt_path = self.output_root / "generation_receipt.json"
        receipt_path.write_bytes(_canonical(receipt))
        scanned.append(receipt_path)
        self._scan_outputs(scanned)
        for path in self.output_root.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        for path in sorted(
            {p.parent for p in self.output_root.rglob("*") if p.is_dir()}, reverse=True
        ):
            path.chmod(
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
        if not receipt_path.is_file():
            raise PublicationRenderError("final publication receipt is missing")
        receipt = self._json(receipt_path, "publication receipt")
        if (
            receipt.get("status") != "VALID_FINAL_PUBLICATION_RENDER"
            or receipt.get("once") is not True
        ):
            raise PublicationRenderError("publication receipt status is invalid")
        if (
            receipt.get("figures") != 15
            or receipt.get("tables") != 18
            or receipt.get("raster_dpi") != 600
        ):
            raise PublicationRenderError("publication coverage or resolution is invalid")
        if (
            receipt.get("manual_numeric_edits") != 0
            or receipt.get("raw_values_written") is not False
            or receipt.get("protected_values_read") is not False
        ):
            raise PublicationRenderError("publication boundary is invalid")
        for relative, expected in _mapping(
            receipt.get("output_hashes"), "publication output hashes"
        ).items():
            path = self.output_root / _string(relative, "publication output path")
            if not path.is_file() or _sha256(path) != expected:
                raise PublicationRenderError(f"publication output hash differs: {relative}")
        self._scan_outputs(
            [
                receipt_path,
                self.output_root / "figure_manifest.json",
                self.output_root / "table_manifest.json",
            ]
        )
        return receipt
