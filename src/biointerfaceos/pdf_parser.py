"""Bounded born-digital PDF fixture parser with scanned quality flags."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


class PDFParseError(ValueError):
    """Raised when a PDF fixture is malformed or missing required structure."""


@dataclass(frozen=True)
class PDFBlock:
    """One page-aware text/layout block."""

    source_asset_id: str
    locator: str
    page: int
    block_type: str
    text: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class PDFQuality:
    """Explicit text-layer quality decision."""

    status: str
    warnings: tuple[str, ...]
    text_blocks: int


@dataclass(frozen=True)
class ParsedPDF:
    """Parsed PDF blocks, source hash, and quality report."""

    source_asset_id: str
    pdf_sha256: str
    page_count: int
    blocks: tuple[PDFBlock, ...]
    quality: PDFQuality

    def by_locator(self, locator: str) -> PDFBlock:
        """Return one block by stable page/block locator."""
        for block in self.blocks:
            if block.locator == locator:
                return block
        raise KeyError(locator)


class PDFParser:
    """Parse controlled PDF text streams without OCR or code execution."""

    _TEXT = re.compile(r"\(((?:\\.|[^\\)])*)\)\s*Tj")
    _POSITION = re.compile(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+Td")
    _FONT = re.compile(r"(-?\d+(?:\.\d+)?)\s+Tf")

    @staticmethod
    def _decode_pdf_string(value: str) -> str:
        value = re.sub(r"\\([\\()])", r"\1", value)
        value = value.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
        return value

    @staticmethod
    def _page_count(raw: bytes) -> int:
        text = raw.decode("latin1", errors="ignore")
        return max(1, len(re.findall(r"/Type\s*/Page(?!s)", text)))

    def parse(self, raw: bytes, *, source_asset_id: str) -> ParsedPDF:
        """Parse PDF text streams and mark textless/scanned inputs explicitly."""
        if not source_asset_id.strip():
            raise PDFParseError("source_asset_id is required")
        if not raw.startswith(b"%PDF-"):
            raise PDFParseError("PDF header is missing")
        streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", raw, flags=re.DOTALL)
        page_count = self._page_count(raw)
        blocks: list[PDFBlock] = []
        for page_number, stream in enumerate(streams, 1):
            text = stream.decode("latin1", errors="ignore")
            x = y = 0.0
            font_size = 12.0
            cursor = 0
            block_number = 0
            for match in re.finditer(
                rf"{self._POSITION.pattern}|{self._FONT.pattern}|{self._TEXT.pattern}",
                text,
            ):
                token = match.group(0)
                position = self._POSITION.fullmatch(token)
                if position is not None:
                    x = float(position.group(1))
                    y = float(position.group(2))
                    continue
                font = self._FONT.fullmatch(token)
                if font is not None:
                    font_size = max(1.0, float(font.group(1)))
                    continue
                text_match = self._TEXT.search(token)
                if text_match is None:
                    continue
                value = self._decode_pdf_string(text_match.group(1))
                if not value.strip():
                    continue
                block_number += 1
                prefix = value.split(":", 1)[0].upper()
                if prefix in {"TABLE", "CAPTION"}:
                    block_type = prefix.lower()
                    value = value.split(":", 1)[1].strip()
                else:
                    block_type = "text"
                width = max(font_size, len(value) * font_size * 0.5)
                locator = f"asset:{source_asset_id}/page[{page_number}]/block[{block_number}]"
                blocks.append(
                    PDFBlock(
                        source_asset_id=source_asset_id,
                        locator=locator,
                        page=page_number,
                        block_type=block_type,
                        text=value,
                        bbox=(x, y, x + width, y + font_size),
                    )
                )
                cursor = match.end()
            del cursor
        warnings: list[str] = []
        if not blocks:
            status = "SCANNED_OR_TEXTLESS"
            warnings.append("no text layer blocks detected; OCR was not attempted")
        else:
            status = "BORN_DIGITAL"
        if page_count > len(streams) and blocks:
            warnings.append("page/content stream count differs; fixture page mapping is bounded")
        return ParsedPDF(
            source_asset_id=source_asset_id,
            pdf_sha256=hashlib.sha256(raw).hexdigest(),
            page_count=page_count,
            blocks=tuple(blocks),
            quality=PDFQuality(status, tuple(warnings), len(blocks)),
        )

    def parse_file(self, path: Path, *, source_asset_id: str) -> ParsedPDF:
        """Read and parse a local PDF fixture."""
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PDFParseError(f"cannot read PDF: {path}") from exc
        return self.parse(raw, source_asset_id=source_asset_id)
