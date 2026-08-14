"""Anonymous PRIDE Archive project and file-manifest adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AssetDescriptor,
    FetchResult,
    SourceAdapter,
    SourceQuery,
)

PRIDE_HOST = "www.ebi.ac.uk"
PRIDE_FTP_HOST = "ftp.pride.ebi.ac.uk"
PROJECT_ENDPOINT = "https://www.ebi.ac.uk/pride/ws/archive/v3/projects/"
SEARCH_ENDPOINT = "https://www.ebi.ac.uk/pride/ws/archive/v3/search/projects"
FILES_ENDPOINT = "https://www.ebi.ac.uk/pride/ws/archive/v3/projects/files-path/"
DOWNLOAD_ENDPOINT = "https://www.ebi.ac.uk/pride/ws/archive-file-downloader/files/s3/"
PROJECT_ACCESSION_PREFIXES = ("PXD", "PXV", "PXR", "PRD")


@dataclass(frozen=True)
class PrideConfig:
    """Bounded PRIDE query and large-file settings."""

    page_size: int = 25
    max_projects: int = 20
    large_file_threshold: int = 1_000_000_000

    def __post_init__(self) -> None:
        if not 0 < self.page_size <= 1000:
            raise AdapterError("page_size must be between 1 and 1000")
        if not 0 < self.max_projects <= 100:
            raise AdapterError("max_projects must be between 1 and 100")
        if self.large_file_threshold <= 0:
            raise AdapterError("large_file_threshold must be positive")


@dataclass(frozen=True)
class PrideFile:
    """Normalized PRIDE file metadata before policy and asset projection."""

    name: str
    url: str
    size_bytes: int | None
    checksum: str | None
    checksum_type: str | None
    category: str | None
    available: bool


class PrideAdapter(SourceAdapter):
    """Use only anonymous PRIDE Archive REST and official HTTPS file links."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: PrideConfig | None = None,
    ) -> None:
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=0.2,
                allowed_hosts=(PRIDE_HOST, PRIDE_FTP_HOST),
            ),
        )
        super().__init__(root, policy, network)
        self.config = config or PrideConfig()

    @property
    def name(self) -> str:
        return "pride"

    @property
    def version(self) -> str:
        return "1.0.0"

    @staticmethod
    def _normalize_accession(value: str) -> str:
        accession = value.strip().upper()
        if not any(
            accession.startswith(prefix) and accession[len(prefix) :].isdigit() for prefix in PROJECT_ACCESSION_PREFIXES
        ):
            raise AdapterError("PRIDE queries require a project accession such as PXD000001")
        return accession

    @staticmethod
    def _project_url(accession: str) -> str:
        return PROJECT_ENDPOINT + accession

    @staticmethod
    def _files_url(accession: str) -> str:
        return FILES_ENDPOINT + accession

    @staticmethod
    def _search_url(text: str, config: PrideConfig) -> str:
        params = (
            ("keyword", text),
            ("page", "0"),
            ("pageSize", str(config.page_size)),
            ("sortDirection", "DESC"),
            ("sortFields", "submissionDate"),
        )
        return SEARCH_ENDPOINT + "?" + urlencode(params)

    def _get_json(self, url: str) -> tuple[Any, str]:
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        payload = self.client.get_bytes(url)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"PRIDE response is not valid JSON: {url}") from exc
        return value, hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
        if isinstance(value, Mapping):
            for key in ("content", "results", "projects", "files", "items"):
                nested = value.get(key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, Mapping)]
            embedded = value.get("_embedded")
            if isinstance(embedded, Mapping):
                return PrideAdapter._mapping_list(embedded)
        return []

    @staticmethod
    def _text(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    @staticmethod
    def _project_accession(record: Mapping[str, Any]) -> str | None:
        for key in ("accession", "projectAccession", "project_accession", "id"):
            value = PrideAdapter._text(record.get(key))
            if value is not None:
                try:
                    return PrideAdapter._normalize_accession(value)
                except AdapterError:
                    continue
        return None

    @staticmethod
    def _license(record: Mapping[str, Any]) -> str | None:
        return PrideAdapter._text(record.get("license") or record.get("licenseText"))

    @staticmethod
    def _candidate(record: Mapping[str, Any]) -> SourceCandidate:
        accession = PrideAdapter._project_accession(record)
        if accession is None:
            raise AdapterError("PRIDE project record has no valid accession")
        license_value = PrideAdapter._license(record)
        return SourceCandidate.from_mapping(
            {
                "source_id": f"pride:{accession}",
                "source_name": "PRIDE Archive",
                "url": PrideAdapter._project_url(accession),
                "accession": accession,
                "license_identifier": license_value,
                "license_text": license_value,
                "evidence_location": "PRIDE Archive REST v3 project record",
                "registration_required": False,
                "login_required": False,
                "api_key_required": False,
                "application_required": False,
                "approval_required": False,
                "institution_required": False,
                "data_use_agreement_required": False,
                "paid_required": False,
            }
        )

    def _project(self, accession: str) -> tuple[Mapping[str, Any], str]:
        value, response_sha256 = self._get_json(self._project_url(accession))
        if not isinstance(value, Mapping):
            raise AdapterError("PRIDE project response is not an object")
        return value, response_sha256

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Search projects by accession or official keyword endpoint."""
        text = query.text.strip()
        if text.upper().startswith(PROJECT_ACCESSION_PREFIXES):
            accession = self._normalize_accession(text)
            record, _ = self._project(accession)
            return (self._candidate(record),)
        value, _ = self._get_json(self._search_url(text, self.config))
        records = self._mapping_list(value)
        candidates: list[SourceCandidate] = []
        seen: set[str] = set()
        for record in records[: self.config.max_projects]:
            try:
                candidate = self._candidate(record)
            except AdapterError:
                continue
            if candidate.source_id not in seen:
                candidates.append(candidate)
                seen.add(candidate.source_id)
        return tuple(candidates[: query.limit])

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return accession, date, species, instruments, license, and provenance."""
        self.require_admitted(candidate)
        accession = self._candidate_accession(candidate)
        record, response_sha256 = self._project(accession)
        return {
            "source_id": candidate.source_id,
            "accession": accession,
            "title": self._text(record.get("title")),
            "submission_date": self._text(record.get("submissionDate") or record.get("submission_date")),
            "publication_date": self._text(record.get("publicationDate") or record.get("publication_date")),
            "species": self._names(record.get("organisms") or record.get("species")),
            "instruments": self._names(record.get("instruments")),
            "license": self._license(record),
            "doi": self._text(record.get("doi")),
            "file_manifest_url": self._files_url(accession),
            "request_url": self._project_url(accession),
            "response_sha256": response_sha256,
            "evidence_location": "PRIDE Archive REST v3 project record",
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """List available project files with checksum and official URLs."""
        self.require_admitted(candidate)
        accession = self._candidate_accession(candidate)
        value, _ = self._get_json(self._files_url(accession))
        files = self._files(value, accession)
        assets: list[AssetDescriptor] = []
        for item in files:
            if not item.available:
                continue
            sha256 = self._sha256_if_supported(item.checksum, item.checksum_type)
            asset_type = (item.category or self._file_type(item.name)).upper()
            asset_id = hashlib.sha256(f"{candidate.source_id}|{item.name}|{item.url}".encode()).hexdigest()
            assets.append(
                AssetDescriptor(
                    asset_id=asset_id,
                    source_id=candidate.source_id,
                    url=item.url,
                    asset_type=asset_type,
                    accession=accession,
                    sha256=sha256,
                    size_bytes=item.size_bytes,
                    license=candidate.license_identifier,
                )
            )
        return tuple(assets)

    def dry_run(self, candidate: SourceCandidate, asset: AssetDescriptor) -> dict[str, Any]:
        """Return a bounded large-file plan without downloading bytes."""
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        if not asset.sha256:
            raise AdapterError("PRIDE dry-run requires a SHA-256 checksum")
        size = asset.size_bytes or 0
        return {
            "asset_id": asset.asset_id,
            "accession": asset.accession,
            "url": asset.url,
            "sha256": asset.sha256,
            "size_bytes": asset.size_bytes,
            "large_file": size >= self.config.large_file_threshold,
            "downloaded": False,
        }

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Fetch an available project file only with a verified SHA-256."""
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        if not asset.sha256:
            raise AdapterError("PRIDE fetch requires an API or manifest SHA-256")
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        path = self.client.download(
            asset.url,
            destination,
            expected_sha256=asset.sha256,
        )
        return FetchResult(path, asset.sha256, path.stat().st_size)

    @staticmethod
    def _candidate_accession(candidate: SourceCandidate) -> str:
        if candidate.accession is None:
            raise AdapterError("candidate has no accession")
        return PrideAdapter._normalize_accession(candidate.accession)

    @staticmethod
    def _names(value: Any) -> list[str]:
        if isinstance(value, list):
            names: list[str] = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    names.append(item.strip())
                elif isinstance(item, Mapping):
                    name = PrideAdapter._text(item.get("name") or item.get("value"))
                    if name:
                        names.append(name)
            return names
        value_text = PrideAdapter._text(value)
        return [value_text] if value_text else []

    @staticmethod
    def _files(value: Any, accession: str) -> list[PrideFile]:
        records = PrideAdapter._mapping_list(value)
        if isinstance(value, Mapping) and not records:
            records = [value]
        files: list[PrideFile] = []
        for record in records:
            name = PrideAdapter._text(record.get("fileName") or record.get("filename") or record.get("name"))
            href = PrideAdapter._text(
                record.get("downloadLink")
                or record.get("url")
                or record.get("ftp")
                or record.get("filePath")
                or record.get("path")
            )
            if not name or not href:
                continue
            try:
                url = PrideAdapter._public_url(href, accession)
            except AdapterError:
                continue
            checksum = PrideAdapter._text(
                record.get("sha256") or record.get("sha256sum") or record.get("checksum") or record.get("fileChecksum")
            )
            checksum_type = PrideAdapter._text(record.get("checksumType") or record.get("fileChecksumType"))
            category = PrideAdapter._text(
                record.get("fileType") or record.get("fileCategory") or record.get("category")
            )
            access = " ".join(str(record.get(key, "")).upper() for key in ("access", "availability", "status"))
            available = not any(word in access for word in ("RESTRICTED", "UNAVAILABLE", "PRIVATE"))
            files.append(
                PrideFile(
                    name=name,
                    url=url,
                    size_bytes=PrideAdapter._int(
                        record.get("fileSize") or record.get("size") or record.get("file_size")
                    ),
                    checksum=checksum,
                    checksum_type=checksum_type,
                    category=category,
                    available=available,
                )
            )
        return files

    @staticmethod
    def _public_url(href: str, accession: str) -> str:
        parsed = urlsplit(href)
        if parsed.scheme == "ftp" and parsed.hostname == PRIDE_FTP_HOST:
            return urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, parsed.fragment))
        if parsed.scheme == "https" and parsed.hostname in {PRIDE_HOST, PRIDE_FTP_HOST}:
            return href
        if parsed.scheme == "" and not parsed.netloc:
            return urljoin(
                "https://ftp.pride.ebi.ac.uk/pride/data/archive/",
                href.lstrip("/"),
            )
        raise AdapterError("PRIDE file URL is not an official HTTPS/FTP link")

    @staticmethod
    def _sha256_if_supported(checksum: str | None, checksum_type: str | None) -> str | None:
        if checksum is None or len(checksum) != 64:
            return None
        if any(character not in "0123456789abcdefABCDEF" for character in checksum):
            return None
        normalized_type = (checksum_type or "").replace("-", "").replace("_", "").upper()
        if normalized_type in {"", "SHA256"}:
            return checksum.lower()
        return None

    @staticmethod
    def _file_type(name: str) -> str:
        suffix = Path(name).suffix.lower().lstrip(".")
        return suffix or "UNKNOWN"
