"""Anonymous Europe PMC search and asset adapter."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AssetDescriptor,
    FetchResult,
    SourceAdapter,
    SourceQuery,
)

SEARCH_ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
REST_ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest"


@dataclass(frozen=True)
class EuropePmcConfig:
    """Pinned official endpoint and bounded query settings."""

    page_size: int = 25
    max_pages: int = 20

    def __post_init__(self) -> None:
        if not 0 < self.page_size <= 1000:
            raise AdapterError("page_size must be between 1 and 1000")
        if not 0 < self.max_pages <= 100:
            raise AdapterError("max_pages must be between 1 and 100")


class EuropePmcAdapter(SourceAdapter):
    """Europe PMC adapter using only the official anonymous REST endpoint."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: EuropePmcConfig | None = None,
    ) -> None:
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=0.2,
                allowed_hosts=("www.ebi.ac.uk",),
            ),
        )
        super().__init__(root, policy, network)
        self.config = config or EuropePmcConfig()

    @property
    def name(self) -> str:
        return "europe_pmc"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _search_url(self, query: str, cursor: str) -> str:
        params = (
            ("cursorMark", cursor),
            ("format", "json"),
            ("pageSize", str(self.config.page_size)),
            ("query", query),
            ("resultType", "core"),
        )
        return SEARCH_ENDPOINT + "?" + urlencode(params)

    @staticmethod
    def _result_list(page: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        result_list = page.get("resultList", {})
        if not isinstance(result_list, Mapping):
            raise AdapterError("Europe PMC resultList is not an object")
        results = result_list.get("result", [])
        if not isinstance(results, list) or not all(isinstance(item, Mapping) for item in results):
            raise AdapterError("Europe PMC resultList.result is invalid")
        return [item for item in results if isinstance(item, Mapping)]

    @staticmethod
    def _candidate(result: Mapping[str, Any]) -> SourceCandidate:
        accession_value = result.get("pmcid") or result.get("id")
        if not isinstance(accession_value, str) or not accession_value:
            raise AdapterError("Europe PMC result has no accession")
        pmcid = result.get("pmcid")
        identifier = f"europepmc:{accession_value}"
        url = (
            f"https://europepmc.org/articles/{pmcid}"
            if isinstance(pmcid, str) and pmcid
            else f"https://europepmc.org/article/{result.get('source', 'MED')}/{accession_value}"
        )
        license_value = result.get("license")
        license_text = license_value if isinstance(license_value, str) else None
        publication_date = result.get("firstPublicationDate")
        if not isinstance(publication_date, str) or len(publication_date) != 10:
            publication_date = None
        return SourceCandidate.from_mapping(
            {
                "source_id": identifier,
                "source_name": "Europe PMC",
                "url": url,
                "accession": accession_value,
                "license_identifier": license_text,
                "license_text": license_text,
                "evidence_location": "Europe PMC REST search result",
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
        """Search with cursorMark pagination and repeated-cursor protection."""
        cursor = "*"
        seen: set[str] = set()
        candidates: list[SourceCandidate] = []
        seen_sources: set[str] = set()
        for _ in range(self.config.max_pages):
            if cursor in seen:
                raise AdapterError(f"Europe PMC cursor repeated: {cursor}")
            seen.add(cursor)
            page = self.client.get_json(self._search_url(query.text, cursor))  # type: ignore[union-attr]
            if not isinstance(page, Mapping):
                raise AdapterError("Europe PMC response is not an object")
            for result in self._result_list(page):
                candidate = self._candidate(result)
                if candidate.source_id not in seen_sources:
                    candidates.append(candidate)
                    seen_sources.add(candidate.source_id)
            next_cursor = page.get("nextCursorMark")
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor or next_cursor == "*":
                return tuple(candidates[: query.limit])
            if next_cursor in seen:
                raise AdapterError(f"Europe PMC cursor repeated: {next_cursor}")
            cursor = next_cursor
        raise AdapterError("Europe PMC pagination exceeded max_pages")

    def metadata(self, candidate: SourceCandidate) -> Mapping[str, Any]:
        """Retrieve one result record and add official full-text links."""
        self.require_admitted(candidate)
        if candidate.accession is None:
            raise AdapterError("candidate has no accession")
        page = self.client.get_json(  # type: ignore[union-attr]
            self._search_url(f"EXT_ID:{candidate.accession}", "*")
        )
        if not isinstance(page, Mapping):
            raise AdapterError("Europe PMC metadata response is not an object")
        results = self._result_list(page)
        result = results[0] if results else {}
        pmcid = result.get("pmcid") if isinstance(result, Mapping) else None
        pmcid_value = pmcid if isinstance(pmcid, str) else None
        return {
            "source_id": candidate.source_id,
            "accession": candidate.accession,
            "title": result.get("title") if isinstance(result, Mapping) else None,
            "publication_date": (result.get("firstPublicationDate") if isinstance(result, Mapping) else None),
            "license": candidate.license_identifier,
            "full_text_url": self._full_text_url(pmcid_value),
            "supplementary_url": self._supplementary_url(pmcid_value),
            "evidence_location": "Europe PMC REST metadata result",
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """List official full-text XML and supplementary-file endpoints."""
        self.require_admitted(candidate)
        if candidate.accession is None or not candidate.accession.upper().startswith("PMC"):
            return ()
        pmcid = candidate.accession
        license_value = candidate.license_identifier
        return (
            AssetDescriptor(
                asset_id=hashlib.sha256(f"{candidate.source_id}|{pmcid}|fulltext_xml".encode()).hexdigest(),
                source_id=candidate.source_id,
                url=self._full_text_url(pmcid) or "",
                asset_type="JATS",
                accession=pmcid,
                sha256=None,
                size_bytes=None,
                license=license_value,
            ),
            AssetDescriptor(
                asset_id=hashlib.sha256(f"{candidate.source_id}|{pmcid}|supplementary".encode()).hexdigest(),
                source_id=candidate.source_id,
                url=self._supplementary_url(pmcid) or "",
                asset_type="SUPPLEMENTARY",
                accession=pmcid,
                sha256=None,
                size_bytes=None,
                license=license_value,
            ),
        )

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Fetch only a manifest asset with an explicit expected checksum."""
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        if not asset.sha256:
            raise AdapterError("Europe PMC fetch requires manifest SHA-256")
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        return_path = self.client.download(
            asset.url,
            destination,
            expected_sha256=asset.sha256,
        )
        return FetchResult(return_path, asset.sha256, return_path.stat().st_size)

    @staticmethod
    def _full_text_url(pmcid: str | None) -> str | None:
        return f"{REST_ENDPOINT}/{pmcid}/fullTextXML" if pmcid else None

    @staticmethod
    def _supplementary_url(pmcid: str | None) -> str | None:
        return f"{REST_ENDPOINT}/{pmcid}/supplementaryFiles" if pmcid else None
