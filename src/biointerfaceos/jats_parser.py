"""Namespace-aware JATS/XML parser with stable evidence locators."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class JATSParseError(ValueError):
    """Raised when JATS/XML is unsafe, malformed, or missing required identity."""


@dataclass(frozen=True)
class DocumentNode:
    """One stable document-graph node."""

    source_asset_id: str
    locator: str
    node_type: str
    text: str
    parent_locator: str | None
    ordinal: int
    attributes: Mapping[str, str]

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedDocument:
    """Parsed JATS graph and explicit parser warnings."""

    source_asset_id: str
    xml_sha256: str
    article_id: str
    nodes: tuple[DocumentNode, ...]
    warnings: tuple[str, ...]

    def by_locator(self, locator: str) -> DocumentNode:
        """Return one node by its stable evidence locator."""
        for node in self.nodes:
            if node.locator == locator:
                return node
        raise KeyError(locator)

    def node_types(self) -> tuple[str, ...]:
        """Return node types in document order."""
        return tuple(node.node_type for node in self.nodes)


class JATSParser:
    """Parse a bounded JATS fixture without external entity resolution."""

    _NODE_TYPES = {
        "sec": "section",
        "p": "paragraph",
        "table-wrap": "table",
        "fig": "figure",
        "ref": "reference",
        "supplementary-material": "supplementary_link",
        "ext-link": "supplementary_link",
    }

    @staticmethod
    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _text(element: ET.Element | None) -> str:
        if element is None:
            return ""
        return " ".join("".join(element.itertext()).split())

    @staticmethod
    def _attributes(element: ET.Element) -> dict[str, str]:
        values: dict[str, str] = {}
        for key, value in element.attrib.items():
            local = key.rsplit("}", 1)[-1]
            values[local] = value
        return values

    @staticmethod
    def _href(element: ET.Element | None) -> str | None:
        if element is None:
            return None
        for key, value in element.attrib.items():
            if key.rsplit("}", 1)[-1] == "href":
                return value
        return None

    @staticmethod
    def _element_paths(root: ET.Element) -> dict[int, tuple[str, str | None]]:
        paths: dict[int, tuple[str, str | None]] = {}

        def walk(parent: ET.Element, parent_path: str | None) -> None:
            counts: dict[str, int] = {}
            for child in list(parent):
                local = JATSParser._local(child.tag)
                counts[local] = counts.get(local, 0) + 1
                path = f"{parent_path or 'article'}/{local}[{counts[local]}]"
                paths[id(child)] = (path, parent_path)
                walk(child, path)

        paths[id(root)] = ("article", None)
        walk(root, None)
        return paths

    @staticmethod
    def _unsafe_xml(raw: bytes) -> bool:
        lowered = raw.lower()
        return any(token in lowered for token in (b"<!doctype", b"<!entity", b"system", b"public"))

    @staticmethod
    def _article_id(root: ET.Element) -> str:
        for element in root.iter():
            if JATSParser._local(element.tag) == "article-id":
                value = JATSParser._text(element)
                if value:
                    return value
        raise JATSParseError("JATS article-id is required")

    @staticmethod
    def _table_attributes(element: ET.Element) -> dict[str, str]:
        attributes = JATSParser._attributes(element)
        caption = next(
            (
                JATSParser._text(child)
                for child in list(element)
                if JATSParser._local(child.tag) == "caption"
            ),
            "",
        )
        headers = [
            JATSParser._text(child)
            for child in element.iter()
            if JATSParser._local(child.tag) == "th"
        ]
        cells = [
            JATSParser._text(child)
            for child in element.iter()
            if JATSParser._local(child.tag) in {"th", "td"}
        ]
        if caption:
            attributes["caption"] = caption
        if headers:
            attributes["headers"] = " | ".join(headers)
        if cells:
            attributes["cells"] = " | ".join(cells)
        return attributes

    def parse(self, raw: bytes, *, source_asset_id: str) -> ParsedDocument:
        """Parse bytes into a stable graph and preserve optional-node warnings."""
        if not source_asset_id.strip():
            raise JATSParseError("source_asset_id is required")
        if self._unsafe_xml(raw):
            raise JATSParseError(
                "DTD, external entity, SYSTEM, or PUBLIC declarations are forbidden"
            )
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise JATSParseError(f"malformed XML: {exc}") from exc
        if self._local(root.tag) != "article":
            raise JATSParseError("JATS root element must be article")
        article_id = self._article_id(root)
        paths = self._element_paths(root)
        nodes: list[DocumentNode] = []
        warnings: list[str] = []
        ordinal = 0
        for element in root.iter():
            local = self._local(element.tag)
            node_type = self._NODE_TYPES.get(local)
            if node_type is None:
                continue
            path, parent_path = paths[id(element)]
            attributes = self._attributes(element)
            if local in {"supplementary-material", "ext-link"}:
                href = self._href(element)
                if href is None:
                    warnings.append(f"{path}: supplementary link has no href")
                else:
                    attributes["href"] = href
            if local == "table-wrap":
                attributes = self._table_attributes(element)
                if "caption" not in attributes:
                    warnings.append(f"{path}: table has no caption")
            if local == "fig":
                graphic = next(
                    (child for child in element.iter() if self._local(child.tag) == "graphic"),
                    None,
                )
                graphic_href = self._href(graphic)
                if graphic_href is None:
                    warnings.append(f"{path}: figure has no graphic href")
                else:
                    attributes["graphic_href"] = graphic_href
            ordinal += 1
            nodes.append(
                DocumentNode(
                    source_asset_id=source_asset_id,
                    locator=f"asset:{source_asset_id}/{path}",
                    node_type=node_type,
                    text=self._text(element),
                    parent_locator=(
                        f"asset:{source_asset_id}/{parent_path}" if parent_path else None
                    ),
                    ordinal=ordinal,
                    attributes=attributes,
                )
            )
        return ParsedDocument(
            source_asset_id=source_asset_id,
            xml_sha256=hashlib.sha256(raw).hexdigest(),
            article_id=article_id,
            nodes=tuple(nodes),
            warnings=tuple(warnings),
        )

    def parse_file(self, path: Path, *, source_asset_id: str) -> ParsedDocument:
        """Read one local XML file and parse it."""
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise JATSParseError(f"cannot read XML file: {path}") from exc
        return self.parse(raw, source_asset_id=source_asset_id)
