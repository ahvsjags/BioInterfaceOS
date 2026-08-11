"""Anonymous GEO/SRA metadata and asset adapter."""

from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AssetDescriptor,
    FetchResult,
    SourceAdapter,
    SourceQuery,
)

GEO_ENDPOINT = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"
RUNINFO_ENDPOINT = "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo"
GEO_HOSTS = (
    "www.ncbi.nlm.nih.gov",
    "ftp.ncbi.nlm.nih.gov",
    "trace.ncbi.nlm.nih.gov",
    "sra-download.ncbi.nlm.nih.gov",
    "ftp.sra.ebi.ac.uk",
)


@dataclass(frozen=True)
class GeoConfig:
    """Bounded GEO/SRA metadata settings."""

    max_samples: int = 100
    max_runs: int = 50

    def __post_init__(self) -> None:
        if not 0 < self.max_samples <= 1000:
            raise AdapterError("max_samples must be between 1 and 1000")
        if not 0 < self.max_runs <= 500:
            raise AdapterError("max_runs must be between 1 and 500")


@dataclass(frozen=True)
class GeoRecord:
    """Parsed GEO SOFT metadata and stable cross-database relations."""

    accession: str
    values: Mapping[str, tuple[str, ...]]
    response_sha256: str
    request_url: str

    @property
    def title(self) -> str | None:
        return self.values.get("!Series_title", (None,))[0]

    @property
    def license_identifier(self) -> str | None:
        return _first_value(self.values, ("!Series_license", "!Sample_license"))

    @property
    def restricted(self) -> bool:
        fields = (
            "!Series_access",
            "!Series_data_use",
            "!Series_relation",
            "!Sample_access",
        )
        joined = " ".join(value.upper() for field in fields for value in self.values.get(field, ()))
        return any(term in joined for term in ("DBGAP", "CONTROLLED", "RESTRICTED", "PRIVATE"))

    @property
    def samples(self) -> tuple[str, ...]:
        return _accessions(
            self.values.get("!Series_sample_id", ()),
            prefixes=("GSM",),
        )

    @property
    def sra_accessions(self) -> tuple[str, ...]:
        return _accessions(
            tuple(
                value
                for field, values in self.values.items()
                if "SRA" in field.upper() or "SRA" in " ".join(values).upper()
                for value in values
            ),
            prefixes=("SRP", "SRR"),
        )

    @property
    def bioproject(self) -> str | None:
        return _first_accession(self.values, "PRJNA")


def _first_value(
    values: Mapping[str, tuple[str, ...]],
    fields: tuple[str, ...],
) -> str | None:
    for field in fields:
        for value in values.get(field, ()):
            if value.strip():
                return value.strip()
    return None


def _first_accession(values: Mapping[str, tuple[str, ...]], prefix: str) -> str | None:
    for field_values in values.values():
        for value in field_values:
            for token in value.replace(",", " ").replace(";", " ").replace(":", " ").split():
                token_upper = token.upper().strip("()[]")
                if token_upper.startswith(prefix) and token_upper[len(prefix) :].isdigit():
                    return token_upper
    return None


def _accessions(values: tuple[str, ...], prefixes: tuple[str, ...]) -> tuple[str, ...]:
    found: list[str] = []
    for value in values:
        for token in value.replace(",", " ").replace(";", " ").replace(":", " ").split():
            token_upper = token.upper().strip("()[]")
            if (
                any(
                    token_upper.startswith(prefix) and token_upper[len(prefix) :].isdigit()
                    for prefix in prefixes
                )
                and token_upper not in found
            ):
                found.append(token_upper)
    return tuple(found)


def _parse_soft(payload: bytes, request_url: str) -> GeoRecord:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdapterError("GEO SOFT response is not UTF-8") from exc
    values: defaultdict[str, list[str]] = defaultdict(list)
    for line in text.splitlines():
        if not line.startswith("!"):
            continue
        key, separator, raw_value = line.partition(" = ")
        if separator:
            values[key].append(raw_value.strip().strip('"'))
    normalized_values = {key: tuple(items) for key, items in values.items()}
    accession = _first_value(
        normalized_values,
        ("!Series_geo_accession", "!Sample_geo_accession"),
    )
    if accession is None:
        raise AdapterError("GEO SOFT response has no accession")
    return GeoRecord(
        accession=accession.upper(),
        values=normalized_values,
        response_sha256=hashlib.sha256(payload).hexdigest(),
        request_url=request_url,
    )


class GeoSraAdapter(SourceAdapter):
    """Use NCBI GEO metadata, official GEO FTP, and SRA RunInfo endpoints."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
        config: GeoConfig | None = None,
    ) -> None:
        network = client or AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                timeout=30.0,
                max_retries=3,
                backoff_factor=0.5,
                rate_interval=0.2,
                allowed_hosts=GEO_HOSTS,
            ),
        )
        super().__init__(root, policy, network)
        self.config = config or GeoConfig()

    @property
    def name(self) -> str:
        return "geo_sra"

    @property
    def version(self) -> str:
        return "1.0.0"

    @staticmethod
    def _normalize_accession(value: str) -> str:
        accession = value.strip().upper()
        prefixes = ("GSE", "GSM", "SRP", "SRR")
        if not any(
            accession.startswith(prefix) and accession[len(prefix) :].isdigit()
            for prefix in prefixes
        ):
            raise AdapterError("GEO/SRA query requires GSE, GSM, SRP, or SRR accession")
        return accession

    @staticmethod
    def _geo_url(accession: str) -> str:
        params = (
            ("acc", accession),
            ("form", "text"),
            ("targ", "self"),
            ("view", "full"),
        )
        return GEO_ENDPOINT + "?" + urlencode(params)

    @staticmethod
    def _runinfo_url(accession: str) -> str:
        return RUNINFO_ENDPOINT + "?" + urlencode((("acc", accession),))

    def _get_bytes(self, url: str) -> tuple[bytes, str]:
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        payload = self.client.get_bytes(url)
        return payload, hashlib.sha256(payload).hexdigest()

    def _geo_record(self, accession: str) -> GeoRecord:
        url = self._geo_url(accession)
        payload, _ = self._get_bytes(url)
        return _parse_soft(payload, url)

    def _runinfo_response(self, accession: str) -> tuple[tuple[dict[str, str], ...], str]:
        url = self._runinfo_url(accession)
        payload, response_sha256 = self._get_bytes(url)
        try:
            text = payload.decode("utf-8")
            rows = tuple(csv.DictReader(io.StringIO(text)))
        except (UnicodeDecodeError, csv.Error) as exc:
            raise AdapterError("SRA RunInfo response is invalid CSV") from exc
        if not rows:
            raise AdapterError("SRA RunInfo response has no rows")
        normalized = tuple(
            {str(key): str(value or "").strip() for key, value in row.items()} for row in rows
        )
        return normalized, response_sha256

    def _runinfo(self, accession: str) -> tuple[dict[str, str], ...]:
        rows, _ = self._runinfo_response(accession)
        return rows

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Resolve explicit GEO or SRA accessions without broad page scraping."""
        accession = self._normalize_accession(query.text.split()[0])
        if accession.startswith(("GSE", "GSM")):
            record = self._geo_record(accession)
            return (self._candidate(record),)
        rows = self._runinfo(accession)
        return (self._sra_candidate(accession, rows[0]),)

    def metadata(self, candidate: SourceCandidate) -> dict[str, Any]:
        """Return GEO relationships or SRA run metadata with response hash."""
        self.require_admitted(candidate)
        accession = self._candidate_accession(candidate)
        if accession.startswith(("GSE", "GSM")):
            record = self._geo_record(accession)
            return {
                "source_id": candidate.source_id,
                "accession": accession,
                "title": record.title,
                "organisms": list(record.values.get("!Series_organism", ())),
                "samples": list(record.samples[: self.config.max_samples]),
                "sra_accessions": list(record.sra_accessions[: self.config.max_runs]),
                "bioproject": record.bioproject,
                "license": record.license_identifier,
                "request_url": record.request_url,
                "response_sha256": record.response_sha256,
                "evidence_location": "NCBI GEO SOFT metadata",
            }
        rows, response_sha256 = self._runinfo_response(accession)
        row = rows[0]
        return {
            "source_id": candidate.source_id,
            "accession": accession,
            "study": row.get("SRAStudy") or row.get("Study"),
            "bioproject": row.get("BioProject"),
            "biosample": row.get("BioSample"),
            "organism": row.get("ScientificName"),
            "platform": row.get("Platform"),
            "release_date": row.get("ReleaseDate"),
            "visibility": row.get("Visibility"),
            "request_url": self._runinfo_url(accession),
            "response_sha256": response_sha256,
            "evidence_location": "NCBI SRA RunInfo metadata",
        }

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """List processed GEO files first, then linked SRA raw runs."""
        self.require_admitted(candidate)
        accession = self._candidate_accession(candidate)
        if accession.startswith(("GSE", "GSM")):
            record = self._geo_record(accession)
            assets = list(self._geo_assets(candidate, record))
            for sra_accession in record.sra_accessions[: self.config.max_runs]:
                rows = self._runinfo(sra_accession)
                assets.extend(self._sra_assets(candidate, rows))
            return tuple(assets)
        return self._sra_assets(candidate, self._runinfo(accession))

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Fetch an official GEO/SRA asset only with a verified SHA-256."""
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        if not asset.sha256:
            raise AdapterError("GEO/SRA fetch requires a manifest SHA-256")
        if self.client is None:
            raise AdapterError("anonymous network client is unavailable")
        path = self.client.download(
            asset.url,
            destination,
            expected_sha256=asset.sha256,
        )
        return FetchResult(path, asset.sha256, path.stat().st_size)

    @staticmethod
    def _candidate(record: GeoRecord) -> SourceCandidate:
        return SourceCandidate.from_mapping(
            {
                "source_id": f"geo:{record.accession}",
                "source_name": "NCBI GEO",
                "url": record.request_url,
                "accession": record.accession,
                "license_identifier": record.license_identifier,
                "license_text": record.license_identifier,
                "evidence_location": "NCBI GEO SOFT metadata",
                "registration_required": False,
                "login_required": record.restricted,
                "api_key_required": False,
                "application_required": False,
                "approval_required": record.restricted,
                "institution_required": False,
                "data_use_agreement_required": record.restricted,
                "paid_required": False,
            }
        )

    @staticmethod
    def _sra_candidate(accession: str, row: Mapping[str, str]) -> SourceCandidate:
        visibility = row.get("Visibility", "").upper()
        restricted = visibility not in {"PUBLIC", ""}
        return SourceCandidate.from_mapping(
            {
                "source_id": f"sra:{accession}",
                "source_name": "NCBI SRA",
                "url": GeoSraAdapter._runinfo_url(accession),
                "accession": accession,
                "license_identifier": "PUBLIC-DOMAIN" if not restricted else None,
                "license_text": "NCBI public SRA metadata" if not restricted else None,
                "evidence_location": "NCBI SRA RunInfo metadata",
                "registration_required": False,
                "login_required": restricted,
                "api_key_required": False,
                "application_required": False,
                "approval_required": restricted,
                "institution_required": False,
                "data_use_agreement_required": restricted,
                "paid_required": False,
            }
        )

    @staticmethod
    def _candidate_accession(candidate: SourceCandidate) -> str:
        if candidate.accession is None:
            raise AdapterError("candidate has no accession")
        return GeoSraAdapter._normalize_accession(candidate.accession)

    @staticmethod
    def _geo_assets(
        candidate: SourceCandidate,
        record: GeoRecord,
    ) -> tuple[AssetDescriptor, ...]:
        accession = record.accession
        urls = (
            (
                "SERIES_MATRIX",
                GeoSraAdapter._series_url(accession, "matrix", f"{accession}_series_matrix.txt.gz"),
                _first_value(record.values, ("!Series_matrix_sha256",)),
            ),
            (
                "SOFT",
                GeoSraAdapter._series_url(accession, "soft", f"{accession}_family.soft.gz"),
                _first_value(record.values, ("!Series_soft_sha256",)),
            ),
        )
        assets: list[AssetDescriptor] = []
        for asset_type, url, sha256 in urls:
            assets.append(GeoSraAdapter._asset(candidate, accession, asset_type, url, sha256))
        for value in record.values.get("!Series_supplementary_file", ()):
            filename = value.strip()
            url = (
                filename
                if filename.startswith(("http://", "https://"))
                else GeoSraAdapter._series_url(accession, "suppl", filename)
            )
            assets.append(GeoSraAdapter._asset(candidate, accession, "SUPPLEMENTARY", url, None))
        return tuple(assets)

    @staticmethod
    def _sra_assets(
        candidate: SourceCandidate,
        rows: tuple[dict[str, str], ...],
    ) -> tuple[AssetDescriptor, ...]:
        assets: list[AssetDescriptor] = []
        for row in rows:
            run = row.get("Run") or row.get("run")
            url = row.get("download_path") or row.get("DownloadPath")
            if not run or not url:
                continue
            checksum = row.get("download_path_sha256") or row.get("sha256")
            assets.append(
                GeoSraAdapter._asset(
                    candidate,
                    run,
                    "SRA_RAW",
                    GeoSraAdapter._public_url(url),
                    checksum,
                )
            )
        return tuple(assets)

    @staticmethod
    def _asset(
        candidate: SourceCandidate,
        accession: str,
        asset_type: str,
        url: str,
        sha256: str | None,
    ) -> AssetDescriptor:
        public_url = GeoSraAdapter._public_url(url)
        asset_id = hashlib.sha256(
            f"{candidate.source_id}|{asset_type}|{public_url}".encode()
        ).hexdigest()
        return AssetDescriptor(
            asset_id=asset_id,
            source_id=candidate.source_id,
            url=public_url,
            asset_type=asset_type,
            accession=accession,
            sha256=sha256.lower() if sha256 and len(sha256) == 64 else None,
            size_bytes=None,
            license=candidate.license_identifier,
        )

    @staticmethod
    def _public_url(url: str) -> str:
        parsed = urlsplit(url)
        if parsed.scheme == "ftp" and parsed.hostname in GEO_HOSTS:
            return urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, parsed.fragment))
        if parsed.scheme in {"http", "https"} and parsed.hostname in GEO_HOSTS:
            return url
        raise AdapterError("GEO/SRA URL is not an official allowlisted HTTP(S)/FTP link")

    @staticmethod
    def _series_url(accession: str, folder: str, filename: str) -> str:
        prefix = accession[:3]
        digits = accession[3:]
        range_dir = prefix + (digits[:-3] if len(digits) > 3 else "") + "nnn"
        return (
            f"https://ftp.ncbi.nlm.nih.gov/geo/series/{range_dir}/{accession}/{folder}/{filename}"
        )


if __name__ == "__main__":
    raise SystemExit("Use GeoSraAdapter through the source adapter contract.")
