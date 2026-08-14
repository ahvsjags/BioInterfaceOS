"""Anonymous PMC Open Access file-list adapter."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AssetDescriptor,
    FetchResult,
    SourceAdapter,
    SourceQuery,
)

OA_ENDPOINT = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
OA_HOSTS = ("www.ncbi.nlm.nih.gov", "ftp.ncbi.nlm.nih.gov")


@dataclass(frozen=True)
class PmcOaConfig:
    """Bounded PMC OA file-list query settings."""

    max_records: int = 20

    def __post_init__(self) -> None:
        if not 0 < self.max_records <= 100:
            raise AdapterError("max_records must be between 1 and 100")


@dataclass(frozen=True)
class PmcOaRecord:
    """One sanitized record returned by the official OA Web Service."""

    accession: str
    citation: str | None
    license_identifier: str | None
    links: tuple[tuple[str, str], ...]


class PmcOaAdapter(SourceAdapter):
    """Use only the official anonymous PMC OA Web Service and file links."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: PmcOaConfig | None = None,
    ) -> None:
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=0.2,
                allowed_hosts=OA_HOSTS,
            ),
        )
        super().__init__(root, policy, network)
        self.config = config or PmcOaConfig()

    @property
    def name(self) -> str:
        return "pmc_oa"

    @property
    def version(self) -> str:
        return "1.0.0"

    @staticmethod
    def _normalize_accession(value: str) -> str:
        accession = value.strip().upper()
        if not accession.startswith("PMC") or not accession[3:].isdigit():
            raise AdapterError("PMC OA queries require PMC accessions such as PMC123")
        return accession

    @staticmethod
    def _request_url(accession: str) -> str:
        return OA_ENDPOINT + "?" + urlencode((("id", accession),))

    def _record(self, accession: str) -> tuple[PmcOaRecord | None, str, str]:
        request_url = self._request_url(accession)
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        payload = self.client.get_bytes(request_url)
        response_sha256 = hashlib.sha256(payload).hexdigest()
        try:
            document = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise AdapterError("PMC OA response is not valid XML") from exc
        if document.tag != "OA":
            raise AdapterError("PMC OA response root must be OA")
        record = document.find("./records/record")
        if record is None:
            record = document.find("./record")
        if record is None:
            return None, request_url, response_sha256
        record_id = record.attrib.get("id")
        if record_id is None or record_id.upper() != accession:
            raise AdapterError("PMC OA response accession mismatch")
        links: list[tuple[str, str]] = []
        for link in record.findall("./link"):
            file_format = link.attrib.get("format")
            href = link.attrib.get("href")
            if file_format and href:
                links.append((file_format.strip().lower(), href.strip()))
        license_value = record.attrib.get("license")
        if license_value is not None:
            license_value = license_value.strip() or None
        citation = record.attrib.get("citation")
        return (
            PmcOaRecord(
                accession=accession,
                citation=citation.strip() if citation else None,
                license_identifier=license_value,
                links=tuple(links),
            ),
            request_url,
            response_sha256,
        )

    @staticmethod
    def _candidate(
        accession: str,
        record: PmcOaRecord | None,
    ) -> SourceCandidate:
        license_value = record.license_identifier if record else None
        evidence = "PMC OA Web Service record" if record is not None else "PMC OA Web Service non-OA response"
        return SourceCandidate.from_mapping(
            {
                "source_id": f"pmc_oa:{accession}",
                "source_name": "PMC Open Access Subset",
                "url": PmcOaAdapter._request_url(accession),
                "accession": accession,
                "license_identifier": license_value,
                "license_text": license_value,
                "evidence_location": evidence,
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

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Resolve explicit PMC accessions through the OA file-list service."""
        accessions: list[str] = []
        for token in query.text.replace(",", " ").split():
            accession = self._normalize_accession(token)
            if accession not in accessions:
                accessions.append(accession)
        if not accessions:
            raise AdapterError("PMC OA search requires at least one accession")
        if len(accessions) > self.config.max_records:
            raise AdapterError("PMC OA query exceeded max_records")
        candidates: list[SourceCandidate] = []
        for accession in accessions:
            record, _, _ = self._record(accession)
            candidates.append(self._candidate(accession, record))
        return tuple(candidates[: query.limit])

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return OA membership, explicit license, links, and response provenance."""
        self.require_admitted(candidate)
        if candidate.accession is None:
            raise AdapterError("candidate has no accession")
        accession = self._normalize_accession(candidate.accession)
        record, request_url, response_sha256 = self._record(accession)
        if record is None:
            raise AdapterError("candidate is not in the PMC Open Access Subset")
        return {
            "source_id": candidate.source_id,
            "accession": accession,
            "open_access_subset": True,
            "citation": record.citation,
            "license": record.license_identifier,
            "links": [{"format": file_format, "url": self._public_url(href)} for file_format, href in record.links],
            "request_url": request_url,
            "response_sha256": response_sha256,
            "evidence_location": "PMC OA Web Service record",
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """List OA package, JATS/XML, figures, PDF, and supplementary links."""
        self.require_admitted(candidate)
        if candidate.accession is None:
            raise AdapterError("candidate has no accession")
        accession = self._normalize_accession(candidate.accession)
        record, _, _ = self._record(accession)
        if record is None:
            raise AdapterError("candidate is not in the PMC Open Access Subset")
        if not record.links:
            raise AdapterError("PMC OA record has no file links")
        assets: list[AssetDescriptor] = []
        for file_format, href in record.links:
            url = self._public_url(href)
            asset_type = self._asset_type(file_format)
            asset_id = hashlib.sha256(f"{candidate.source_id}|{asset_type}|{url}".encode()).hexdigest()
            assets.append(
                AssetDescriptor(
                    asset_id=asset_id,
                    source_id=candidate.source_id,
                    url=url,
                    asset_type=asset_type,
                    accession=accession,
                    sha256=None,
                    size_bytes=None,
                    license=candidate.license_identifier,
                )
            )
        return tuple(assets)

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Fetch an admitted OA asset only with a manifest checksum."""
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        if not asset.sha256:
            raise AdapterError("PMC OA fetch requires manifest SHA-256")
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        path = self.client.download(
            asset.url,
            destination,
            expected_sha256=asset.sha256,
        )
        return FetchResult(path, asset.sha256, path.stat().st_size)

    @staticmethod
    def _public_url(href: str) -> str:
        parsed = urlsplit(href)
        if parsed.scheme == "ftp" and parsed.hostname in OA_HOSTS:
            return urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, parsed.fragment))
        if parsed.scheme != "https" or parsed.hostname not in OA_HOSTS:
            raise AdapterError("PMC OA link is not an official HTTPS/FTP URL")
        return href

    @staticmethod
    def _asset_type(file_format: str) -> str:
        normalized = file_format.lower().replace("-", "_")
        return {
            "tgz": "OA_PACKAGE",
            "tar_gz": "OA_PACKAGE",
            "xml": "JATS",
            "jats": "JATS",
            "pdf": "PDF",
            "figure": "FIGURE",
            "figures": "FIGURE",
            "supplement": "SUPPLEMENTARY",
            "supplementary": "SUPPLEMENTARY",
        }.get(normalized, normalized.upper())
