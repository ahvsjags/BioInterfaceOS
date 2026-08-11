"""Anonymous metadata and release-asset adapters for public repositories."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AssetDescriptor,
    FetchResult,
    SourceAdapter,
    SourceQuery,
)

HOSTS = ("zenodo.org", "api.figshare.com", "api.osf.io", "api.github.com")
PROVIDERS = ("zenodo", "figshare", "osf", "github")
PROVIDER_NAMES = {
    "zenodo": "Zenodo",
    "figshare": "Figshare",
    "osf": "Open Science Framework",
    "github": "GitHub",
}


@dataclass(frozen=True)
class RepositoryConfig:
    """Bounded public-repository query settings."""

    page_size: int = 20
    max_pages: int = 5
    rate_interval: float = 0.2

    def __post_init__(self) -> None:
        if not 0 < self.page_size <= 100:
            raise AdapterError("page_size must be between 1 and 100")
        if not 0 < self.max_pages <= 20:
            raise AdapterError("max_pages must be between 1 and 20")
        if self.rate_interval < 0.2:
            raise AdapterError("rate_interval must be at least 0.2 seconds")


class RepositoryAdapter(SourceAdapter):
    """Resolve public repository releases without credentials or code execution."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: RepositoryConfig | None = None,
    ) -> None:
        self.config = config or RepositoryConfig()
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=self.config.rate_interval,
                allowed_hosts=HOSTS,
            ),
        )
        super().__init__(root, policy, network)

    @property
    def name(self) -> str:
        return "repositories"

    @property
    def version(self) -> str:
        return "1.0.0"

    @staticmethod
    def _parse_query(text: str) -> tuple[str, str]:
        stripped = text.strip()
        if ":" not in stripped:
            raise AdapterError("repository query must be provider:identifier")
        provider, identifier = stripped.split(":", 1)
        if provider.lower() == "repository":
            if ":" not in identifier:
                raise AdapterError("repository query must include provider")
            provider, identifier = identifier.split(":", 1)
        provider = provider.lower().strip()
        identifier = identifier.strip()
        if provider not in PROVIDERS or not identifier:
            raise AdapterError("unknown repository provider or empty identifier")
        if provider == "github" and not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:@[A-Za-z0-9_.-]+)?",
            identifier,
        ):
            raise AdapterError("GitHub query must be owner/repository or owner/repository@tag")
        return provider, identifier

    @staticmethod
    def _github_parts(identifier: str) -> tuple[str, str | None]:
        repository, separator, tag = identifier.partition("@")
        if separator:
            return repository, tag
        return repository, None

    @staticmethod
    def _record_url(provider: str, identifier: str) -> str:
        if provider == "zenodo":
            record_id = (
                identifier.rsplit(".", 1)[-1] if identifier.startswith("10.") else identifier
            )
            return f"https://zenodo.org/api/records/{quote(record_id, safe='')}"
        if provider == "figshare":
            return f"https://api.figshare.com/v2/articles/{quote(identifier, safe='')}"
        if provider == "osf":
            return f"https://api.osf.io/v2/nodes/{quote(identifier, safe='')}/"
        repository, tag = RepositoryAdapter._github_parts(identifier)
        suffix = f"/releases/tags/{quote(tag, safe='')}" if tag else "/releases/latest"
        return f"https://api.github.com/repos/{repository}{suffix}"

    @staticmethod
    def _github_repo_url(identifier: str) -> str:
        repository, _ = RepositoryAdapter._github_parts(identifier)
        return f"https://api.github.com/repos/{repository}"

    def _zenodo_search_url(self, term: str, page: int) -> str:
        return "https://zenodo.org/api/records?" + urlencode(
            {"q": term, "size": self.config.page_size, "page": page}
        )

    @staticmethod
    def _license_parts(record: Mapping[str, Any]) -> tuple[str | None, str | None]:
        raw = record.get("license") or record.get("license_identifier")
        text: str | None = None
        if isinstance(raw, Mapping):
            identifier = raw.get("id") or raw.get("spdx_id") or raw.get("value") or raw.get("name")
            raw_text = raw.get("title") or raw.get("text") or raw.get("name")
            text = raw_text.strip() if isinstance(raw_text, str) and raw_text.strip() else None
        else:
            identifier = raw
        if not isinstance(identifier, str) or not identifier.strip():
            return None, text
        normalized = re.sub(r"[^A-Za-z0-9]+", "-", identifier.strip()).strip("-").upper()
        aliases = {
            "CC-BY-4-0": "CC-BY-4.0",
            "CC-BY-3-0": "CC-BY-3.0",
            "CC-BY-NC-4-0": "CC-BY-NC-4.0",
            "CC0-1-0": "CC0",
            "CC-0": "CC0",
        }
        return aliases.get(normalized, normalized), text or identifier.strip()

    @staticmethod
    def _record_mapping(provider: str, value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise AdapterError(f"{provider} response is not an object")
        if provider == "zenodo":
            metadata = value.get("metadata")
            if isinstance(metadata, Mapping):
                merged = dict(value)
                merged.update(metadata)
                return merged
        if provider == "osf":
            data = value.get("data")
            if isinstance(data, Mapping):
                attributes = data.get("attributes")
                if isinstance(attributes, Mapping):
                    merged = dict(attributes)
                    if isinstance(data.get("id"), str):
                        merged["id"] = data["id"]
                    relationships = data.get("relationships")
                    if isinstance(relationships, Mapping):
                        merged["relationships"] = relationships
                    return merged
        return value

    def _get_json(self, url: str) -> tuple[Any, str]:
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        try:
            payload = self.client.get_bytes(url)
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"{self.name} response is not valid JSON: {url}") from exc
        return value, hashlib.sha256(payload).hexdigest()

    def _candidate(
        self,
        provider: str,
        identifier: str,
        *,
        license_identifier: str | None,
        license_text: str | None,
    ) -> SourceCandidate:
        return SourceCandidate.from_mapping(
            {
                "source_id": f"repository:{provider}:{identifier}",
                "source_name": PROVIDER_NAMES[provider],
                "url": self._record_url(provider, identifier),
                "accession": identifier,
                "license_identifier": license_identifier,
                "license_text": license_text,
                "evidence_location": f"{PROVIDER_NAMES[provider]} public API",
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

    def _candidate_from_record(
        self,
        provider: str,
        identifier: str,
        record: Any,
    ) -> SourceCandidate:
        mapped = self._record_mapping(provider, record)
        license_identifier, license_text = self._license_parts(mapped)
        return self._candidate(
            provider,
            identifier,
            license_identifier=license_identifier,
            license_text=license_text,
        )

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Resolve one public release or bounded Zenodo search results."""
        provider, identifier = self._parse_query(query.text)
        if provider == "zenodo" and identifier.lower().startswith("search:"):
            return self._search_zenodo(identifier[7:].strip(), query.limit)
        value, _ = self._get_json(self._record_url(provider, identifier))
        candidate = self._candidate_from_record(provider, identifier, value)
        if provider == "github":
            repository_value, _ = self._get_json(self._github_repo_url(identifier))
            license_identifier, license_text = self._license_parts(
                repository_value if isinstance(repository_value, Mapping) else {}
            )
            candidate = self._candidate(
                provider,
                identifier,
                license_identifier=license_identifier,
                license_text=license_text,
            )
        return (candidate,)

    def _search_zenodo(self, term: str, limit: int) -> tuple[SourceCandidate, ...]:
        if not term:
            raise AdapterError("Zenodo search term cannot be empty")
        candidates: list[SourceCandidate] = []
        seen: set[str] = set()
        for page in range(1, self.config.max_pages + 1):
            value, _ = self._get_json(self._zenodo_search_url(term, page))
            if not isinstance(value, Mapping):
                raise AdapterError("Zenodo search response is not an object")
            hits = value.get("hits")
            raw_hits = hits.get("hits") if isinstance(hits, Mapping) else None
            if not isinstance(raw_hits, list):
                raise AdapterError("Zenodo search response has no hits")
            for item in raw_hits:
                if not isinstance(item, Mapping):
                    continue
                raw_id = item.get("id")
                if isinstance(raw_id, int):
                    identifier = str(raw_id)
                elif isinstance(raw_id, str) and raw_id.strip():
                    identifier = raw_id.strip()
                else:
                    continue
                if identifier in seen:
                    continue
                seen.add(identifier)
                candidates.append(self._candidate_from_record("zenodo", identifier, item))
                if len(candidates) >= limit:
                    return tuple(candidates)
            links = value.get("links")
            next_url = links.get("next") if isinstance(links, Mapping) else None
            if not isinstance(next_url, str) or not next_url:
                return tuple(candidates)
        raise AdapterError("Zenodo pagination exceeded max_pages")

    @staticmethod
    def _text(record: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, Mapping):
                nested = value.get("value") or value.get("title") or value.get("name")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
        return None

    @staticmethod
    def _date(record: Mapping[str, Any]) -> str | None:
        return RepositoryAdapter._text(
            record,
            "published_at",
            "publication_date",
            "date_published",
            "date_modified",
            "modified",
            "created",
            "created_at",
        )

    @staticmethod
    def _doi(record: Mapping[str, Any]) -> str | None:
        return RepositoryAdapter._text(record, "doi", "conceptdoi", "citation_doi")

    @staticmethod
    def _commit(record: Mapping[str, Any]) -> str | None:
        return RepositoryAdapter._text(
            record,
            "tag_name",
            "target_commitish",
            "commit",
            "commit_sha",
            "sha",
        )

    @staticmethod
    def _asset_sha256(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        digest = value.strip().lower()
        if digest.startswith("sha256:"):
            digest = digest[7:]
        return digest if re.fullmatch(r"[0-9a-f]{64}", digest) else None

    def _files_url(self, provider: str, record: Mapping[str, Any]) -> str | None:
        if provider != "osf":
            return None
        relationships = record.get("relationships")
        files = relationships.get("files") if isinstance(relationships, Mapping) else None
        links = files.get("links") if isinstance(files, Mapping) else None
        related = links.get("related") if isinstance(links, Mapping) else None
        href = related.get("href") if isinstance(related, Mapping) else None
        return href if isinstance(href, str) and href else None

    def _asset_records(self, provider: str, record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        if provider in {"zenodo", "figshare"}:
            raw = record.get("files")
        elif provider == "github":
            raw = record.get("assets")
        else:
            raw = record.get("data")
        return [item for item in raw if isinstance(item, Mapping)] if isinstance(raw, list) else []

    def _assets(
        self,
        candidate: SourceCandidate,
        provider: str,
        record: Mapping[str, Any],
    ) -> tuple[AssetDescriptor, ...]:
        result: list[AssetDescriptor] = []
        for index, item in enumerate(self._asset_records(provider, record)):
            raw_id = item.get("id") or item.get("key") or item.get("name") or index
            asset_id = f"{candidate.source_id}:asset:{raw_id}"
            if provider == "zenodo":
                url = (
                    item.get("links", {}).get("self")
                    if isinstance(item.get("links"), Mapping)
                    else None
                )
                url = item.get("download") or url
                asset_type = item.get("type") or "application/octet-stream"
                checksum = item.get("checksum")
            elif provider == "figshare":
                url = item.get("download_url")
                asset_type = item.get("mime_type") or "application/octet-stream"
                checksum = item.get("sha256")
            elif provider == "github":
                url = item.get("browser_download_url")
                asset_type = item.get("content_type") or "application/octet-stream"
                checksum = item.get("digest")
            else:
                url = (
                    item.get("links", {}).get("download")
                    if isinstance(item.get("links"), Mapping)
                    else None
                )
                asset_type = (
                    item.get("attributes", {}).get("contentType")
                    if isinstance(item.get("attributes"), Mapping)
                    else None
                )
                checksum = (
                    item.get("attributes", {}).get("checksum")
                    if isinstance(item.get("attributes"), Mapping)
                    else None
                )
            if not isinstance(url, str) or not url.strip():
                continue
            size = item.get("size")
            size_bytes = size if isinstance(size, int) and size >= 0 else None
            result.append(
                AssetDescriptor(
                    asset_id=asset_id,
                    source_id=candidate.source_id,
                    url=url,
                    asset_type=str(asset_type),
                    accession=str(raw_id),
                    sha256=self._asset_sha256(checksum),
                    size_bytes=size_bytes,
                    license=candidate.license_identifier,
                )
            )
        return tuple(result)

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return public release metadata only after policy admission."""
        self.require_admitted(candidate)
        provider, identifier = self._source_identifier(candidate)
        value, response_sha256 = self._get_json(self._record_url(provider, identifier))
        record = self._record_mapping(provider, value)
        repository_sha256: str | None = None
        repository_license: str | None = None
        if provider == "github":
            repository_value, repository_sha256 = self._get_json(self._github_repo_url(identifier))
            repo_record = repository_value if isinstance(repository_value, Mapping) else {}
            repository_license, _ = self._license_parts(repo_record)
        license_identifier, license_text = self._license_parts(
            {"license": repository_license} if repository_license else record
        )
        return {
            "provider": provider,
            "identifier": identifier,
            "title": self._text(record, "title", "name", "citation_title"),
            "doi": self._doi(record),
            "version": self._text(record, "version", "version_number", "tag_name"),
            "date": self._date(record),
            "commit": self._commit(record),
            "license": license_identifier or candidate.license_identifier,
            "license_text": license_text or candidate.license_text,
            "asset_count": len(self._asset_records(provider, record)),
            "request_url": self._record_url(provider, identifier),
            "response_sha256": response_sha256,
            "repository_response_sha256": repository_sha256,
            "evidence_location": f"{PROVIDER_NAMES[provider]} public API",
            "raw_record": dict(record),
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """List public release files without executing or downloading them."""
        self.require_admitted(candidate)
        provider, identifier = self._source_identifier(candidate)
        value, _ = self._get_json(self._record_url(provider, identifier))
        record = self._record_mapping(provider, value)
        files_url = self._files_url(provider, record)
        if files_url is not None:
            files_value, _ = self._get_json(files_url)
            record = files_value if isinstance(files_value, Mapping) else record
        return self._assets(candidate, provider, record)

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Download only a hash-verifiable admitted public asset."""
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        if asset.sha256 is None:
            raise AdapterError("asset has no verifiable SHA-256; retain pointer only")
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        path = self.client.download(asset.url, destination, expected_sha256=asset.sha256)
        return FetchResult(path=path, sha256=asset.sha256, size_bytes=path.stat().st_size)

    @staticmethod
    def _source_identifier(candidate: SourceCandidate) -> tuple[str, str]:
        parts = candidate.source_id.split(":", 2)
        if len(parts) != 3 or parts[0] != "repository":
            raise AdapterError("repository candidate source_id is malformed")
        return parts[1], parts[2]
