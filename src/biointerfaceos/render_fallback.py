"""Deterministic standard-library fallbacks for optional figure converters."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def write_placeholder_png(path: Path, *, width: int = 3600, height: int = 2000) -> None:
    """Write a valid blank raster when the optional SVG converter is unavailable."""
    raw = (b"\x00" + b"\x00" * width) * height
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(raw, level=9))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def write_placeholder_pdf(path: Path, *, width: int = 360, height: int = 200) -> None:
    """Write a minimal one-page PDF placeholder for protocol-only QA."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] >>".encode("ascii"),
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(output))
