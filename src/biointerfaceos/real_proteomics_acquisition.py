"""Resumable, source-bounded staging for the T123 public proteomics cohort.

The workflow retrieves only the preflight-selected author assets.  It verifies
the strongest publisher integrity signal available for each file and writes a
local SHA-256 ledger, but it never harmonizes author quantification or permits
model fitting.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import stat
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from biointerfaceos.network import PROJECT_USER_AGENT


class RealProteomicsAcquisitionError(RuntimeError):
    """Raised when a T123 source transfer is incomplete or unverifiable."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealProteomicsAcquisitionError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise RealProteomicsAcquisitionError(
            f"{label} must be a list with at least {minimum} items"
        )
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealProteomicsAcquisitionError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RealProteomicsAcquisitionError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class TransferAsset:
    """One selected public file and its publisher-verification contract."""

    source_id: str
    accession: str
    asset_id: str
    file_name: str
    relative_path: str
    url: str
    role: str
    publisher_api_bytes: int
    expected_bytes: int | None
    publisher_checksum: str | None
    publisher_checksum_algorithm: str | None
    checksum_representation: str
    byte_verification: str


@dataclass(frozen=True)
class RealProteomicsAcquisitionSummary:
    """Counts from a staging pass or final immutable acquisition audit."""

    asset_count: int
    source_count: int
    publisher_checksum_verified_count: int
    receipt_path: Path | None


class RealProteomicsAcquisitionWorkflow:
    """Stage the fixed public cohort without promoting it to a model target."""

    MANIFEST_ID = "bioif-r2-real-proteomics-transfer-manifest-v1.0.0"
    MANIFEST_RELATIVE = "docs/data/R2_T123_PROTEOMICS_TRANSFER_MANIFEST.json"
    PREFLIGHT_REGISTRY_RELATIVE = "docs/data/R2_T123_PROTEOMICS_SOURCE_PREFLIGHT.json"
    PREFLIGHT_RECEIPT_RELATIVE = (
        "reports/review_round_2/real_proteomics_source_preflight/v1.0.0/"
        "source_preflight_receipt.json"
    )
    RAW_RELATIVE = "data/raw/r2_t123_proteomics"
    OUTPUT_RELATIVE = "reports/review_round_2/real_proteomics_acquisition/v1.0.0"
    EVENT_LOG_NAME = "transfer_events.jsonl"
    ALLOWED_HOST = "ftp.pride.ebi.ac.uk"
    EXPECTED_SOURCE_COUNTS = {
        "PRIDE-PXD017776": 12,
        "PRIDE-PXD052701": 10,
        "PRIDE-PXD032162": 5,
    }
    REQUIRED_MANIFEST_FIELDS = {
        "schema_version",
        "manifest_id",
        "evaluated_at",
        "source_preflight_registry_sha256",
        "source_preflight_receipt_sha256",
        "transport_policy",
        "sources",
    }
    REQUIRED_POLICY_FIELDS = {
        "anonymous_https_only",
        "allowed_host",
        "resume_partial_files",
        "preserve_failed_partials",
        "record_local_sha256",
        "prohibit_model_input",
    }
    REQUIRED_SOURCE_FIELDS = {"source_id", "accession", "archive_prefix", "asset_count", "assets"}
    REQUIRED_ASSET_FIELDS = {
        "asset_id",
        "file_name",
        "relative_path",
        "role",
        "publisher_api_bytes",
        "expected_bytes",
        "publisher_checksum",
        "publisher_checksum_algorithm",
        "checksum_representation",
        "byte_verification",
    }
    _CHUNK_SIZE = 1024 * 1024
    _MAX_RETRIES = 4

    def __init__(
        self,
        root: Path,
        *,
        manifest_path: Path | None = None,
        raw_root: Path | None = None,
        output_root: Path | None = None,
        opener: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.manifest_path = manifest_path or self.root / self.MANIFEST_RELATIVE
        self.raw_root = raw_root or self.root / self.RAW_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE
        self._opener = opener or urlopen
        self._sleep = sleep or time.sleep

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RealProteomicsAcquisitionError(f"cannot parse {label}") from exc

    @staticmethod
    def _safe_relative(value: str, label: str) -> Path:
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise RealProteomicsAcquisitionError(f"{label} is not a safe relative path")
        return candidate

    @staticmethod
    def _digest(path: Path, algorithm: str, representation: str) -> str:
        if algorithm != "SHA1":
            raise RealProteomicsAcquisitionError("unsupported publisher checksum algorithm")
        try:
            stream = gzip.open(path, "rb") if representation == "GZIP_DECOMPRESSED_BYTES" else path.open("rb")
            with stream:
                digest = hashlib.sha1()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise RealProteomicsAcquisitionError(
                f"cannot digest publisher checksum representation for {path}"
            ) from exc
        return digest.hexdigest()

    def _assert_local_path(self, path: Path) -> Path:
        resolved = path.resolve(strict=False)
        raw_root = self.raw_root.resolve(strict=False)
        if resolved == raw_root or raw_root not in resolved.parents:
            raise RealProteomicsAcquisitionError("raw transfer path escapes the declared data root")
        return resolved

    def _url(self, archive_prefix: str, file_name: str) -> str:
        url = archive_prefix + quote(file_name)
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != self.ALLOWED_HOST
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise RealProteomicsAcquisitionError("transfer URL is not an approved anonymous PRIDE URL")
        return url

    def _manifest(self) -> tuple[dict[str, Any], tuple[TransferAsset, ...]]:
        manifest = self._json(self.manifest_path, "T123 proteomics transfer manifest")
        if set(manifest) != self.REQUIRED_MANIFEST_FIELDS or manifest.get("schema_version") != 1:
            raise RealProteomicsAcquisitionError("transfer manifest fields or schema are invalid")
        if manifest.get("manifest_id") != self.MANIFEST_ID:
            raise RealProteomicsAcquisitionError("transfer manifest identity is invalid")
        _string(manifest.get("evaluated_at"), "transfer manifest evaluated_at")
        if manifest.get("source_preflight_registry_sha256") != _sha256(
            self.root / self.PREFLIGHT_REGISTRY_RELATIVE
        ):
            raise RealProteomicsAcquisitionError("transfer manifest does not bind preflight registry")
        if manifest.get("source_preflight_receipt_sha256") != _sha256(
            self.root / self.PREFLIGHT_RECEIPT_RELATIVE
        ):
            raise RealProteomicsAcquisitionError("transfer manifest does not bind preflight receipt")

        policy = _mapping(manifest.get("transport_policy"), "transfer transport policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS or any(
            policy.get(field) is not True for field in self.REQUIRED_POLICY_FIELDS - {"allowed_host"}
        ):
            raise RealProteomicsAcquisitionError("transfer policy is unsafe")
        if policy.get("allowed_host") != self.ALLOWED_HOST:
            raise RealProteomicsAcquisitionError("transfer host policy is invalid")

        assets: list[TransferAsset] = []
        source_ids: set[str] = set()
        asset_ids: set[str] = set()
        relative_paths: set[str] = set()
        for source_value in _list(manifest.get("sources"), "transfer sources", minimum=3):
            source = _mapping(source_value, "transfer source")
            if set(source) != self.REQUIRED_SOURCE_FIELDS:
                raise RealProteomicsAcquisitionError("transfer source fields are invalid")
            source_id = _string(source.get("source_id"), "transfer source_id")
            accession = _string(source.get("accession"), "transfer accession")
            if source_id in source_ids or source_id not in self.EXPECTED_SOURCE_COUNTS:
                raise RealProteomicsAcquisitionError("transfer source identity is invalid")
            if accession != source_id.removeprefix("PRIDE-"):
                raise RealProteomicsAcquisitionError("transfer source accession is invalid")
            source_ids.add(source_id)
            archive_prefix = _string(source.get("archive_prefix"), "transfer archive prefix")
            if not archive_prefix.endswith(f"/{accession}/"):
                raise RealProteomicsAcquisitionError("transfer archive prefix is invalid")
            _url = self._url(archive_prefix, "probe")
            if not _url.endswith("/probe"):
                raise RealProteomicsAcquisitionError("transfer archive prefix is malformed")
            source_assets = _list(source.get("assets"), "transfer source assets", minimum=1)
            if _integer(source.get("asset_count"), "transfer source asset count", minimum=1) != len(
                source_assets
            ):
                raise RealProteomicsAcquisitionError("transfer source asset count is invalid")
            if len(source_assets) != self.EXPECTED_SOURCE_COUNTS[source_id]:
                raise RealProteomicsAcquisitionError("transfer source selection changed")
            for asset_value in source_assets:
                asset = _mapping(asset_value, "transfer asset")
                if set(asset) != self.REQUIRED_ASSET_FIELDS:
                    raise RealProteomicsAcquisitionError("transfer asset fields are invalid")
                asset_id = _string(asset.get("asset_id"), "transfer asset_id")
                file_name = _string(asset.get("file_name"), "transfer file_name")
                relative_path = _string(asset.get("relative_path"), "transfer relative_path")
                relative = self._safe_relative(relative_path, "transfer relative_path")
                if relative.parts[0] != accession or relative.name != file_name:
                    raise RealProteomicsAcquisitionError("transfer asset path does not bind its source")
                if asset_id in asset_ids or relative_path in relative_paths:
                    raise RealProteomicsAcquisitionError("transfer asset identity is not unique")
                asset_ids.add(asset_id)
                relative_paths.add(relative_path)
                publisher_api_bytes = _integer(
                    asset.get("publisher_api_bytes"), "transfer publisher_api_bytes", minimum=1
                )
                expected_bytes_value = asset.get("expected_bytes")
                if expected_bytes_value is not None:
                    expected_bytes = _integer(
                        expected_bytes_value, "transfer expected_bytes", minimum=1
                    )
                    if expected_bytes != publisher_api_bytes:
                        raise RealProteomicsAcquisitionError(
                            "exact byte verification must match publisher metadata"
                        )
                else:
                    expected_bytes = None
                checksum = asset.get("publisher_checksum")
                checksum_algorithm = asset.get("publisher_checksum_algorithm")
                representation = _string(
                    asset.get("checksum_representation"), "transfer checksum_representation"
                )
                if checksum is None:
                    if checksum_algorithm is not None or representation != "NOT_AVAILABLE_IN_PRIDE_FILE_RECORD":
                        raise RealProteomicsAcquisitionError(
                            "absent publisher checksum is represented unsafely"
                        )
                else:
                    checksum = _string(checksum, "transfer publisher_checksum").lower()
                    if (
                        checksum_algorithm != "SHA1"
                        or len(checksum) != 40
                        or any(character not in "0123456789abcdef" for character in checksum)
                        or representation not in {"FILE_BYTES", "GZIP_DECOMPRESSED_BYTES"}
                    ):
                        raise RealProteomicsAcquisitionError("publisher checksum contract is invalid")
                byte_verification = _string(
                    asset.get("byte_verification"), "transfer byte_verification"
                )
                if expected_bytes is None:
                    if (
                        source_id != "PRIDE-PXD017776"
                        or byte_verification != "INFORMATIONAL_ONLY_PUBLISHER_API_SIZE_MISMATCH_OBSERVED"
                        or checksum is None
                    ):
                        raise RealProteomicsAcquisitionError("unverified transfer size is not allowed")
                elif byte_verification != "EXACT_FILE_BYTES":
                    raise RealProteomicsAcquisitionError("transfer byte verification is invalid")
                assets.append(
                    TransferAsset(
                        source_id=source_id,
                        accession=accession,
                        asset_id=asset_id,
                        file_name=file_name,
                        relative_path=relative_path,
                        url=self._url(archive_prefix, file_name),
                        role=_string(asset.get("role"), "transfer role"),
                        publisher_api_bytes=publisher_api_bytes,
                        expected_bytes=expected_bytes,
                        publisher_checksum=checksum,
                        publisher_checksum_algorithm=checksum_algorithm,
                        checksum_representation=representation,
                        byte_verification=byte_verification,
                    )
                )
        if source_ids != set(self.EXPECTED_SOURCE_COUNTS) or len(assets) != 27:
            raise RealProteomicsAcquisitionError("transfer cohort selection is incomplete")
        return manifest, tuple(sorted(assets, key=lambda item: item.asset_id))

    def _asset_path(self, asset: TransferAsset) -> Path:
        return self._assert_local_path(self.raw_root / self._safe_relative(asset.relative_path, "asset"))

    def _verify_path(self, path: Path, asset: TransferAsset) -> dict[str, Any]:
        if not path.is_file():
            raise RealProteomicsAcquisitionError(f"required asset is missing: {asset.asset_id}")
        bytes_on_disk = path.stat().st_size
        if asset.expected_bytes is not None and bytes_on_disk != asset.expected_bytes:
            raise RealProteomicsAcquisitionError(
                f"byte count mismatch for {asset.asset_id}: expected {asset.expected_bytes}, got {bytes_on_disk}"
            )
        publisher_checksum_verified = False
        if asset.publisher_checksum is not None:
            actual_checksum = self._digest(
                path, asset.publisher_checksum_algorithm or "", asset.checksum_representation
            )
            if actual_checksum != asset.publisher_checksum:
                raise RealProteomicsAcquisitionError(
                    f"publisher checksum mismatch for {asset.asset_id}: expected "
                    f"{asset.publisher_checksum}, got {actual_checksum}"
                )
            publisher_checksum_verified = True
        return {
            "asset_id": asset.asset_id,
            "source_id": asset.source_id,
            "accession": asset.accession,
            "relative_path": asset.relative_path,
            "download_url": asset.url,
            "role": asset.role,
            "bytes_on_disk": bytes_on_disk,
            "publisher_api_bytes": asset.publisher_api_bytes,
            "expected_bytes": asset.expected_bytes,
            "byte_verification": asset.byte_verification,
            "publisher_checksum": asset.publisher_checksum,
            "publisher_checksum_algorithm": asset.publisher_checksum_algorithm,
            "checksum_representation": asset.checksum_representation,
            "publisher_checksum_verified": publisher_checksum_verified,
            "local_sha256": _sha256(path),
        }

    def _event(self, value: dict[str, Any]) -> None:
        self.raw_root.mkdir(parents=True, exist_ok=True)
        event = {
            "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "manifest_sha256": _sha256(self.manifest_path),
            **value,
        }
        event_path = self._assert_local_path(self.raw_root / self.EVENT_LOG_NAME)
        with event_path.open("ab") as stream:
            stream.write(_canonical(event))
            stream.flush()
            os.fsync(stream.fileno())

    def _open(self, request: Request) -> Any:
        retryable = {429, 500, 502, 503, 504}
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                response = self._opener(request, timeout=120)
                status = int(getattr(response, "status", None) or response.getcode() or 200)
                if 200 <= status < 300:
                    return response
                close = getattr(response, "close", None)
                if close is not None:
                    close()
                if status not in retryable or attempt >= self._MAX_RETRIES:
                    raise RealProteomicsAcquisitionError(
                        f"unexpected HTTP status {status} for {request.full_url}"
                    )
            except HTTPError as exc:
                if exc.code not in retryable or attempt >= self._MAX_RETRIES:
                    raise RealProteomicsAcquisitionError(
                        f"HTTP {exc.code} for {request.full_url}"
                    ) from exc
            except (URLError, TimeoutError) as exc:
                if attempt >= self._MAX_RETRIES:
                    raise RealProteomicsAcquisitionError(
                        f"transport failure for {request.full_url}"
                    ) from exc
            self._sleep(float(2**attempt))
        raise RealProteomicsAcquisitionError("transfer retry loop ended unexpectedly")

    @staticmethod
    def _status(response: Any) -> int:
        return int(getattr(response, "status", None) or response.getcode() or 200)

    @staticmethod
    def _header(response: Any, name: str) -> str | None:
        headers = getattr(response, "headers", None)
        if headers is None:
            return None
        value = headers.get(name) or headers.get(name.lower())
        return str(value).strip() if value is not None else None

    def _download(self, asset: TransferAsset) -> dict[str, Any]:
        destination = self._asset_path(asset)
        if destination.exists():
            record = self._verify_path(destination, asset)
            self._event({"event": "ALREADY_VERIFIED", **record})
            return record
        partial = self._assert_local_path(Path(f"{destination}.part"))
        partial.parent.mkdir(parents=True, exist_ok=True)
        existing_bytes = partial.stat().st_size if partial.is_file() else 0
        request = Request(asset.url, method="GET", headers={"User-Agent": PROJECT_USER_AGENT})
        if existing_bytes:
            request.add_header("Range", f"bytes={existing_bytes}-")
        self._event(
            {
                "event": "TRANSFER_STARTED",
                "asset_id": asset.asset_id,
                "source_id": asset.source_id,
                "resume_bytes": existing_bytes,
                "download_url": asset.url,
            }
        )
        response = self._open(request)
        try:
            status = self._status(response)
            append = existing_bytes > 0 and status == 206
            if existing_bytes > 0 and status == 206:
                content_range = self._header(response, "Content-Range")
                if content_range is None or not content_range.startswith(f"bytes {existing_bytes}-"):
                    raise RealProteomicsAcquisitionError("server returned an incompatible Content-Range")
            elif existing_bytes > 0 and status == 200:
                preserved = self._assert_local_path(
                    Path(f"{partial}.range-ignored-{existing_bytes}")
                )
                if preserved.exists():
                    raise RealProteomicsAcquisitionError(
                        f"cannot preserve existing partial without overwrite: {preserved}"
                    )
                os.replace(partial, preserved)
                append = False
            elif status != 200:
                raise RealProteomicsAcquisitionError(
                    f"unexpected download status {status} for {asset.asset_id}"
                )
            mode = "ab" if append else "wb"
            with partial.open(mode) as stream:
                while True:
                    chunk = response.read(self._CHUNK_SIZE)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise RealProteomicsAcquisitionError("HTTP stream did not return bytes")
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                close()
        try:
            record = self._verify_path(partial, asset)
        except RealProteomicsAcquisitionError as exc:
            self._event(
                {
                    "event": "TRANSFER_UNVERIFIED_PARTIAL_PRESERVED",
                    "asset_id": asset.asset_id,
                    "source_id": asset.source_id,
                    "partial_path": str(partial.relative_to(self.raw_root)),
                    "reason": str(exc),
                }
            )
            raise
        os.replace(partial, destination)
        self._event({"event": "TRANSFER_VERIFIED", **record})
        return record

    @staticmethod
    def _select(assets: Iterable[TransferAsset], source_ids: Iterable[str] | None) -> tuple[TransferAsset, ...]:
        requested = set(source_ids or ())
        known = {asset.source_id for asset in assets}
        if requested and not requested <= known:
            unknown = ", ".join(sorted(requested - known))
            raise RealProteomicsAcquisitionError(f"unknown transfer source: {unknown}")
        return tuple(asset for asset in assets if not requested or asset.source_id in requested)

    def stage(
        self, *, strict: bool = False, source_ids: Iterable[str] | None = None
    ) -> RealProteomicsAcquisitionSummary:
        """Download a selected source subset into ignored raw storage with verification."""

        if not strict:
            raise RealProteomicsAcquisitionError("proteomics source acquisition requires --strict")
        _, assets = self._manifest()
        selected = self._select(assets, source_ids)
        if not selected:
            raise RealProteomicsAcquisitionError("transfer selection is empty")
        records = [self._download(asset) for asset in selected]
        return RealProteomicsAcquisitionSummary(
            asset_count=len(records),
            source_count=len({record["source_id"] for record in records}),
            publisher_checksum_verified_count=sum(
                record["publisher_checksum_verified"] for record in records
            ),
            receipt_path=None,
        )

    def _records(self) -> tuple[dict[str, Any], tuple[TransferAsset, ...], list[dict[str, Any]]]:
        manifest, assets = self._manifest()
        records = [self._verify_path(self._asset_path(asset), asset) for asset in assets]
        return manifest, assets, records

    def run(self, *, strict: bool = False) -> RealProteomicsAcquisitionSummary:
        """Freeze one immutable receipt after every selected source asset is verified."""

        if not strict:
            raise RealProteomicsAcquisitionError("proteomics acquisition audit requires --strict")
        if self.output_root.exists():
            raise RealProteomicsAcquisitionError("real proteomics acquisition audit already executed")
        manifest, assets, records = self._records()
        if len(records) != 27 or len({record["source_id"] for record in records}) != 3:
            raise RealProteomicsAcquisitionError("full transfer cohort is incomplete")
        verified_count = sum(record["publisher_checksum_verified"] for record in records)
        decision = {
            "schema_version": 1,
            "audit_id": "bioif-r2-real-proteomics-acquisition-v1.0.0",
            "evaluated_at": manifest["evaluated_at"],
            "transfer_manifest_sha256": _sha256(self.manifest_path),
            "source_preflight_registry_sha256": manifest["source_preflight_registry_sha256"],
            "source_preflight_receipt_sha256": manifest["source_preflight_receipt_sha256"],
            "asset_count": len(records),
            "source_count": len({record["source_id"] for record in records}),
            "publisher_checksum_verified_count": verified_count,
            "publisher_checksum_unavailable_count": len(records) - verified_count,
            "assets": records,
            "status": "STAGED_REAL_AUTHOR_RESULTS_NOT_A_MODEL_TARGET",
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "author_quantification_concatenated": False,
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
            "required_before_target_freeze": [
                "Resolve PXD052701 covariates from a source-matched reusable record without inferring L/S names.",
                "Define and lock one common parser, protein-crown endpoint and analysis-unit manifest.",
                "Revise the T121 analysis plan before any fit, ablation, OOD or external evaluation.",
            ],
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "acquisition_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": decision["audit_id"],
            "status": decision["status"],
            "acquisition_decision_sha256": _sha256(decision_path),
            "asset_count": decision["asset_count"],
            "source_count": decision["source_count"],
            "publisher_checksum_verified_count": verified_count,
            "publisher_checksum_unavailable_count": len(records) - verified_count,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "acquisition_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return RealProteomicsAcquisitionSummary(
            asset_count=len(records),
            source_count=3,
            publisher_checksum_verified_count=verified_count,
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify an immutable full-transfer receipt without changing it."""

        decision_path = self.output_root / "acquisition_decision.json"
        receipt_path = self.output_root / "acquisition_receipt.json"
        decision = self._json(decision_path, "proteomics acquisition decision")
        receipt = self._json(receipt_path, "proteomics acquisition receipt")
        required_false = (
            "model_fitted",
            "paired_ablations_run",
            "external_ood_evaluated",
            "negative_controls_run",
            "independent_validation",
            "scientific_submission_ready",
        )
        if (
            receipt.get("audit_id") != "bioif-r2-real-proteomics-acquisition-v1.0.0"
            or receipt.get("status") != "STAGED_REAL_AUTHOR_RESULTS_NOT_A_MODEL_TARGET"
            or decision.get("status") != receipt["status"]
            or receipt.get("acquisition_decision_sha256") != _sha256(decision_path)
            or receipt.get("asset_count") != 27
            or receipt.get("source_count") != 3
            or receipt.get("publisher_checksum_verified_count") != 16
            or receipt.get("publisher_checksum_unavailable_count") != 11
            or receipt.get("target_status") != "NOT_FROZEN"
            or receipt.get("model_use") != "PROHIBITED"
            or decision.get("target_status") != "NOT_FROZEN"
            or decision.get("model_use") != "PROHIBITED"
            or decision.get("author_quantification_concatenated") is not False
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise RealProteomicsAcquisitionError("proteomics acquisition receipt is invalid")
        return receipt
