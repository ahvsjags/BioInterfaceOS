"""Conservatively resolve R3 source-native protein identifiers through UniProt.

Only a source identifier with one resolved human canonical accession enters the
candidate shared universe.  Protein groups resolving to multiple accessions,
non-human entries and unsupported identifiers remain explicitly unresolved.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


class R3UniProtMappingError(RuntimeError):
    """Raised when the R3 protein-identifier mapping is incomplete or unsafe."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise R3UniProtMappingError(f"{label} must be an object")
    return dict(value)


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R3UniProtMappingError(f"{label} must contain at least {minimum} items")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise R3UniProtMappingError(f"{label} must be a non-empty string")
    return value.strip()


def _checksum(value: Any, label: str) -> str:
    checksum = _string(value, label)
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise R3UniProtMappingError(f"{label} must be a lowercase SHA-256")
    return checksum


ACCESSION = re.compile(
    r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9][A-Z0-9]{3}[0-9]|"
    r"[A-NR-Z][0-9][A-Z0-9]{8})(?:-\d+)?$"
)
ENTRY_NAME = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,20}_HUMAN$")


@dataclass(frozen=True)
class R3UniProtMappingSummary:
    """Accounting for a conservatively resolved three-source protein universe."""

    queried_token_count: int
    resolved_identifier_count: int
    shared_canonical_protein_count: int
    shared_source_cell_count: int
    status: str
    receipt_path: Path


class R3UniProtMappingWorkflow:
    """Map source-native records without collapsing ambiguous protein groups."""

    AUDIT_ID = "bioif-r3-uniprot-human-mapping-v1.0.1"
    REGISTRY_RELATIVE = "docs/data/R3_T148_UNIPROT_MAPPING_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_3/uniprot_human_mapping/v1.0.1"
    REQUEST_RELATIVE = "uniprot_human_mapping/uniprot_request_manifest.csv"
    RESPONSE_RELATIVE = "uniprot_human_mapping/uniprot_api_response_batches"
    RESOLUTION_RELATIVE = "uniprot_human_mapping/source_identifier_resolution.csv"
    SHARED_RELATIVE = "uniprot_human_mapping/shared_canonical_source_cells.csv"
    STATUS = "CANDIDATE_SHARED_PROTEIN_UNIVERSE_PENDING_PROTOCOL_AMENDMENT"
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "uniprot_source",
        "source_maps",
        "minimum_shared_canonical_proteins",
        "scope",
    }
    REQUIRED_UNIPROT = {"api_locator", "license", "organism_id", "fields", "batch_size"}
    REQUIRED_SOURCE = {"source_id", "relative_path", "sha256", "identifier_column"}
    REQUIRED_SCOPE = {
        "mapping_policy",
        "admission_status",
        "model_status",
        "scientific_submission_ready",
    }

    def __init__(
        self,
        root: Path,
        mapping_root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.mapping_root = mapping_root.resolve(strict=False)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R3UniProtMappingError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R3UniProtMappingError(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R3UniProtMappingError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R3UniProtMappingError(f"{label} is missing or outside repository root")
        return path

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "R3 UniProt mapping registry")
        if set(registry) != self.REQUIRED_TOP_LEVEL or registry.get("schema_version") != 1:
            raise R3UniProtMappingError("R3 UniProt mapping registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise R3UniProtMappingError("R3 UniProt mapping registry identity is invalid")
        if (
            registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R3UniProtMappingError("R3 UniProt mapping evidence boundary is invalid")
        _string(registry.get("evaluated_at"), "R3 UniProt mapping evaluated_at")
        uniprot = _mapping(registry.get("uniprot_source"), "R3 UniProt source")
        if set(uniprot) != self.REQUIRED_UNIPROT or (
            not _string(uniprot.get("api_locator"), "R3 UniProt API locator").startswith("https://rest.uniprot.org/")
            or uniprot.get("license") != "CC-BY-4.0"
            or uniprot.get("organism_id") != 9606
            or uniprot.get("fields") != ["accession", "id", "gene_names", "xref_refseq"]
            or not isinstance(uniprot.get("batch_size"), int)
            or uniprot["batch_size"] < 10
            or uniprot["batch_size"] > 200
        ):
            raise R3UniProtMappingError("R3 UniProt source configuration is invalid")
        sources: list[dict[str, Any]] = []
        source_ids: set[str] = set()
        for value in _list(registry.get("source_maps"), "R3 source maps", minimum=3):
            source = _mapping(value, "R3 source map")
            if set(source) != self.REQUIRED_SOURCE:
                raise R3UniProtMappingError("R3 source map fields are invalid")
            source_id = _string(source.get("source_id"), "R3 source ID")
            if source_id in source_ids:
                raise R3UniProtMappingError("R3 source ID is duplicated")
            source_ids.add(source_id)
            path = self._root_file(_string(source.get("relative_path"), source_id), source_id)
            if _sha256(path) != _checksum(source.get("sha256"), source_id):
                raise R3UniProtMappingError(f"R3 source map checksum differs: {source_id}")
            identifier_column = _string(source.get("identifier_column"), source_id)
            with path.open("r", encoding="utf-8", newline="") as stream:
                header = next(csv.reader(stream), [])
            if identifier_column not in header:
                raise R3UniProtMappingError(f"R3 source identifier column missing: {source_id}")
            sources.append({**source, "path": path})
        if source_ids != {
            "PXD017052_SEER_BROAD",
            "PMC9633814_MSU_MULTICORE",
            "PMC7788026_OUHSC_GOLD",
        }:
            raise R3UniProtMappingError("R3 source-map laboratory roster is invalid")
        minimum = registry.get("minimum_shared_canonical_proteins")
        if not isinstance(minimum, int) or minimum < 100:
            raise R3UniProtMappingError("R3 shared-protein threshold is invalid")
        scope = _mapping(registry.get("scope"), "R3 UniProt scope")
        if set(scope) != self.REQUIRED_SCOPE or (
            scope.get("mapping_policy") != "UNIQUE_HUMAN_CANONICAL_ACCESSION_ONLY"
            or scope.get("admission_status") != self.STATUS
            or scope.get("model_status") != "NOT_FITTED"
            or scope.get("scientific_submission_ready") is not False
        ):
            raise R3UniProtMappingError("R3 UniProt mapping scope is invalid")
        return registry, sources

    @staticmethod
    def _tokens(identifier: str) -> list[tuple[str, str]]:
        tokens: list[tuple[str, str]] = []
        for raw_token in identifier.replace(";", " ").split():
            token = raw_token.strip()
            if ACCESSION.fullmatch(token):
                tokens.append(("accession", token.split("-", maxsplit=1)[0]))
            elif ENTRY_NAME.fullmatch(token):
                tokens.append(("id", token))
        return sorted(set(tokens))

    @staticmethod
    def _response_rows(payload: str) -> list[dict[str, str]]:
        return list(csv.DictReader(payload.splitlines(), delimiter="\t"))

    @staticmethod
    def _query_terms(tokens: list[tuple[str, str]]) -> str:
        return " OR ".join(f"{field}:{value}" for field, value in tokens)

    def _fetch_uniprot(
        self, tokens: list[tuple[str, str]], config: dict[str, Any]
    ) -> tuple[
        list[dict[str, str]],
        list[dict[str, str]],
        list[tuple[str, str]],
        dict[str, str],
    ]:
        api_rows: list[dict[str, str]] = []
        request_rows: list[dict[str, str]] = []
        response_payloads: list[tuple[str, str]] = []
        response_headers: dict[str, str] = {}
        for start in range(0, len(tokens), config["batch_size"]):
            batch = tokens[start : start + config["batch_size"]]
            query = f"({self._query_terms(batch)}) AND organism_id:{config['organism_id']}"
            parameters = {
                "query": query,
                "format": "tsv",
                "fields": ",".join(config["fields"]),
                "size": "500",
            }
            url = f"{config['api_locator']}?{urllib.parse.urlencode(parameters)}"
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = response.read().decode("utf-8")
                    response_headers = {
                        "x-uniprot-release": response.headers.get("x-uniprot-release", ""),
                        "x-uniprot-release-date": response.headers.get("x-uniprot-release-date", ""),
                    }
            except OSError as exc:
                raise R3UniProtMappingError("UniProt identifier query failed") from exc
            payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            rows = self._response_rows(payload)
            api_rows.extend(rows)
            batch_index = start // config["batch_size"] + 1
            response_file_name = f"batch-{batch_index:04d}.tsv"
            response_payloads.append((response_file_name, payload))
            request_rows.append(
                {
                    "batch_index": str(batch_index),
                    "query_token_count": str(len(batch)),
                    "response_row_count": str(len(rows)),
                    "request_url": url,
                    "response_file_name": response_file_name,
                    "response_sha256": payload_sha256,
                }
            )
        return api_rows, request_rows, response_payloads, response_headers

    @staticmethod
    def _token_matches(rows: list[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
        matches: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in rows:
            accession = row.get("Entry", "").strip()
            entry_name = row.get("Entry Name", "").strip()
            if not accession:
                continue
            matches[("accession", accession)].add(accession)
            if entry_name:
                matches[("id", entry_name)].add(accession)
        return matches

    @staticmethod
    def _source_identifiers(
        sources: list[dict[str, Any]],
    ) -> tuple[dict[str, set[str]], list[tuple[str, str]]]:
        identifiers: dict[str, set[str]] = {}
        all_tokens: set[tuple[str, str]] = set()
        for source in sources:
            with source["path"].open("r", encoding="utf-8", newline="") as stream:
                records = list(csv.DictReader(stream))
            source_identifiers = {
                _string(record.get(source["identifier_column"]), source["source_id"])
                for record in records
                if record.get(source["identifier_column"])
            }
            identifiers[source["source_id"]] = source_identifiers
            for identifier in source_identifiers:
                all_tokens.update(R3UniProtMappingWorkflow._tokens(identifier))
        return identifiers, sorted(all_tokens)

    def run(self, *, strict: bool = False) -> R3UniProtMappingSummary:
        if not strict:
            raise R3UniProtMappingError("R3 UniProt mapping requires --strict")
        if self.output_root.exists():
            raise R3UniProtMappingError("R3 UniProt mapping already executed")
        registry, sources = self._registry()
        uniprot = _mapping(registry["uniprot_source"], "R3 UniProt source")
        identifiers, tokens = self._source_identifiers(sources)
        if not tokens:
            raise R3UniProtMappingError("R3 UniProt mapping found no supported source tokens")
        api_rows, request_rows, response_payloads, response_headers = self._fetch_uniprot(tokens, uniprot)
        matches = self._token_matches(api_rows)
        resolutions: list[dict[str, str]] = []
        resolved_by_source: dict[str, dict[str, str]] = {}
        for source_id, source_identifiers in identifiers.items():
            source_resolution: dict[str, str] = {}
            for identifier in sorted(source_identifiers):
                candidates = self._tokens(identifier)
                accessions = sorted({accession for candidate in candidates for accession in matches[candidate]})
                if len(accessions) == 1:
                    status = "UNIQUE_HUMAN_CANONICAL_ACCESSION"
                    resolved = accessions[0]
                    source_resolution[identifier] = resolved
                elif not candidates:
                    status = "NO_SUPPORTED_UNIPROT_TOKEN"
                    resolved = ""
                elif not accessions:
                    status = "NO_HUMAN_UNIPROT_MATCH"
                    resolved = ""
                else:
                    status = "AMBIGUOUS_MULTI_ACCESSION_GROUP"
                    resolved = ""
                resolutions.append(
                    {
                        "source_id": source_id,
                        "source_identifier": identifier,
                        "candidate_tokens": ";".join(f"{kind}:{token}" for kind, token in candidates),
                        "resolved_canonical_accession": resolved,
                        "resolution_status": status,
                    }
                )
            resolved_by_source[source_id] = source_resolution
        canonical_sets = {
            source_id: set(source_resolution.values()) for source_id, source_resolution in resolved_by_source.items()
        }
        shared = set.intersection(*canonical_sets.values())
        if len(shared) < registry["minimum_shared_canonical_proteins"]:
            raise R3UniProtMappingError("R3 UniProt mapping has too few shared canonical proteins")
        shared_rows: list[dict[str, str]] = []
        for source in sources:
            resolution = resolved_by_source[source["source_id"]]
            with source["path"].open("r", encoding="utf-8", newline="") as stream:
                for record in csv.DictReader(stream):
                    identifier = record.get(source["identifier_column"], "")
                    canonical_accession = resolution.get(identifier)
                    if canonical_accession in shared:
                        shared_rows.append(
                            {
                                "source_id": source["source_id"],
                                "canonical_accession": canonical_accession,
                                "source_identifier": identifier,
                                "source_analysis_unit_id": record.get("analysis_unit_id", ""),
                                "source_asset_id": record.get("source_asset_id", ""),
                                "source_worksheet": record.get("source_worksheet", ""),
                                "source_row": record.get("source_row", ""),
                                "source_coordinate": record.get("source_cell", record.get("source_cell_range", "")),
                            }
                        )
        if not shared_rows:
            raise R3UniProtMappingError("R3 UniProt mapping produced no shared source-cell rows")
        request_path = self.mapping_root / self.REQUEST_RELATIVE
        response_root = self.mapping_root / self.RESPONSE_RELATIVE
        resolution_path = self.mapping_root / self.RESOLUTION_RELATIVE
        shared_path = self.mapping_root / self.SHARED_RELATIVE
        if any(path.exists() for path in (request_path, response_root, resolution_path, shared_path)):
            raise R3UniProtMappingError("R3 UniProt mapping output already exists")
        for path in (request_path, resolution_path, shared_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        response_root.mkdir(parents=True, exist_ok=False)
        for response_file_name, payload in response_payloads:
            (response_root / response_file_name).write_text(payload, encoding="utf-8", newline="")
        with request_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(request_rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(request_rows)
        with resolution_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(resolutions[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(resolutions)
        with shared_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(shared_rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(shared_rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "uniprot_source": {
                **uniprot,
                "response_headers": response_headers,
                "queried_token_count": len(tokens),
                "api_response_row_count": len(api_rows),
                "request_manifest_location": self.REQUEST_RELATIVE,
                "request_manifest_sha256": _sha256(request_path),
                "response_batch_directory": self.RESPONSE_RELATIVE,
                "response_batch_count": len(response_payloads),
            },
            "source_maps": [
                {
                    "source_id": source["source_id"],
                    "relative_path": source["relative_path"],
                    "sha256": source["sha256"],
                    "identifier_column": source["identifier_column"],
                    "source_identifier_count": len(identifiers[source["source_id"]]),
                    "unique_resolved_canonical_count": len(canonical_sets[source["source_id"]]),
                }
                for source in sources
            ],
            "resolution_manifest_location": self.RESOLUTION_RELATIVE,
            "resolution_manifest_sha256": _sha256(resolution_path),
            "resolved_identifier_count": sum(len(values) for values in resolved_by_source.values()),
            "shared_canonical_protein_count": len(shared),
            "shared_canonical_source_cells_location": self.SHARED_RELATIVE,
            "shared_canonical_source_cells_sha256": _sha256(shared_path),
            "shared_canonical_source_cell_count": len(shared_rows),
            "status": self.STATUS,
            "target_status": "CANDIDATE_COMMON_TARGET_NOT_FROZEN",
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": hashlib.sha256(_canonical(report)).hexdigest(),
            "queried_token_count": len(tokens),
            "resolved_identifier_count": report["resolved_identifier_count"],
            "shared_canonical_protein_count": len(shared),
            "shared_canonical_source_cell_count": len(shared_rows),
            "target_status": "CANDIDATE_COMMON_TARGET_NOT_FROZEN",
            "model_fitted": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        self._write(self.output_root / "uniprot_mapping_report.json", report)
        self._write(self.output_root / "uniprot_mapping_receipt.json", receipt)
        return R3UniProtMappingSummary(
            queried_token_count=len(tokens),
            resolved_identifier_count=report["resolved_identifier_count"],
            shared_canonical_protein_count=len(shared),
            shared_source_cell_count=len(shared_rows),
            status=self.STATUS,
            receipt_path=self.output_root / "uniprot_mapping_receipt.json",
        )

    def verify(self) -> R3UniProtMappingSummary:
        report_path = self.output_root / "uniprot_mapping_report.json"
        receipt_path = self.output_root / "uniprot_mapping_receipt.json"
        report = self._json(report_path, "R3 UniProt mapping report")
        receipt = self._json(receipt_path, "R3 UniProt mapping receipt")
        request_path = self.mapping_root / _string(
            _mapping(report.get("uniprot_source"), "R3 UniProt source").get("request_manifest_location"),
            "request manifest location",
        )
        required_files = (
            request_path,
            self.mapping_root / _string(report.get("resolution_manifest_location"), "resolution location"),
            self.mapping_root
            / _string(report.get("shared_canonical_source_cells_location"), "shared source-cell location"),
        )
        response_root = self.mapping_root / _string(
            _mapping(report.get("uniprot_source"), "R3 UniProt source").get("response_batch_directory"),
            "response batch directory",
        )
        response_manifest_valid = False
        if request_path.is_file() and response_root.is_dir():
            with request_path.open("r", encoding="utf-8", newline="") as stream:
                request_rows = list(csv.DictReader(stream))
            response_manifest_valid = bool(request_rows) and all(
                (response_root / row.get("response_file_name", "")).is_file()
                and _sha256(response_root / row["response_file_name"]) == row.get("response_sha256")
                for row in request_rows
            )
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or report.get("target_status") != "CANDIDATE_COMMON_TARGET_NOT_FROZEN"
            or report.get("shared_canonical_protein_count", 0) < 100
            or report.get("model_fitted") is not False
            or report.get("scientific_submission_ready") is not False
            or not all(path.is_file() for path in required_files)
            or not response_manifest_valid
        ):
            raise R3UniProtMappingError("R3 UniProt mapping receipt is invalid")
        return R3UniProtMappingSummary(
            queried_token_count=int(receipt["queried_token_count"]),
            resolved_identifier_count=int(receipt["resolved_identifier_count"]),
            shared_canonical_protein_count=int(receipt["shared_canonical_protein_count"]),
            shared_source_cell_count=int(receipt["shared_canonical_source_cell_count"]),
            status=self.STATUS,
            receipt_path=receipt_path,
        )
