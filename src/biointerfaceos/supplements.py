"""Safe supplementary CSV/TSV/XLSX/ZIP parser with cell provenance."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


class SupplementParseError(ValueError):
    """Raised when a supplementary file is malformed or unsafe."""


@dataclass(frozen=True)
class NormalizedCell:
    """One normalized cell retaining source coordinates and formula metadata."""

    source_sha256: str
    source_path: str
    table_id: str
    sheet: str | None
    member_path: str | None
    coordinate: str
    row: int
    column: int
    raw_value: str
    formula: str | None
    unit: str | None
    header_level: int | None


@dataclass(frozen=True)
class NormalizedTable:
    """One normalized supplementary table."""

    table_id: str
    source_path: str
    sheet: str | None
    member_path: str | None
    cells: tuple[NormalizedCell, ...]
    merged_ranges: tuple[str, ...]
    header_rows: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveMember:
    """Safe archive inventory metadata."""

    name: str
    compressed_size: int
    uncompressed_size: int
    encrypted: bool


@dataclass(frozen=True)
class SupplementDocument:
    """Parsed supplement tables and archive inventory."""

    source_path: str
    source_sha256: str
    tables: tuple[NormalizedTable, ...]
    archive_members: tuple[ArchiveMember, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _column_name(number: int) -> str:
    value = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _coordinate(row: int, column: int) -> str:
    return f"{_column_name(column)}{row}"


def _parse_coordinate(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)([0-9]+)", value.upper())
    if match is None:
        raise SupplementParseError(f"invalid cell coordinate: {value}")
    column = 0
    for char in match.group(1):
        column = column * 26 + ord(char) - 64
    return int(match.group(2)), column


def _unit(value: str) -> str | None:
    match = re.search(r"\[([^\]]+)\]|\(([^)]+)\)", value)
    if match is None:
        return None
    return (match.group(1) or match.group(2)).strip()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr(element: ET.Element, local_name: str) -> str | None:
    for key, value in element.attrib.items():
        if key.rsplit("}", 1)[-1] == local_name:
            return value
    return None


class SupplementParser:
    """Parse spreadsheet and archive fixtures without executing content."""

    def __init__(self, *, max_archive_bytes: int = 10_000_000) -> None:
        if max_archive_bytes <= 0:
            raise ValueError("max_archive_bytes must be positive")
        self.max_archive_bytes = max_archive_bytes

    @staticmethod
    def _source_hash(raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _csv_table(
        raw: bytes,
        *,
        source_path: str,
        delimiter: str,
        table_id: str,
        sheet: str | None = None,
        member_path: str | None = None,
    ) -> NormalizedTable:
        try:
            text = raw.decode("utf-8-sig")
            records = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise SupplementParseError(f"invalid delimited table {source_path}: {exc}") from exc
        if not records:
            raise SupplementParseError(f"empty delimited table: {source_path}")
        width = max(len(row) for row in records)
        headers = records[:2] if len(records) >= 2 else records[:1]
        units = {
            column: next(
                (
                    _unit(row[column])
                    for row in headers
                    if column < len(row) and _unit(row[column]) is not None
                ),
                None,
            )
            for column in range(width)
        }
        digest = hashlib.sha256(raw).hexdigest()
        cells: list[NormalizedCell] = []
        for row_number, row in enumerate(records, 1):
            for column_number in range(1, width + 1):
                value = row[column_number - 1] if column_number <= len(row) else ""
                cells.append(
                    NormalizedCell(
                        source_sha256=digest,
                        source_path=source_path,
                        table_id=table_id,
                        sheet=sheet,
                        member_path=member_path,
                        coordinate=_coordinate(row_number, column_number),
                        row=row_number,
                        column=column_number,
                        raw_value=value,
                        formula=None,
                        unit=units[column_number - 1],
                        header_level=row_number if row_number <= len(headers) else None,
                    )
                )
        return NormalizedTable(
            table_id=table_id,
            source_path=source_path,
            sheet=sheet,
            member_path=member_path,
            cells=tuple(cells),
            merged_ranges=(),
            header_rows=len(headers),
            warnings=(),
        )

    @staticmethod
    def _safe_members(raw: bytes) -> tuple[ArchiveMember, ...]:
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                infos = archive.infolist()
        except (OSError, zipfile.BadZipFile) as exc:
            raise SupplementParseError(f"invalid ZIP archive: {exc}") from exc
        total = 0
        members: list[ArchiveMember] = []
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                path.is_absolute()
                or (bool(path.parts) and ":" in path.parts[0])
                or ".." in path.parts
            ):
                raise SupplementParseError(f"zip-slip member path blocked: {info.filename}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise SupplementParseError(f"symlink-like archive member blocked: {info.filename}")
            encrypted = bool(info.flag_bits & 0x1)
            if encrypted:
                raise SupplementParseError(f"encrypted archive member unsupported: {info.filename}")
            total += info.file_size
            if total > 10_000_000:
                raise SupplementParseError("archive uncompressed size exceeds safety limit")
            members.append(
                ArchiveMember(
                    name=info.filename,
                    compressed_size=info.compress_size,
                    uncompressed_size=info.file_size,
                    encrypted=encrypted,
                )
            )
        return tuple(members)

    @staticmethod
    def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
        try:
            raw = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise SupplementParseError("sharedStrings.xml is malformed") from exc
        return [
            " ".join("".join(element.itertext()).split())
            for element in root
            if _local(element.tag) == "si"
        ]

    @staticmethod
    def _workbook_sheets(
        archive: zipfile.ZipFile,
    ) -> list[tuple[str, str]]:
        try:
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        except (KeyError, ET.ParseError) as exc:
            raise SupplementParseError("XLSX workbook metadata is malformed") from exc
        targets = {
            str(element.attrib["Id"]): str(element.attrib["Target"])
            for element in relationships
            if _local(element.tag) == "Relationship" and "Id" in element.attrib
        }
        sheets: list[tuple[str, str]] = []
        for sheet in workbook.iter():
            if _local(sheet.tag) != "sheet":
                continue
            name = sheet.attrib.get("name")
            relation_id = _attr(sheet, "id")
            if not isinstance(name, str) or not name or relation_id not in targets:
                raise SupplementParseError("XLSX sheet relationship is invalid")
            target = targets[relation_id]
            if not target.startswith("/"):
                target = "xl/" + target.lstrip("/")
            sheets.append((name, target))
        if not sheets:
            raise SupplementParseError("XLSX workbook has no sheets")
        return sheets

    @staticmethod
    def _xlsx_cell_value(
        cell: ET.Element,
        shared_strings: list[str],
    ) -> tuple[str, str | None]:
        formula_element = next(
            (child for child in list(cell) if _local(child.tag) == "f"),
            None,
        )
        formula = (
            "".join(formula_element.itertext()).strip() if formula_element is not None else None
        )
        value_element = next(
            (child for child in list(cell) if _local(child.tag) == "v"),
            None,
        )
        inline = next(
            (child for child in list(cell) if _local(child.tag) == "is"),
            None,
        )
        raw_value = "".join(value_element.itertext()).strip() if value_element is not None else ""
        if cell.attrib.get("t") == "s" and raw_value:
            try:
                raw_value = shared_strings[int(raw_value)]
            except (ValueError, IndexError) as exc:
                raise SupplementParseError("XLSX shared-string index is invalid") from exc
        elif inline is not None:
            raw_value = " ".join("".join(inline.itertext()).split())
        return raw_value, formula

    def _xlsx_tables(self, raw: bytes, *, source_path: str) -> tuple[NormalizedTable, ...]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as exc:
            raise SupplementParseError("XLSX is not a valid ZIP archive") from exc
        with archive:
            shared_strings = self._shared_strings(archive)
            sheets = self._workbook_sheets(archive)
            digest = hashlib.sha256(raw).hexdigest()
            tables: list[NormalizedTable] = []
            for sheet_name, target in sheets:
                try:
                    root = ET.fromstring(archive.read(target))
                except (KeyError, ET.ParseError) as exc:
                    raise SupplementParseError(
                        f"XLSX worksheet is malformed: {sheet_name}"
                    ) from exc
                merged_ranges = tuple(
                    str(element.attrib["ref"])
                    for element in root.iter()
                    if _local(element.tag) == "mergeCell" and "ref" in element.attrib
                )
                cells: list[NormalizedCell] = []
                rows = [element for element in root.iter() if _local(element.tag) == "row"]
                max_row = max((int(row.attrib.get("r", "0")) for row in rows), default=0)
                header_rows = min(2, max_row)
                header_values: dict[int, list[str]] = {}
                for row in rows:
                    row_number = int(row.attrib.get("r", "0"))
                    for cell in list(row):
                        if _local(cell.tag) != "c":
                            continue
                        reference = cell.attrib.get("r")
                        if reference is None:
                            raise SupplementParseError("XLSX cell has no coordinate")
                        parsed_row, column_number = _parse_coordinate(reference)
                        value, formula = self._xlsx_cell_value(cell, shared_strings)
                        header_values.setdefault(column_number, []).append(value)
                        cells.append(
                            NormalizedCell(
                                source_sha256=digest,
                                source_path=source_path,
                                table_id=f"{source_path}#{sheet_name}",
                                sheet=sheet_name,
                                member_path=None,
                                coordinate=reference,
                                row=parsed_row or row_number,
                                column=column_number,
                                raw_value=value,
                                formula=formula,
                                unit=None,
                                header_level=(parsed_row if parsed_row <= header_rows else None),
                            )
                        )
                unit_by_column = {
                    column: next(
                        (
                            _unit(value)
                            for value in values[:header_rows]
                            if _unit(value) is not None
                        ),
                        None,
                    )
                    for column, values in header_values.items()
                }
                cells = [
                    NormalizedCell(
                        **{
                            **cell.__dict__,
                            "unit": unit_by_column.get(cell.column),
                        }
                    )
                    for cell in cells
                ]
                tables.append(
                    NormalizedTable(
                        table_id=f"{source_path}#{sheet_name}",
                        source_path=source_path,
                        sheet=sheet_name,
                        member_path=None,
                        cells=tuple(cells),
                        merged_ranges=merged_ranges,
                        header_rows=header_rows,
                        warnings=(),
                    )
                )
            return tuple(tables)

    def parse(self, raw: bytes, *, source_path: str) -> SupplementDocument:
        """Parse one CSV/TSV/XLSX/ZIP payload without executing content."""
        suffix = Path(source_path).suffix.lower()
        digest = self._source_hash(raw)
        if suffix == ".csv":
            table = self._csv_table(
                raw, source_path=source_path, delimiter=",", table_id=source_path
            )
            return SupplementDocument(source_path, digest, (table,))
        if suffix == ".tsv":
            table = self._csv_table(
                raw, source_path=source_path, delimiter="\t", table_id=source_path
            )
            return SupplementDocument(source_path, digest, (table,))
        if suffix == ".xlsx":
            return SupplementDocument(
                source_path, digest, self._xlsx_tables(raw, source_path=source_path)
            )
        if suffix == ".zip":
            members = self._safe_members(raw)
            tables: list[NormalizedTable] = []
            warnings: list[str] = []
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for member in members:
                    member_suffix = Path(member.name).suffix.lower()
                    if member_suffix not in {".csv", ".tsv", ".xlsx"}:
                        warnings.append(f"unsupported archive member preserved: {member.name}")
                        continue
                    payload = archive.read(member.name)
                    nested = self.parse(payload, source_path=f"{source_path}!{member.name}")
                    tables.extend(
                        NormalizedTable(
                            table_id=table.table_id,
                            source_path=table.source_path,
                            sheet=table.sheet,
                            member_path=member.name,
                            cells=tuple(
                                NormalizedCell(
                                    **{
                                        **cell.__dict__,
                                        "member_path": member.name,
                                    }
                                )
                                for cell in table.cells
                            ),
                            merged_ranges=table.merged_ranges,
                            header_rows=table.header_rows,
                            warnings=table.warnings,
                        )
                        for table in nested.tables
                    )
                    warnings.extend(nested.warnings)
            return SupplementDocument(source_path, digest, tuple(tables), members, tuple(warnings))
        raise SupplementParseError(f"unsupported supplement type: {source_path}")

    def parse_file(self, path: Path) -> SupplementDocument:
        """Read and parse one local supplement file."""
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise SupplementParseError(f"cannot read supplement: {path}") from exc
        return self.parse(raw, source_path=path.as_posix())
