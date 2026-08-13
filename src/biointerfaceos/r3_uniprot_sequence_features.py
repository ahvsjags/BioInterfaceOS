"""Retrieve and freeze sequence-derived features for the R3 common proteins."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R3UniProtSequenceFeaturesError(RuntimeError):
    """Raised when source-release sequence features are incomplete or unsafe."""


AA_ORDER = "ACDEFGHIKLMNPQRSTVWY"
AA_MASS = {
    "A": 71.0788, "C": 103.1388, "D": 115.0886, "E": 129.1155, "F": 147.1766,
    "G": 57.0519, "H": 137.1411, "I": 113.1594, "K": 128.1741, "L": 113.1594,
    "M": 131.1926, "N": 114.1038, "P": 97.1167, "Q": 128.1307, "R": 156.1875,
    "S": 87.0782, "T": 101.1051, "V": 99.1326, "W": 186.2132, "Y": 163.1760,
}
HYDROPATHY = {
    "A": 1.8, "C": 2.5, "D": -3.5, "E": -3.5, "F": 2.8, "G": -0.4, "H": -3.2,
    "I": 4.5, "K": -3.9, "L": 3.8, "M": 1.9, "N": -3.5, "P": -1.6, "Q": -3.5,
    "R": -4.5, "S": -0.8, "T": -0.7, "V": 4.2, "W": -0.9, "Y": -1.3,
}


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R3UniProtSequenceFeaturesError(f"{label} must contain at least {minimum} items")
    return value


@dataclass(frozen=True)
class R3UniProtSequenceFeaturesSummary:
    """Accounting for a release-fixed sequence feature table."""

    canonical_protein_count: int
    descriptor_count: int
    response_batch_count: int
    status: str
    receipt_path: Path


class R3UniProtSequenceFeaturesWorkflow:
    """Generate identity-free, deterministic descriptors from UniProt sequences."""

    AUDIT_ID = "bioif-r3-uniprot-sequence-features-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R3_T150_UNIPROT_SEQUENCE_FEATURE_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_3/uniprot_sequence_features/v1.0.0"
    REQUEST_RELATIVE = "uniprot_sequence_features/request_manifest.csv"
    RESPONSE_RELATIVE = "uniprot_sequence_features/fasta_response_batches"
    FEATURES_RELATIVE = "uniprot_sequence_features/R3_uniprot_sequence_features.csv"
    STATUS = "R3_SEQUENCE_FEATURES_READY_FOR_PROTOCOL_FREEZE"
    REQUIRED_TOP_LEVEL = {
        "schema_version", "audit_id", "evaluated_at", "evidence_class", "allowed_claim_level",
        "common_target_receipt", "common_target_ledger", "uniprot_source", "feature_definition", "scope",
    }
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    REQUIRED_UNIPROT = {"api_locator", "license", "batch_size"}
    REQUIRED_FEATURES = {"feature_set_id", "feature_names", "unknown_residue_policy"}
    REQUIRED_SCOPE = {"status", "prohibited_features", "model_status", "scientific_submission_ready"}

    def __init__(
        self,
        root: Path,
        feature_root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.feature_root = feature_root.resolve(strict=False)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R3UniProtSequenceFeaturesError(f"cannot parse {label}") from exc
        try:
            return _mapping(value, label)
        except Exception as exc:
            raise R3UniProtSequenceFeaturesError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R3UniProtSequenceFeaturesError(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R3UniProtSequenceFeaturesError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R3UniProtSequenceFeaturesError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        item = _mapping(value, label)
        if set(item) != self.REQUIRED_REFERENCE:
            raise R3UniProtSequenceFeaturesError(f"{label} fields are invalid")
        path = self._root_file(_string(item.get("relative_path"), label), label)
        if _sha256(path) != _checksum(item.get("sha256"), label):
            raise R3UniProtSequenceFeaturesError(f"{label} checksum differs")
        return path

    @staticmethod
    def _feature_names() -> list[str]:
        return [
            "sequence_length", "estimated_molecular_mass_da", "hydrophobic_fraction",
            "aromatic_fraction", "acidic_fraction", "basic_fraction", "cysteine_fraction",
            "proline_fraction", "mean_kyte_doolittle",
        ] + [f"aa_fraction_{residue}" for residue in AA_ORDER]

    def _registry(self) -> tuple[dict[str, Any], list[str]]:
        registry = self._json(self.registry_path, "R3 sequence-feature registry")
        if set(registry) != self.REQUIRED_TOP_LEVEL or registry.get("schema_version") != 1:
            raise R3UniProtSequenceFeaturesError("R3 sequence-feature registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise R3UniProtSequenceFeaturesError("R3 sequence-feature registry identity is invalid")
        if (
            registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R3UniProtSequenceFeaturesError("R3 sequence-feature evidence boundary is invalid")
        _string(registry.get("evaluated_at"), "R3 sequence-feature evaluated_at")
        receipt_path = self._reference(registry.get("common_target_receipt"), "R3 common target receipt")
        receipt = self._json(receipt_path, "R3 common target receipt")
        if (
            receipt.get("audit_id") != "bioif-r3-common-rank-target-v1.0.0"
            or receipt.get("status") != "ADMITTED_COMMON_RANK_TARGET_PROTOCOL_AMENDMENT_REQUIRED"
            or receipt.get("target_status") != "NOT_FROZEN_PROTOCOL_AMENDMENT_REQUIRED"
            or receipt.get("model_fitted") is not False
        ):
            raise R3UniProtSequenceFeaturesError("R3 common target receipt boundary is invalid")
        ledger_path = self._reference(registry.get("common_target_ledger"), "R3 common target ledger")
        with ledger_path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        required = {"canonical_accession", "rank_target_eligible", "common_rank_target_member"}
        if not rows or not required.issubset(rows[0]):
            raise R3UniProtSequenceFeaturesError("R3 common target ledger schema is invalid")
        accessions = sorted(
            {
                row["canonical_accession"]
                for row in rows
                if row["rank_target_eligible"] == "true"
                and row["common_rank_target_member"] == "true"
            }
        )
        if len(accessions) != receipt.get("rank_eligible_shared_canonical_protein_count"):
            raise R3UniProtSequenceFeaturesError("R3 common target accession count is invalid")
        uniprot = _mapping(registry.get("uniprot_source"), "R3 UniProt sequence source")
        if set(uniprot) != self.REQUIRED_UNIPROT or (
            not _string(uniprot.get("api_locator"), "R3 UniProt sequence API").startswith("https://rest.uniprot.org/")
            or uniprot.get("license") != "CC-BY-4.0"
            or not isinstance(uniprot.get("batch_size"), int)
            or uniprot["batch_size"] < 10
            or uniprot["batch_size"] > 100
        ):
            raise R3UniProtSequenceFeaturesError("R3 UniProt sequence source is invalid")
        features = _mapping(registry.get("feature_definition"), "R3 feature definition")
        if set(features) != self.REQUIRED_FEATURES or (
            features.get("feature_set_id") != "R3_UNIPROT_SEQUENCE_COMPOSITION_PHYSICOCHEMICAL_V1"
            or features.get("feature_names") != self._feature_names()
            or features.get("unknown_residue_policy") != "FAIL_CLOSED"
        ):
            raise R3UniProtSequenceFeaturesError("R3 feature definition is invalid")
        scope = _mapping(registry.get("scope"), "R3 feature scope")
        if set(scope) != self.REQUIRED_SCOPE or (
            scope.get("status") != self.STATUS
            or scope.get("model_status") != "NOT_FITTED"
            or scope.get("scientific_submission_ready") is not False
        ):
            raise R3UniProtSequenceFeaturesError("R3 feature scope is invalid")
        prohibited = _list(scope.get("prohibited_features"), "R3 prohibited features", minimum=6)
        if any(not isinstance(item, str) or not item.strip() for item in prohibited):
            raise R3UniProtSequenceFeaturesError("R3 prohibited feature list is invalid")
        return registry, accessions

    @staticmethod
    def _parse_fasta(payload: str) -> dict[str, str]:
        sequences: dict[str, str] = {}
        accession = ""
        fragments: list[str] = []
        for line in payload.splitlines():
            if not line:
                continue
            if line.startswith(">"):
                if accession:
                    sequences[accession] = "".join(fragments)
                fields = line[1:].split("|", maxsplit=2)
                if len(fields) < 2 or not fields[1]:
                    raise R3UniProtSequenceFeaturesError("UniProt FASTA header is invalid")
                accession = fields[1]
                fragments = []
            else:
                fragments.append(line.strip())
        if accession:
            sequences[accession] = "".join(fragments)
        if not sequences:
            raise R3UniProtSequenceFeaturesError("UniProt FASTA response is empty")
        return sequences

    def _fetch(self, accessions: list[str], config: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]], list[tuple[str, str]], dict[str, str]]:
        sequences: dict[str, str] = {}
        manifest: list[dict[str, str]] = []
        payloads: list[tuple[str, str]] = []
        release_headers: dict[str, str] | None = None
        for start in range(0, len(accessions), config["batch_size"]):
            batch = accessions[start : start + config["batch_size"]]
            query = " OR ".join(f"accession:{accession}" for accession in batch)
            parameters = {"query": f"({query})", "format": "fasta"}
            url = f"{config['api_locator']}?{urllib.parse.urlencode(parameters)}"
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    payload = response.read().decode("utf-8")
                    current_headers = {
                        "x-uniprot-release": response.headers.get("x-uniprot-release", ""),
                        "x-uniprot-release-date": response.headers.get("x-uniprot-release-date", ""),
                    }
            except OSError as exc:
                raise R3UniProtSequenceFeaturesError("UniProt FASTA query failed") from exc
            if release_headers is None:
                release_headers = current_headers
            elif release_headers != current_headers:
                raise R3UniProtSequenceFeaturesError("UniProt release changed during FASTA retrieval")
            parsed = self._parse_fasta(payload)
            duplicate = set(parsed).intersection(sequences)
            if duplicate:
                raise R3UniProtSequenceFeaturesError("UniProt FASTA response repeats an accession")
            sequences.update(parsed)
            index = start // config["batch_size"] + 1
            file_name = f"batch-{index:04d}.fasta"
            payloads.append((file_name, payload))
            manifest.append(
                {
                    "batch_index": str(index),
                    "request_accession_count": str(len(batch)),
                    "response_accession_count": str(len(parsed)),
                    "request_url": url,
                    "response_file_name": file_name,
                    "response_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                }
            )
        if set(sequences) != set(accessions):
            raise R3UniProtSequenceFeaturesError("UniProt FASTA accession coverage is incomplete")
        return sequences, manifest, payloads, release_headers or {}

    @staticmethod
    def _descriptors(accession: str, sequence: str) -> dict[str, str]:
        if not sequence or any(residue not in AA_ORDER for residue in sequence):
            raise R3UniProtSequenceFeaturesError("UniProt sequence contains an unsupported residue")
        length = len(sequence)
        counts = {residue: sequence.count(residue) for residue in AA_ORDER}
        return {
            "canonical_accession": accession,
            "sequence_length": str(length),
            "estimated_molecular_mass_da": format(sum(AA_MASS[residue] for residue in sequence) + 18.0153, ".17g"),
            "hydrophobic_fraction": format(sum(counts[item] for item in "AVILMFWYC") / length, ".17g"),
            "aromatic_fraction": format(sum(counts[item] for item in "FWY") / length, ".17g"),
            "acidic_fraction": format(sum(counts[item] for item in "DE") / length, ".17g"),
            "basic_fraction": format(sum(counts[item] for item in "KRH") / length, ".17g"),
            "cysteine_fraction": format(counts["C"] / length, ".17g"),
            "proline_fraction": format(counts["P"] / length, ".17g"),
            "mean_kyte_doolittle": format(sum(HYDROPATHY[residue] for residue in sequence) / length, ".17g"),
            **{f"aa_fraction_{residue}": format(counts[residue] / length, ".17g") for residue in AA_ORDER},
        }

    def run(self, *, strict: bool = False) -> R3UniProtSequenceFeaturesSummary:
        if not strict:
            raise R3UniProtSequenceFeaturesError("R3 UniProt sequence feature build requires --strict")
        if self.output_root.exists():
            raise R3UniProtSequenceFeaturesError("R3 UniProt sequence features already executed")
        registry, accessions = self._registry()
        config = _mapping(registry["uniprot_source"], "R3 UniProt sequence source")
        sequences, manifest, payloads, release_headers = self._fetch(accessions, config)
        request_path = self.feature_root / self.REQUEST_RELATIVE
        response_root = self.feature_root / self.RESPONSE_RELATIVE
        features_path = self.feature_root / self.FEATURES_RELATIVE
        if any(path.exists() for path in (request_path, response_root, features_path)):
            raise R3UniProtSequenceFeaturesError("R3 UniProt sequence-feature output already exists")
        request_path.parent.mkdir(parents=True, exist_ok=True)
        response_root.mkdir(parents=True, exist_ok=False)
        for file_name, payload in payloads:
            (response_root / file_name).write_text(payload, encoding="utf-8", newline="")
        rows = [self._descriptors(accession, sequences[accession]) for accession in accessions]
        with request_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(manifest[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(manifest)
        with features_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "uniprot_source": {
                **config,
                "release_headers": release_headers,
                "request_manifest_location": self.REQUEST_RELATIVE,
                "request_manifest_sha256": _sha256(request_path),
                "response_batch_directory": self.RESPONSE_RELATIVE,
                "response_batch_count": len(payloads),
            },
            "feature_definition": registry["feature_definition"],
            "canonical_protein_count": len(accessions),
            "descriptor_count": len(self._feature_names()),
            "feature_table": {"location": self.FEATURES_RELATIVE, "sha256": _sha256(features_path)},
            "status": self.STATUS,
            "model_fitted": False,
            "scientific_submission_ready": False,
        }
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": hashlib.sha256(_canonical(report)).hexdigest(),
            "canonical_protein_count": len(accessions),
            "descriptor_count": len(self._feature_names()),
            "response_batch_count": len(payloads),
            "model_fitted": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        self._write(self.output_root / "uniprot_sequence_features_report.json", report)
        self._write(self.output_root / "uniprot_sequence_features_receipt.json", receipt)
        return R3UniProtSequenceFeaturesSummary(
            canonical_protein_count=len(accessions),
            descriptor_count=len(self._feature_names()),
            response_batch_count=len(payloads),
            status=self.STATUS,
            receipt_path=self.output_root / "uniprot_sequence_features_receipt.json",
        )

    def verify(self) -> R3UniProtSequenceFeaturesSummary:
        report_path = self.output_root / "uniprot_sequence_features_report.json"
        receipt_path = self.output_root / "uniprot_sequence_features_receipt.json"
        report = self._json(report_path, "R3 UniProt sequence-feature report")
        receipt = self._json(receipt_path, "R3 UniProt sequence-feature receipt")
        source = _mapping(report.get("uniprot_source"), "R3 UniProt sequence source")
        request_path = self.feature_root / _string(source.get("request_manifest_location"), "request manifest")
        response_root = self.feature_root / _string(source.get("response_batch_directory"), "response directory")
        features = _mapping(report.get("feature_table"), "R3 UniProt feature table")
        features_path = self.feature_root / _string(features.get("location"), "feature table location")
        response_valid = False
        if request_path.is_file() and response_root.is_dir():
            with request_path.open("r", encoding="utf-8", newline="") as stream:
                requests = list(csv.DictReader(stream))
            response_valid = bool(requests) and all(
                (response_root / row.get("response_file_name", "")).is_file()
                and _sha256(response_root / row["response_file_name"]) == row.get("response_sha256")
                for row in requests
            )
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or report.get("model_fitted") is not False
            or report.get("scientific_submission_ready") is not False
            or not features_path.is_file()
            or features.get("sha256") != _sha256(features_path)
            or not response_valid
        ):
            raise R3UniProtSequenceFeaturesError("R3 UniProt sequence-feature receipt is invalid")
        return R3UniProtSequenceFeaturesSummary(
            canonical_protein_count=int(receipt["canonical_protein_count"]),
            descriptor_count=int(receipt["descriptor_count"]),
            response_batch_count=int(receipt["response_batch_count"]),
            status=self.STATUS,
            receipt_path=receipt_path,
        )
