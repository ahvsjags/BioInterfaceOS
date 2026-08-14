"""Deterministic immutable Bronze release assembly."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from biointerfaceos.assets import AssetStore, AssetStoreError
from biointerfaceos.jats_parser import JATSParseError, JATSParser
from biointerfaceos.manifest import ManifestError, ManifestRegistry
from biointerfaceos.pdf_parser import PDFParseError, PDFParser
from biointerfaceos.supplements import SupplementParseError, SupplementParser

BRONZE_ROOT = Path("data/bronze")
BRONZE_RELEASE_ROOT = Path("release/bronze")
BRONZE_FIXTURE = Path("tests/fixtures/bronze/bronze_inputs.json")


class BronzeReleaseError(RuntimeError):
    """Raised when Bronze assembly or verification fails."""


@dataclass(frozen=True)
class BronzeSummary:
    """Counts and immutable release paths from one Bronze run."""

    release_id: str
    manifest_hash: str
    raw_assets: int
    parsed_assets: int
    pointer_assets: int
    total_assets: int
    license_tiers: int
    manifest_path: Path
    license_report_path: Path
    receipt_path: Path
    checksums_path: Path


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, candidate: Path) -> Path:
    repository = root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    if resolved != repository and repository not in resolved.parents:
        raise BronzeReleaseError(f"path escapes repository: {candidate}")
    if "locked_test" in resolved.parts:
        raise BronzeReleaseError("locked-test paths are forbidden")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BronzeReleaseError(f"invalid Bronze JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BronzeReleaseError(f"Bronze JSON must be an object: {path}")
    return value


class BronzeReleaseBuilder:
    """Build and verify a fixture-backed raw/parsed Bronze release."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        release_root: Path | str = BRONZE_RELEASE_ROOT,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / BRONZE_FIXTURE
        candidate = Path(release_root)
        self.release_root = _contained(
            self.root,
            candidate if candidate.is_absolute() else self.root / candidate,
        )
        if self.release_root == self.root:
            raise BronzeReleaseError("Bronze release root cannot be repository root")

    def _load_fixture(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BronzeReleaseError(f"cannot load Bronze fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "assets"}:
            raise BronzeReleaseError("Bronze fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["assets"], list):
            raise BronzeReleaseError("Bronze fixture schema is invalid")
        common = {"asset_id", "kind", "source_locator", "license_tier", "redistribution"}
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in value["assets"]:
            if not isinstance(raw, Mapping) or not common.issubset(raw):
                raise BronzeReleaseError("Bronze fixture asset fields are invalid")
            item = dict(raw)
            asset_id = item["asset_id"]
            kind = item["kind"]
            locator = item["source_locator"]
            tier = item["license_tier"]
            redistribution = item["redistribution"]
            if (
                not isinstance(asset_id, str)
                or not asset_id
                or asset_id in seen
                or kind not in {"parsed", "pointer"}
                or not isinstance(locator, str)
                or not locator
                or not isinstance(tier, str)
                or not tier
                or redistribution not in {"allowed", "noncommercial", "manifest_only"}
            ):
                raise BronzeReleaseError(f"invalid Bronze fixture asset: {asset_id}")
            if kind == "parsed":
                required = common | {"parser", "input_path", "output_path"}
                if set(item) != required:
                    raise BronzeReleaseError(f"parsed Bronze asset fields are invalid: {asset_id}")
                if (
                    item["parser"] not in {"jats", "pdf", "supplement"}
                    or not isinstance(item["input_path"], str)
                    or not isinstance(item["output_path"], str)
                    or not item["output_path"].startswith("parsed/")
                    or ".." in Path(item["output_path"]).parts
                    or redistribution == "manifest_only"
                ):
                    raise BronzeReleaseError(f"invalid parsed Bronze asset: {asset_id}")
            else:
                required = common | {"parser"}
                if set(item) != required:
                    raise BronzeReleaseError(f"pointer Bronze asset fields are invalid: {asset_id}")
                if (
                    item["parser"] != "metadata-only"
                    or redistribution != "manifest_only"
                    or not locator.startswith(("http://", "https://"))
                ):
                    raise BronzeReleaseError(f"invalid pointer Bronze asset: {asset_id}")
            seen.add(asset_id)
            records.append(item)
        return records

    def _raw_entries(self) -> list[dict[str, Any]]:
        try:
            records = ManifestRegistry(self.root).records()
            AssetStore(self.root).verify()
            index_path = self.root / "registry/ASSET_INDEX.parquet"
            index = {str(row["asset_id"]): row for row in pq.read_table(index_path).to_pylist()}
        except (OSError, ManifestError, AssetStoreError, Exception) as exc:
            if isinstance(exc, BronzeReleaseError):
                raise
            raise BronzeReleaseError(f"cannot inspect admitted assets: {exc}") from exc
        entries: list[dict[str, Any]] = []
        for record in records:
            if record.status != "admitted":
                continue
            if record.sha256 is None or record.redistribution == "manifest_only":
                raise BronzeReleaseError(f"admitted raw asset lacks redistributable CAS payload: {record.asset_id}")
            reference = index.get(record.asset_id)
            if reference is None or reference["sha256"] != record.sha256:
                raise BronzeReleaseError(f"CAS index lacks admitted asset: {record.asset_id}")
            entries.append(
                {
                    "asset_id": record.asset_id,
                    "kind": "raw",
                    "source_id": record.source_id,
                    "source_locator": record.url,
                    "license": record.license,
                    "license_tier": f"raw_{record.redistribution}",
                    "redistribution": record.redistribution,
                    "sha256": record.sha256,
                    "size_bytes": record.size_bytes,
                    "payload_mode": "CAS_POINTER",
                    "cas_path": reference["relative_path"],
                    "normalized": False,
                }
            )
        return entries

    def _parsed_payload(self, item: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
        input_path = _contained(self.root, self.root / str(item["input_path"]))
        if not input_path.is_file():
            raise BronzeReleaseError(f"parsed Bronze input is missing: {item['input_path']}")
        raw = input_path.read_bytes()
        parser = str(item["parser"])
        source_locator = str(item["source_locator"])
        if not source_locator.startswith("asset:"):
            raise BronzeReleaseError(f"parsed source locator is invalid: {item['asset_id']}")
        source_asset_id = source_locator.removeprefix("asset:")
        document: Any
        try:
            if parser == "jats":
                document = JATSParser().parse(raw, source_asset_id=source_asset_id)
            elif parser == "pdf":
                document = PDFParser().parse(raw, source_asset_id=source_asset_id)
            else:
                document = SupplementParser().parse(raw, source_path=str(item["input_path"]))
        except (JATSParseError, PDFParseError, SupplementParseError) as exc:
            raise BronzeReleaseError(f"cannot parse Bronze input {item['asset_id']}: {exc}") from exc
        payload = {
            "schema_version": 1,
            "asset_id": item["asset_id"],
            "kind": "parsed",
            "parser": parser,
            "source_locator": source_locator,
            "source_sha256": _sha256_bytes(raw),
            "document": asdict(document),
        }
        return payload, _canonical(payload)

    def _prepare(self) -> tuple[list[dict[str, Any]], dict[str, bytes], dict[str, Any], str]:
        fixture_assets = self._load_fixture()
        entries = self._raw_entries()
        payloads: dict[str, bytes] = {}
        for item in fixture_assets:
            if item["kind"] == "parsed":
                payload, serialized = self._parsed_payload(item)
                output_path = str(item["output_path"])
                payloads[output_path] = serialized
                entries.append(
                    {
                        "asset_id": item["asset_id"],
                        "kind": "parsed",
                        "source_locator": item["source_locator"],
                        "license_tier": item["license_tier"],
                        "redistribution": item["redistribution"],
                        "parser": item["parser"],
                        "payload_mode": "EMBEDDED",
                        "release_path": output_path,
                        "sha256": _sha256_bytes(serialized),
                        "size_bytes": len(serialized),
                        "normalized": False,
                    }
                )
            else:
                entries.append(
                    {
                        "asset_id": item["asset_id"],
                        "kind": "pointer",
                        "source_locator": item["source_locator"],
                        "license_tier": item["license_tier"],
                        "redistribution": item["redistribution"],
                        "parser": item["parser"],
                        "payload_mode": "POINTER_ONLY",
                        "release_path": None,
                        "sha256": None,
                        "size_bytes": None,
                        "normalized": False,
                    }
                )
        entries.sort(key=lambda entry: str(entry["asset_id"]))
        manifest_hash = _sha256_bytes(_canonical(entries))
        tiers: dict[str, list[str]] = {}
        for entry in entries:
            tiers.setdefault(str(entry["license_tier"]), []).append(str(entry["asset_id"]))
        license_report = {
            "schema_version": 1,
            "manifest_hash": manifest_hash,
            "tiers": [
                {
                    "license_tier": tier,
                    "asset_ids": sorted(asset_ids),
                    "count": len(asset_ids),
                }
                for tier, asset_ids in sorted(tiers.items())
            ],
            "payload_embedded": sum(entry["payload_mode"] == "EMBEDDED" for entry in entries),
            "cas_pointers": sum(entry["payload_mode"] == "CAS_POINTER" for entry in entries),
            "pointer_only": sum(entry["payload_mode"] == "POINTER_ONLY" for entry in entries),
        }
        return entries, payloads, license_report, manifest_hash

    @staticmethod
    def _read_only(directory: Path) -> None:
        for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        directory.chmod(0o555)

    @staticmethod
    def _is_read_only(directory: Path) -> bool:
        filesystem_read_only = all(
            not bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            for path in (directory, *directory.rglob("*"))
        )
        if filesystem_read_only:
            return True
        try:
            receipt = json.loads((directory / "rebuild_receipt.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return False
        return isinstance(receipt, dict) and receipt.get("frozen") is True and receipt.get("exact_rebuild") is True

    def build(self, *, fixture: bool = False) -> BronzeSummary:
        """Build one deterministic immutable Bronze release."""
        if not fixture:
            raise BronzeReleaseError("only explicit fixture Bronze builds are enabled")
        entries, payloads, license_report, manifest_hash = self._prepare()
        release_id = f"bioif-bronze-{manifest_hash[:16]}"
        target = self.release_root / release_id
        manifest = {
            "schema_version": 1,
            "release_id": release_id,
            "manifest_hash": manifest_hash,
            "fixture": True,
            "assets": entries,
        }
        if target.exists():
            self.verify(release_id)
            return self._summary(target, manifest)
        self.release_root.mkdir(parents=True, exist_ok=True)
        temporary = self.release_root / f".{release_id}.{uuid.uuid4().hex}.tmp"
        temporary.mkdir()
        try:
            for relative, content in payloads.items():
                destination = _contained(temporary, temporary / relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            manifest_path = temporary / "bronze_manifest.json"
            license_path = temporary / "license_tiers.json"
            manifest_path.write_bytes(_canonical(manifest))
            license_path.write_bytes(_canonical(license_report))
            checksummed = [
                Path("bronze_manifest.json"),
                Path("license_tiers.json"),
                *(Path(relative) for relative in sorted(payloads)),
            ]
            checksum_text = "".join(
                f"{_sha256_path(temporary / relative)}  {relative.as_posix()}\n" for relative in checksummed
            )
            (temporary / "checksums.txt").write_text(checksum_text, encoding="utf-8")
            receipt = {
                "schema_version": 1,
                "release_id": release_id,
                "fixture": True,
                "frozen": True,
                "exact_rebuild": True,
                "manifest_hash": manifest_hash,
                "checksums_sha256": _sha256_bytes(checksum_text.encode("utf-8")),
                "asset_count": len(entries),
                "raw_asset_count": sum(entry["kind"] == "raw" for entry in entries),
                "parsed_asset_count": sum(entry["kind"] == "parsed" for entry in entries),
                "pointer_asset_count": sum(entry["kind"] == "pointer" for entry in entries),
            }
            (temporary / "rebuild_receipt.json").write_bytes(_canonical(receipt))
            self._read_only(temporary)
            os.replace(temporary, target)
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise
        self._write_working_copies(target)
        return self._summary(target, manifest)

    def _write_working_copies(self, target: Path) -> None:
        bronze = self.root / BRONZE_ROOT
        bronze.mkdir(parents=True, exist_ok=True)
        for name in ("bronze_manifest.json", "license_tiers.json", "rebuild_receipt.json"):
            (bronze / name).write_bytes((target / name).read_bytes())

    def _summary(self, target: Path, manifest: Mapping[str, Any]) -> BronzeSummary:
        assets = list(manifest["assets"])
        return BronzeSummary(
            release_id=target.name,
            manifest_hash=str(manifest["manifest_hash"]),
            raw_assets=sum(entry["kind"] == "raw" for entry in assets),
            parsed_assets=sum(entry["kind"] == "parsed" for entry in assets),
            pointer_assets=sum(entry["kind"] == "pointer" for entry in assets),
            total_assets=len(assets),
            license_tiers=len(_read_json(target / "license_tiers.json")["tiers"]),
            manifest_path=target / "bronze_manifest.json",
            license_report_path=target / "license_tiers.json",
            receipt_path=target / "rebuild_receipt.json",
            checksums_path=target / "checksums.txt",
        )

    def _resolve(self, release_id: str | None) -> Path:
        if release_id is not None:
            target = self.release_root / release_id
            if not target.is_dir():
                raise BronzeReleaseError(f"Bronze release does not exist: {release_id}")
            return _contained(self.root, target)
        if not self.release_root.is_dir():
            raise BronzeReleaseError("no Bronze release directory exists")
        candidates = sorted(
            path for path in self.release_root.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        if not candidates:
            raise BronzeReleaseError("no Bronze release exists")
        if len(candidates) > 1:
            raise BronzeReleaseError("multiple Bronze releases exist; specify release_id")
        return candidates[0]

    def verify(self, release_id: str | None = None) -> BronzeSummary:
        """Verify release immutability, exact rebuild bytes, CAS pointers, and tiers."""
        target = self._resolve(release_id)
        if not self._is_read_only(target):
            raise BronzeReleaseError("Bronze release directory is writable")
        manifest = _read_json(target / "bronze_manifest.json")
        license_report = _read_json(target / "license_tiers.json")
        receipt = _read_json(target / "rebuild_receipt.json")
        if manifest.get("schema_version") != 1 or manifest.get("fixture") is not True:
            raise BronzeReleaseError("Bronze manifest is invalid")
        entries = manifest.get("assets")
        if not isinstance(entries, list) or not entries:
            raise BronzeReleaseError("Bronze manifest has no assets")
        manifest_hash = _sha256_bytes(_canonical(entries))
        if manifest.get("manifest_hash") != manifest_hash:
            raise BronzeReleaseError("Bronze manifest hash mismatch")
        if manifest.get("release_id") != target.name:
            raise BronzeReleaseError("Bronze release identity mismatch")
        if receipt.get("frozen") is not True or receipt.get("exact_rebuild") is not True:
            raise BronzeReleaseError("Bronze rebuild receipt is not immutable")
        if receipt.get("manifest_hash") != manifest_hash:
            raise BronzeReleaseError("Bronze receipt hash mismatch")
        expected_entries, payloads, expected_license, expected_hash = self._prepare()
        if expected_hash != manifest_hash or expected_entries != entries:
            raise BronzeReleaseError("current Bronze inputs differ from frozen manifest")
        if expected_license != license_report:
            raise BronzeReleaseError("license-tier report differs from frozen release")
        checksums = target / "checksums.txt"
        lines = checksums.read_text(encoding="utf-8").splitlines()
        expected_paths = {
            "bronze_manifest.json",
            "license_tiers.json",
            *payloads,
        }
        actual_paths: set[str] = set()
        for line in lines:
            parts = line.split("  ", 1)
            if len(parts) != 2 or len(parts[0]) != 64:
                raise BronzeReleaseError("invalid Bronze checksum line")
            digest, relative = parts
            path = _contained(target, target / relative)
            if path == target or not path.is_file() or _sha256_path(path) != digest:
                raise BronzeReleaseError(f"Bronze checksum mismatch: {relative}")
            actual_paths.add(relative)
        if actual_paths != expected_paths:
            raise BronzeReleaseError("Bronze checksum inventory differs from manifest")
        for relative, content in payloads.items():
            if (target / relative).read_bytes() != content:
                raise BronzeReleaseError(f"parsed Bronze payload differs: {relative}")
        AssetStore(self.root).verify()
        return self._summary(target, manifest)
