"""Anonymous PubChem PUG-REST adapter with atomic response caching."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AssetDescriptor,
    FetchResult,
    SourceAdapter,
    SourceQuery,
)

PUG_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_HOST = "pubchem.ncbi.nlm.nih.gov"
PROPERTY_NAMES = (
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChI",
    "InChIKey",
    "MolecularFormula",
    "MolecularWeight",
)


@dataclass(frozen=True)
class PubChemConfig:
    """Bounded PUG-REST and cache settings."""

    rate_interval: float = 0.2
    max_cids: int = 20
    cache_relative: Path = Path("data/cache/pubchem")

    def __post_init__(self) -> None:
        if self.rate_interval < 0.2:
            raise AdapterError("rate_interval must be at least 0.2 seconds")
        if self.rate_interval > 3600:
            raise AdapterError("rate_interval is too large")
        if not 0 < self.max_cids <= 100:
            raise AdapterError("max_cids must be between 1 and 100")
        if self.cache_relative.is_absolute() or ".." in self.cache_relative.parts:
            raise AdapterError("cache_relative must remain inside the repository")


@dataclass(frozen=True)
class PubChemResolution:
    """Name resolution outcome that preserves ambiguity and no-hit state."""

    query: str
    cids: tuple[int, ...]
    ambiguous: bool
    unresolved: bool
    response_sha256: str
    request_url: str
    cached: bool


class PubChemAdapter(SourceAdapter):
    """Use the official PubChem PUG-REST name and property endpoints."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: PubChemConfig | None = None,
    ) -> None:
        self.config = config or PubChemConfig()
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=self.config.rate_interval,
                allowed_hosts=(PUBCHEM_HOST,),
            ),
        )
        super().__init__(root, policy, network)
        self.cache_root = (self.root / self.config.cache_relative).resolve(strict=False)
        if self.cache_root == self.root or self.root not in self.cache_root.parents:
            raise AdapterError("PubChem cache path escapes repository")

    @property
    def name(self) -> str:
        return "pubchem"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _cache_path(self, url: str) -> Path:
        return self.cache_root / f"{hashlib.sha256(url.encode()).hexdigest()}.json"

    def _cached_json(self, url: str) -> tuple[Any, str, bool]:
        cache_path = self._cache_path(url)
        if cache_path.exists():
            payload = cache_path.read_bytes()
            try:
                value = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise AdapterError(f"PubChem cache is invalid: {cache_path}") from exc
            return value, hashlib.sha256(payload).hexdigest(), True
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        payload = self.client.get_bytes(url)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"PubChem response is not valid JSON: {url}") from exc
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{cache_path.name}.",
            dir=cache_path.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, cache_path)
        finally:
            temporary.unlink(missing_ok=True)
        return value, hashlib.sha256(payload).hexdigest(), False

    @staticmethod
    def _cid(value: str) -> int:
        raw = value.strip().upper()
        if raw.startswith("CID:"):
            raw = raw[4:]
        if not raw.isdigit() or int(raw) <= 0:
            raise AdapterError("PubChem accession must be a positive CID")
        return int(raw)

    @staticmethod
    def _name_url(name: str) -> str:
        return f"{PUG_BASE}/compound/name/{quote(name, safe='')}/cids/JSON"

    @staticmethod
    def _property_url(cid: int) -> str:
        properties = ",".join(PROPERTY_NAMES)
        return f"{PUG_BASE}/compound/cid/{cid}/property/{properties}/JSON"

    @staticmethod
    def _parse_cids(value: Any) -> tuple[int, ...]:
        if not isinstance(value, dict):
            raise AdapterError("PubChem CID response is not an object")
        identifier_list = value.get("IdentifierList")
        if not isinstance(identifier_list, dict):
            raise AdapterError("PubChem CID response has no IdentifierList")
        raw_cids = identifier_list.get("CID", [])
        if not isinstance(raw_cids, list):
            raise AdapterError("PubChem CID response CID is not a list")
        cids: list[int] = []
        for raw in raw_cids:
            try:
                cid = int(raw)
            except (TypeError, ValueError) as exc:
                raise AdapterError("PubChem returned an invalid CID") from exc
            if cid > 0 and cid not in cids:
                cids.append(cid)
        return tuple(cids)

    @staticmethod
    def _candidate(cid: int, query: str | None = None) -> SourceCandidate:
        evidence = "PubChem PUG-REST CID/property response"
        if query:
            evidence = f"PubChem PUG-REST name resolution for {query}"
        return SourceCandidate.from_mapping(
            {
                "source_id": f"pubchem:CID:{cid}",
                "source_name": "PubChem",
                "url": PubChemAdapter._property_url(cid),
                "accession": str(cid),
                "license_identifier": "PUBLIC-DOMAIN",
                "license_text": "Public PubChem PUG-REST record",
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

    def resolve_name(self, name: str) -> PubChemResolution:
        """Resolve a name while preserving zero, one, or many CIDs."""
        query = name.strip()
        if not query:
            raise AdapterError("PubChem name query cannot be empty")
        url = self._name_url(query)
        value, response_sha256, cached = self._cached_json(url)
        cids = self._parse_cids(value)
        bounded = cids[: self.config.max_cids]
        return PubChemResolution(
            query=query,
            cids=bounded,
            ambiguous=len(bounded) > 1,
            unresolved=not bounded,
            response_sha256=response_sha256,
            request_url=url,
            cached=cached,
        )

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Resolve a CID directly or return all bounded name-resolution candidates."""
        text = query.text.strip()
        if text.upper().startswith("CID:") or text.isdigit():
            return (self._candidate(self._cid(text)),)
        resolution = self.resolve_name(text)
        return tuple(self._candidate(cid, text) for cid in resolution.cids[: query.limit])

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return selected structure identifiers and descriptors with provenance."""
        self.require_admitted(candidate)
        if candidate.accession is None:
            raise AdapterError("PubChem candidate has no CID")
        cid = self._cid(candidate.accession)
        value, response_sha256, cached = self._cached_json(self._property_url(cid))
        if not isinstance(value, dict):
            raise AdapterError("PubChem property response is not an object")
        table = value.get("PropertyTable")
        properties: Any = table.get("Properties") if isinstance(table, dict) else None
        if not isinstance(properties, list) or not properties:
            raise AdapterError("PubChem property response has no properties")
        record = properties[0]
        if not isinstance(record, dict):
            raise AdapterError("PubChem property record is not an object")
        return {
            "source_id": candidate.source_id,
            "cid": record.get("CID", cid),
            "canonical_smiles": record.get("ConnectivitySMILES") or record.get("CanonicalSMILES"),
            "isomeric_smiles": record.get("SMILES") or record.get("IsomericSMILES"),
            "inchi": record.get("InChI"),
            "inchikey": record.get("InChIKey"),
            "molecular_formula": record.get("MolecularFormula"),
            "molecular_weight": record.get("MolecularWeight"),
            "request_url": self._property_url(cid),
            "response_sha256": response_sha256,
            "cached": cached,
            "evidence_location": "PubChem PUG-REST property table",
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """Compounds are metadata records; no binary asset is promoted here."""
        self.require_admitted(candidate)
        return ()

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Reject binary fetch because this adapter exposes structure metadata only."""
        self.require_admitted(candidate)
        raise AdapterError("PubChem adapter has no binary assets to fetch")
