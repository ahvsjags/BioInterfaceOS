"""Fixture-backed, checksum-gated mass-spec conversion and mzML bypass."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONVERSION_FIXTURE = Path("tests/fixtures/omics/conversion_fixture.json")
CONVERSION_ROOT = Path("reports/omics/conversion")
TRIAGE_CARDS = Path("reports/omics/pride/project_cards.json")
TRIAGE_SPLITS = Path("reports/omics/pride/split_eligibility.json")


class ConversionError(RuntimeError):
    """Raised when conversion inputs or receipts are invalid."""


@dataclass(frozen=True)
class ConversionSummary:
    """Summary and output paths from one conversion run."""

    records: int
    completed: int
    refused: int
    resumed: int
    receipt_path: Path
    manifest_path: Path
    log_path: Path
    artifact_paths: tuple[Path, ...]


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConversionError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConversionError(f"JSON object required: {path}")
    return value


class ConversionWorkflow:
    """Perform a bounded supported-mzML bypass with fail-closed refusal paths."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / CONVERSION_FIXTURE
        self.output_root = output_root or self.root / CONVERSION_ROOT

    def _load(self) -> tuple[int, list[dict[str, Any]]]:
        value = _read_json(self.fixture_path)
        if set(value) != {"schema_version", "max_bytes", "records"}:
            raise ConversionError("conversion fixture envelope is invalid")
        max_bytes = value.get("max_bytes")
        records = value.get("records")
        if (
            value.get("schema_version") != 1
            or not isinstance(max_bytes, int)
            or max_bytes <= 0
            or not isinstance(records, list)
            or not records
        ):
            raise ConversionError("conversion fixture schema is invalid")
        fields = {
            "project_accession",
            "file_name",
            "kind",
            "access",
            "input_path",
            "input_sha256",
            "declared_size_bytes",
            "instrument",
            "expected_status",
        }
        normalized: list[dict[str, Any]] = []
        for raw in records:
            if not isinstance(raw, Mapping) or set(raw) != fields:
                raise ConversionError("conversion fixture record fields are invalid")
            row = dict(raw)
            if (
                not isinstance(row["project_accession"], str)
                or not isinstance(row["file_name"], str)
                or row["kind"] not in {"MZML", "RAW"}
                or row["access"] not in {"PUBLIC", "RESTRICTED", "METADATA_ONLY"}
                or row["input_path"] is not None
                and not isinstance(row["input_path"], str)
                or row["input_sha256"] is not None
                and not isinstance(row["input_sha256"], str)
                or not isinstance(row["declared_size_bytes"], int)
                or row["declared_size_bytes"] < 0
                or not isinstance(row["instrument"], str)
                or not row["instrument"]
                or row["expected_status"]
                not in {
                    "COMPLETED",
                    "REFUSED_RESTRICTED",
                    "REFUSED_SIZE",
                    "REFUSED_UNSUPPORTED_FORMAT",
                    "REFUSED_CHECKSUM",
                }
            ):
                raise ConversionError(f"conversion fixture record values are invalid: {row}")
            normalized.append(row)
        if len({str(row["project_accession"]) for row in normalized}) != len(normalized):
            raise ConversionError("conversion project accessions are not unique")
        return max_bytes, normalized

    def _validate_upstream(self, records: list[dict[str, Any]]) -> None:
        cards = _read_json(self.root / TRIAGE_CARDS)
        card_rows = cards.get("cards")
        if not isinstance(card_rows, list):
            raise ConversionError("PRIDE project cards are missing")
        cards_by_accession = {
            str(card["project_accession"]): card
            for card in card_rows
            if isinstance(card, Mapping) and isinstance(card.get("project_accession"), str)
        }
        splits = _read_json(self.root / TRIAGE_SPLITS)
        split_rows = splits.get("projects")
        if not isinstance(split_rows, list):
            raise ConversionError("PRIDE split eligibility is missing")
        eligible = {
            str(row["project_accession"])
            for row in split_rows
            if isinstance(row, Mapping) and row.get("eligible_for_split") is True
        }
        for row in records:
            accession = str(row["project_accession"])
            if accession == "PXD000001":
                card = cards_by_accession.get(accession)
                if card is None or accession not in eligible:
                    raise ConversionError("conversion input is not an eligible PRIDE project")
                if card.get("instrument") != row["instrument"]:
                    raise ConversionError("instrument metadata differs from frozen triage")

    def run(self, *, fixture: bool = True) -> ConversionSummary:
        """Run conversion/refusal paths and write deterministic receipts."""
        if not fixture:
            raise ConversionError("--fixture is required for offline conversion")
        max_bytes, records = self._load()
        self._validate_upstream(records)
        artifact_root = self.output_root / "artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)
        receipt_rows: list[dict[str, Any]] = []
        artifact_paths: list[Path] = []
        resumed = 0
        for row in records:
            accession = str(row["project_accession"])
            file_name = str(row["file_name"])
            status = "COMPLETED"
            reason = "supported_mzml_bypass"
            input_bytes: bytes | None = None
            output_path: Path | None = None
            output_sha256: str | None = None
            output_bytes = 0
            if row["access"] != "PUBLIC":
                status = "REFUSED_RESTRICTED"
                reason = "source access is not public"
            elif int(row["declared_size_bytes"]) > max_bytes:
                status = "REFUSED_SIZE"
                reason = "declared file size exceeds conversion limit"
            elif row["kind"] != "MZML":
                status = "REFUSED_UNSUPPORTED_FORMAT"
                reason = "vendor RAW conversion is not enabled in this fixture workflow"
            else:
                input_relative = row["input_path"]
                if not isinstance(input_relative, str) or row["input_sha256"] is None:
                    raise ConversionError(f"public mzML input metadata is incomplete: {accession}")
                input_path = (self.root / input_relative).resolve()
                try:
                    input_path.relative_to(self.root)
                except ValueError as exc:
                    raise ConversionError(
                        f"conversion input escapes repository: {input_relative}"
                    ) from exc
                try:
                    input_bytes = input_path.read_bytes()
                except OSError as exc:
                    raise ConversionError(
                        f"cannot read conversion input: {input_relative}"
                    ) from exc
                actual_hash = _sha256(input_bytes)
                if actual_hash != row["input_sha256"]:
                    status = "REFUSED_CHECKSUM"
                    reason = "input checksum differs from declared checksum"
                elif len(input_bytes) != int(row["declared_size_bytes"]):
                    raise ConversionError(f"input byte count differs from declaration: {accession}")
                else:
                    try:
                        root_element = ET.fromstring(input_bytes)
                    except ET.ParseError as exc:
                        raise ConversionError(f"mzML XML is invalid: {accession}") from exc
                    if not root_element.tag.endswith("mzML"):
                        raise ConversionError(f"input is not mzML: {accession}")
                    output_path = artifact_root / f"{accession}.mzML"
                    output_data = input_bytes
                    output_sha256 = _sha256(output_data)
                    output_bytes = len(output_data)
                    if output_path.exists():
                        existing = output_path.read_bytes()
                        if _sha256(existing) != output_sha256:
                            raise ConversionError(
                                f"existing conversion artifact checksum differs: {accession}"
                            )
                        resumed += 1
                    else:
                        output_path.write_bytes(output_data)
                    artifact_paths.append(output_path)
            if status != str(row["expected_status"]):
                raise ConversionError(
                    f"conversion status differs for {accession}: {status} != "
                    f"{row['expected_status']}"
                )
            receipt_rows.append(
                {
                    "project_accession": accession,
                    "file_name": file_name,
                    "status": status,
                    "reason": reason,
                    "instrument": row["instrument"],
                    "input_sha256": row["input_sha256"],
                    "input_bytes": len(input_bytes) if input_bytes is not None else None,
                    "output_path": (
                        str(CONVERSION_ROOT / "artifacts" / output_path.name)
                        if output_path
                        else None
                    ),
                    "output_sha256": output_sha256,
                    "output_bytes": output_bytes if output_path else None,
                    "converter": "mzml_bypass" if status == "COMPLETED" else None,
                    "converter_version": "fixture-bypass-v1" if status == "COMPLETED" else None,
                    "resume_key": _sha256(
                        _canonical(
                            {
                                "project_accession": accession,
                                "file_name": file_name,
                                "input_sha256": row["input_sha256"],
                                "instrument": row["instrument"],
                            }
                        )
                    ),
                    "raw_downloaded": False,
                    "locked_payload_accessed": False,
                }
            )
        status_counts = dict(sorted(Counter(str(row["status"]) for row in receipt_rows).items()))
        manifest = {
            "schema_version": 1,
            "fixture": True,
            "records": len(receipt_rows),
            "completed": status_counts.get("COMPLETED", 0),
            "refused": len(receipt_rows) - status_counts.get("COMPLETED", 0),
            "status_counts": status_counts,
            "receipt_rows": receipt_rows,
            "raw_downloaded": False,
            "locked_payload_accessed": False,
            "resume_supported": True,
        }
        log = {
            "schema_version": 1,
            "events": receipt_rows,
            "resume_supported": True,
            "raw_downloaded": False,
            "locked_payload_accessed": False,
        }
        input_hashes = {"fixture": _sha256(self.fixture_path.read_bytes())}
        serialized = {
            "conversion_manifest.json": _canonical(manifest),
            "conversion_log.json": _canonical(log),
        }
        receipt = {
            "schema_version": 1,
            "fixture": True,
            "input_sha256": input_hashes,
            "output_sha256": {name: _sha256(content) for name, content in serialized.items()},
            **{key: value for key, value in manifest.items() if key != "receipt_rows"},
        }
        serialized["conversion_receipt.json"] = _canonical(receipt)
        self.output_root.mkdir(parents=True, exist_ok=True)
        for name, content in serialized.items():
            (self.output_root / name).write_bytes(content)
        return ConversionSummary(
            records=len(receipt_rows),
            completed=status_counts.get("COMPLETED", 0),
            refused=len(receipt_rows) - status_counts.get("COMPLETED", 0),
            resumed=resumed,
            receipt_path=self.output_root / "conversion_receipt.json",
            manifest_path=self.output_root / "conversion_manifest.json",
            log_path=self.output_root / "conversion_log.json",
            artifact_paths=tuple(artifact_paths),
        )
