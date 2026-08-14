"""Anonymous ChEMBL molecule adapter with versioned pagination."""

from __future__ import annotations

import hashlib
import json
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

CHEMBL_HOST = "www.ebi.ac.uk"
DATA_BASE = "https://www.ebi.ac.uk/chembl/api/data"
MOLECULE_ENDPOINT = f"{DATA_BASE}/molecule"
STATUS_ENDPOINT = f"{DATA_BASE}/status.json"


@dataclass(frozen=True)
class ChemblConfig:
    """Bounded ChEMBL query and pagination settings."""

    page_size: int = 20
    max_pages: int = 5
    rate_interval: float = 0.2

    def __post_init__(self) -> None:
        if not 0 < self.page_size <= 1000:
            raise AdapterError("page_size must be between 1 and 1000")
        if not 0 < self.max_pages <= 100:
            raise AdapterError("max_pages must be between 1 and 100")
        if self.rate_interval < 0.2:
            raise AdapterError("rate_interval must be at least 0.2 seconds")


class ChemblAdapter(SourceAdapter):
    """Use official ChEMBL molecule/status JSON endpoints."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: ChemblConfig | None = None,
    ) -> None:
        self.config = config or ChemblConfig()
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=self.config.rate_interval,
                allowed_hosts=(CHEMBL_HOST,),
            ),
        )
        super().__init__(root, policy, network)

    @property
    def name(self) -> str:
        return "chembl"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _get_json(self, url: str) -> tuple[Any, str]:
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        payload = self.client.get_bytes(url)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AdapterError(f"ChEMBL response is not valid JSON: {url}") from exc
        return value, hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _molecule_id(value: str) -> str:
        molecule_id = value.strip().upper()
        if not molecule_id.startswith("CHEMBL") or not molecule_id[6:].isdigit():
            raise AdapterError("ChEMBL query requires an identifier such as CHEMBL25")
        return molecule_id

    @staticmethod
    def _molecule_url(molecule_id: str) -> str:
        return f"{MOLECULE_ENDPOINT}/{molecule_id}.json"

    def _search_url(self, query: str, offset: int) -> str:
        params = (
            ("format", "json"),
            ("limit", str(self.config.page_size)),
            ("offset", str(offset)),
            ("pref_name__icontains", query),
        )
        return MOLECULE_ENDPOINT + "?" + urlencode(params)

    @staticmethod
    def _candidate(molecule_id: str) -> SourceCandidate:
        return SourceCandidate.from_mapping(
            {
                "source_id": f"chembl:{molecule_id}",
                "source_name": "ChEMBL",
                "url": ChemblAdapter._molecule_url(molecule_id),
                "accession": molecule_id,
                "license_identifier": "PUBLIC-DOMAIN",
                "license_text": "Public ChEMBL data service record",
                "evidence_location": "ChEMBL Web Services molecule endpoint",
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
    def _records(value: Any) -> list[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            raise AdapterError("ChEMBL molecule response is not an object")
        raw = value.get("molecules")
        if not isinstance(raw, list):
            raise AdapterError("ChEMBL search response has no molecules list")
        return [record for record in raw if isinstance(record, Mapping)]

    @staticmethod
    def _record(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise AdapterError("ChEMBL molecule response is not an object")
        nested = value.get("molecule")
        if isinstance(nested, Mapping):
            return nested
        return value

    def _status(self) -> tuple[Mapping[str, Any], str]:
        value, response_sha256 = self._get_json(STATUS_ENDPOINT)
        if not isinstance(value, Mapping):
            raise AdapterError("ChEMBL status response is not an object")
        return value, response_sha256

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Search by preferred name with bounded page_meta pagination."""
        text = query.text.strip()
        if text.upper().startswith("CHEMBL"):
            return (self._candidate(self._molecule_id(text)),)
        if not text:
            raise AdapterError("ChEMBL query cannot be empty")
        candidates: list[SourceCandidate] = []
        seen: set[str] = set()
        next_url = self._search_url(text, 0)
        for _ in range(self.config.max_pages):
            value, _ = self._get_json(next_url)
            for record in self._records(value):
                raw_id = record.get("molecule_chembl_id") or record.get("chembl_id")
                if not isinstance(raw_id, str):
                    continue
                molecule_id = self._molecule_id(raw_id)
                if molecule_id not in seen:
                    seen.add(molecule_id)
                    candidates.append(self._candidate(molecule_id))
                    if len(candidates) >= query.limit:
                        return tuple(candidates)
            page_meta = value.get("page_meta")
            next_value = page_meta.get("next") if isinstance(page_meta, Mapping) else None
            if not isinstance(next_value, str) or not next_value:
                return tuple(candidates)
            next_url = next_value
        raise AdapterError("ChEMBL pagination exceeded max_pages")

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return structure fields, parent relation, API version, and hashes."""
        self.require_admitted(candidate)
        if candidate.accession is None:
            raise AdapterError("ChEMBL candidate has no molecule ID")
        molecule_id = self._molecule_id(candidate.accession)
        value, response_sha256 = self._get_json(self._molecule_url(molecule_id))
        record = self._record(value)
        status, status_sha256 = self._status()
        structures = record.get("molecule_structures")
        structures_map = structures if isinstance(structures, Mapping) else {}
        properties = record.get("molecule_properties")
        properties_map = properties if isinstance(properties, Mapping) else {}
        return {
            "source_id": candidate.source_id,
            "molecule_chembl_id": molecule_id,
            "pref_name": record.get("pref_name"),
            "molecule_type": record.get("molecule_type"),
            "parent_chembl_id": record.get("parent_molecule_chembl_id") or record.get("parent_chembl_id"),
            "canonical_smiles": structures_map.get("canonical_smiles"),
            "isomeric_smiles": structures_map.get("isomeric_smiles"),
            "inchi": structures_map.get("standard_inchi"),
            "inchikey": structures_map.get("standard_inchi_key"),
            "molecular_weight": properties_map.get("full_mwt"),
            "alogp": properties_map.get("alogp"),
            "hbd": properties_map.get("hbd"),
            "hba": properties_map.get("hba"),
            "max_phase": record.get("max_phase"),
            "chembl_db_version": status.get("chembl_db_version"),
            "chembl_api_version": status.get("chembl_api_version"),
            "request_url": self._molecule_url(molecule_id),
            "response_sha256": response_sha256,
            "status_response_sha256": status_sha256,
            "evidence_location": "ChEMBL Web Services molecule and status endpoints",
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """ChEMBL molecule records expose metadata rather than binary assets."""
        self.require_admitted(candidate)
        return ()

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Reject binary fetch because this adapter exposes molecule metadata only."""
        self.require_admitted(candidate)
        raise AdapterError("ChEMBL adapter has no binary assets to fetch")
