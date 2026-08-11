"""Versioned anonymous adapters for public biomedical ontology records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
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

HOSTS = (
    "rest.uniprot.org",
    "www.ebi.ac.uk",
    "reactome.org",
    "api.cellosaurus.org",
)
SOURCE_NAMES = {
    "uniprot": "UniProtKB",
    "go": "Gene Ontology",
    "reactome": "Reactome",
    "cellosaurus": "Cellosaurus",
}
LICENSE_IDENTIFIER = "CC-BY-4.0"


@dataclass(frozen=True)
class OntologyConfig:
    """Bounded ontology search settings."""

    max_results: int = 20

    def __post_init__(self) -> None:
        if not 0 < self.max_results <= 100:
            raise AdapterError("max_results must be between 1 and 100")


class OntologyAdapter(SourceAdapter):
    """Resolve stable identifiers through official public ontology endpoints."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: OntologyConfig | None = None,
    ) -> None:
        self.config = config or OntologyConfig()
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=0.2,
                allowed_hosts=HOSTS,
            ),
        )
        super().__init__(root, policy, network)

    @property
    def name(self) -> str:
        return "ontology"

    @property
    def version(self) -> str:
        return "1.0.0"

    @staticmethod
    def _parse_query(text: str) -> tuple[str, str]:
        stripped = text.strip()
        if ":" not in stripped:
            raise AdapterError("ontology query must be source:identifier")
        source, identifier = stripped.split(":", 1)
        source = source.lower().strip()
        identifier = identifier.strip()
        if source not in SOURCE_NAMES or not identifier:
            raise AdapterError("unknown ontology source or empty identifier")
        return source, identifier

    @staticmethod
    def _candidate(source: str, identifier: str) -> SourceCandidate:
        return SourceCandidate.from_mapping(
            {
                "source_id": f"ontology:{source}:{identifier}",
                "source_name": SOURCE_NAMES[source],
                "url": OntologyAdapter._record_url(source, identifier),
                "accession": identifier,
                "license_identifier": LICENSE_IDENTIFIER,
                "license_text": "Public ontology record under configured CC-BY-4.0 signal",
                "evidence_location": f"{SOURCE_NAMES[source]} official API",
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

    @staticmethod
    def _record_url(source: str, identifier: str) -> str:
        if source == "uniprot":
            return f"https://rest.uniprot.org/uniprotkb/{quote(identifier, safe='')}.json"
        if source == "go":
            return "https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/" + quote(
                identifier, safe=""
            )
        if source == "reactome":
            return f"https://reactome.org/ContentService/data/query/{quote(identifier, safe='')}"
        return (
            "https://api.cellosaurus.org/cell-line/" + quote(identifier, safe="") + "?format=json"
        )

    @staticmethod
    def _search_url(source: str, label: str) -> str:
        if source == "cellosaurus":
            params = (("fields", "id,ac"), ("format", "json"), ("q", label))
            return "https://api.cellosaurus.org/search/cell-line?" + urlencode(params)
        if source == "go":
            return "https://www.ebi.ac.uk/QuickGO/services/ontology/go/search?" + urlencode(
                (("query", label),)
            )
        raise AdapterError(f"label search is not supported for {source}")

    def _get_json(self, url: str) -> tuple[Any, str]:
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        payload = self.client.get_bytes(url)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"ontology response is not valid JSON: {url}") from exc
        return value, hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _result_list(value: Any) -> list[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return []
        for key in ("results", "cell-lines", "terms"):
            raw = value.get(key)
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, Mapping)]
        return []

    def resolve_label(self, source: str, label: str) -> tuple[SourceCandidate, ...]:
        """Return all bounded label matches without collapsing ambiguity."""
        source_name = source.lower().strip()
        if source_name not in {"cellosaurus", "go"}:
            raise AdapterError("label search supports only cellosaurus and go")
        query = label.strip()
        if not query:
            raise AdapterError("ontology label cannot be empty")
        value, _ = self._get_json(self._search_url(source_name, query))
        candidates: list[SourceCandidate] = []
        seen: set[str] = set()
        for record in self._result_list(value)[: self.config.max_results]:
            identifier = record.get("ac") or record.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                continue
            candidate = self._candidate(source_name, identifier.strip())
            if candidate.source_id not in seen:
                candidates.append(candidate)
                seen.add(candidate.source_id)
        return tuple(candidates)

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Resolve source:identifier or source:name:label queries."""
        text = query.text.strip()
        if ":name:" in text.lower():
            source, label = text.split(":name:", 1)
            return self.resolve_label(source, label)[: query.limit]
        source, identifier = self._parse_query(text)
        return (self._candidate(source, identifier),)

    @staticmethod
    def _record(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise AdapterError("ontology record is not an object")
        nested = value.get("cell-line")
        if isinstance(nested, Mapping):
            return cast(Mapping[str, Any], nested)
        results = OntologyAdapter._result_list(value)
        if results:
            return results[0]
        if any(key in value for key in ("results", "cell-lines", "terms")):
            raise AdapterError("ontology record not found")
        return value

    @staticmethod
    def _text(record: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _names(value: Any) -> list[str]:
        if isinstance(value, list):
            names: list[str] = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    names.append(item.strip())
                elif isinstance(item, Mapping):
                    name = OntologyAdapter._text(item, "name", "displayName", "scientificName")
                    if name:
                        names.append(name)
            return names
        text = value.strip() if isinstance(value, str) else ""
        return [text] if text else []

    @staticmethod
    def _obsolete(record: Mapping[str, Any]) -> bool:
        raw = record.get("isObsolete") or record.get("obsolete") or record.get("status")
        if isinstance(raw, bool):
            return raw
        return isinstance(raw, str) and raw.strip().upper() in {"TRUE", "OBSOLETE", "DEPRECATED"}

    @staticmethod
    def _replaced_by(record: Mapping[str, Any]) -> list[str]:
        raw = record.get("replacedBy") or record.get("replaced_by")
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            values: list[str] = []
            for item in raw:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, Mapping):
                    identifier = item.get("id") or item.get("identifier")
                    if isinstance(identifier, str):
                        values.append(identifier)
            return values
        return []

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return normalized mapping fields and source release provenance."""
        self.require_admitted(candidate)
        source, identifier = self._source_identifier(candidate)
        value, response_sha256 = self._get_json(self._record_url(source, identifier))
        record = self._record(value)
        return {
            "source": source,
            "identifier": identifier,
            "label": self._text(
                record,
                "recommendedName",
                "name",
                "displayName",
                "id",
                "prefLabel",
            ),
            "organism": self._names(
                record.get("organism") or record.get("organisms") or record.get("species")
            ),
            "obsolete": self._obsolete(record),
            "replaced_by": self._replaced_by(record),
            "version": self._text(
                record,
                "release",
                "releaseVersion",
                "version",
                "entryVersion",
            ),
            "date": self._text(
                record,
                "releaseDate",
                "timestamp",
                "modified",
                "date",
            ),
            "license": self._text(record, "license") or candidate.license_identifier,
            "response_sha256": response_sha256,
            "request_url": self._record_url(source, identifier),
            "evidence_location": f"{SOURCE_NAMES[source]} official API",
            "raw_record": dict(record),
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """Ontology mappings expose metadata only, not binary assets."""
        self.require_admitted(candidate)
        return ()

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Reject binary fetch because ontology adapters expose mappings only."""
        self.require_admitted(candidate)
        raise AdapterError("ontology adapter has no binary assets to fetch")

    @staticmethod
    def _source_identifier(candidate: SourceCandidate) -> tuple[str, str]:
        parts = candidate.source_id.split(":", 2)
        if len(parts) != 3:
            raise AdapterError("ontology candidate source_id is malformed")
        return parts[1], parts[2]
