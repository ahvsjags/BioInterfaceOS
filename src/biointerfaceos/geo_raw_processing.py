"""Fixture-backed paired-end raw RNA-seq counting with explicit provenance."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class GeoRawProcessingError(RuntimeError):
    """Raised when the bounded raw RNA-seq fixture fails a declared gate."""


@dataclass(frozen=True)
class GeoRawProcessingSummary:
    """Summary of one study-local raw-counting run."""

    studies_attempted: int
    studies_passed: int
    excluded_studies: int
    genes: int
    samples: int
    pairs: int
    matched_pairs: int
    unmatched_pairs: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GeoRawProcessingError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeoRawProcessingError(f"{label} must be a non-empty string")
    return value.strip()


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GeoRawProcessingError(f"{label} must be an integer")
    return int(value)


class GeoRawProcessingWorkflow:
    """Count exact paired reads against a versioned toy reference."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/geo_raw_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/geo_raw"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GeoRawProcessingError(f"cannot load GEO raw fixture: {exc}") from exc
        fixture = _mapping(data, "GEO raw fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "raw":
            raise GeoRawProcessingError("GEO raw fixture schema or mode is invalid")
        for key in ("counting", "study"):
            if key not in fixture:
                raise GeoRawProcessingError(f"GEO raw fixture missing {key}")
        return fixture

    @staticmethod
    def _verify_digest(material: Any, expected: Any, label: str) -> None:
        material_text = _string(material, f"{label} checksum material")
        expected_text = _string(expected, f"{label} checksum")
        if _sha256(material_text.encode("utf-8")) != expected_text:
            raise GeoRawProcessingError(f"{label} checksum differs from fixture")

    def _process_study(
        self, study: Mapping[str, Any], counting: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], int, int, int]:
        accession = _string(study.get("accession"), "study accession")
        if study.get("access_state") != "PUBLIC":
            raise GeoRawProcessingError(f"raw study is not public: {accession}")
        if study.get("credential_required") is not False:
            raise GeoRawProcessingError(f"raw study requires credentials: {accession}")
        if study.get("manageable") is not True:
            raise GeoRawProcessingError(f"raw study is not manageable: {accession}")
        self._verify_digest(
            study.get("source_checksum_material"), study.get("source_file_sha256"), "source reads"
        )
        reference = _mapping(study.get("reference"), "reference")
        reference_version = _string(reference.get("version"), "reference version")
        self._verify_digest(
            reference.get("checksum_material"), reference.get("sha256"), "reference"
        )
        reference_rows = reference.get("genes")
        if not isinstance(reference_rows, list) or not reference_rows:
            raise GeoRawProcessingError("reference has no genes")
        sequence_to_gene: dict[str, str] = {}
        gene_ids: set[str] = set()
        for value in reference_rows:
            row = _mapping(value, "reference gene")
            gene_id = _string(row.get("gene_id"), "reference gene ID")
            sequence = _string(row.get("sequence"), "reference sequence")
            if gene_id in gene_ids or sequence in sequence_to_gene:
                raise GeoRawProcessingError("reference gene or sequence is duplicated")
            gene_ids.add(gene_id)
            sequence_to_gene[sequence] = gene_id

        samples = study.get("samples")
        if not isinstance(samples, list) or not samples:
            raise GeoRawProcessingError(f"raw study has no samples: {accession}")
        min_replicates = _int(counting.get("min_pairs_per_condition"), "min pairs per condition")
        sample_rows: list[dict[str, Any]] = []
        counts_rows: list[dict[str, Any]] = []
        qc_rows: list[dict[str, Any]] = []
        sample_ids: set[str] = set()
        conditions: dict[str, set[int]] = {}
        total_pairs = 0
        total_matched = 0
        total_unmatched = 0
        for value in samples:
            sample = _mapping(value, "raw sample")
            sample_id = _string(sample.get("sample_id"), "sample ID")
            condition = _string(sample.get("condition"), "sample condition")
            replicate = _int(sample.get("biological_replicate"), "biological replicate")
            if sample_id in sample_ids or replicate < 1:
                raise GeoRawProcessingError(f"sample metadata is invalid: {accession}")
            sample_ids.add(sample_id)
            conditions.setdefault(condition, set()).add(replicate)
            sample_rows.append(
                {
                    "study_accession": accession,
                    "sample_id": sample_id,
                    "condition": condition,
                    "biological_replicate": replicate,
                    "material": _string(sample.get("material"), "sample material"),
                    "biological_system": _string(sample.get("biological_system"), "sample system"),
                    "dose": _string(sample.get("dose"), "sample dose"),
                    "time": _string(sample.get("time"), "sample time"),
                }
            )
            counts = {gene_id: 0 for gene_id in sorted(gene_ids)}
            pairs = sample.get("pairs")
            if not isinstance(pairs, list) or not pairs:
                raise GeoRawProcessingError(f"sample has no read pairs: {sample_id}")
            pair_ids: set[str] = set()
            matched = 0
            unmatched = 0
            for pair_value in pairs:
                pair = _mapping(pair_value, "read pair")
                pair_id = _string(pair.get("pair_id"), "pair ID")
                if pair_id in pair_ids:
                    raise GeoRawProcessingError(f"duplicate pair ID: {pair_id}")
                pair_ids.add(pair_id)
                read1 = _string(pair.get("read1"), "read1")
                read2 = _string(pair.get("read2"), "read2")
                gene1 = sequence_to_gene.get(read1)
                gene2 = sequence_to_gene.get(read2)
                if gene1 is not None and gene1 == gene2:
                    counts[gene1] += 1
                    matched += 1
                else:
                    unmatched += 1
            expected_counts = {
                _string(key, "expected gene ID"): _int(value, "expected count")
                for key, value in _mapping(sample.get("expected_counts"), "expected counts").items()
            }
            if expected_counts != counts:
                raise GeoRawProcessingError(f"count recovery failed: {sample_id}")
            expected_unmatched = _int(
                sample.get("expected_unmatched_pairs"), "expected unmatched pairs"
            )
            if expected_unmatched != unmatched:
                raise GeoRawProcessingError(f"unmatched-pair QC failed: {sample_id}")
            pairs_count = len(pairs)
            sample_counts = {
                "study_accession": accession,
                "sample_id": sample_id,
                "counts": counts,
            }
            counts_rows.append(sample_counts)
            qc_rows.append(
                {
                    "study_accession": accession,
                    "sample_id": sample_id,
                    "pairs": pairs_count,
                    "matched_pairs": matched,
                    "unmatched_pairs": unmatched,
                    "matching_rate": round(matched / pairs_count, 8),
                    "passed": True,
                    "reference_version": reference_version,
                    "counting_rule": _string(counting.get("rule"), "counting rule"),
                }
            )
            total_pairs += pairs_count
            total_matched += matched
            total_unmatched += unmatched
        if any(len(replicates) < min_replicates for replicates in conditions.values()):
            raise GeoRawProcessingError(f"within-study replicate QC failed: {accession}")
        condition_means: dict[str, dict[str, float]] = {}
        for condition in sorted(conditions):
            condition_ids = [
                row["sample_id"] for row in sample_rows if row["condition"] == condition
            ]
            condition_means[condition] = {
                gene_id: round(
                    sum(
                        row["counts"][gene_id]
                        for row in counts_rows
                        if row["sample_id"] in condition_ids
                    )
                    / len(condition_ids),
                    8,
                )
                for gene_id in sorted(gene_ids)
            }
        contrasts = []
        if set(condition_means) == {"control", "treated"}:
            for gene_id in sorted(gene_ids):
                control = condition_means["control"][gene_id]
                treated = condition_means["treated"][gene_id]
                contrasts.append(
                    {
                        "study_accession": accession,
                        "normalized_gene_id": gene_id,
                        "control_mean_count": control,
                        "treated_mean_count": treated,
                        "treated_minus_control": round(treated - control, 8),
                        "treated_control_ratio": round(treated / control, 8)
                        if control > 0
                        else None,
                    }
                )
        study_object = {
            "study_accession": accession,
            "source_file_sha256": _string(study.get("source_file_sha256"), "source checksum"),
            "reference_version": reference_version,
            "counting_rule": _string(counting.get("rule"), "counting rule"),
            "sample_metadata": sample_rows,
            "counts": counts_rows,
            "within_study_only": True,
            "cross_study_batch_merge": False,
        }
        return study_object, qc_rows, contrasts, total_pairs, total_matched, total_unmatched

    def run(self, *, mode: str = "raw", fixture: bool = True) -> GeoRawProcessingSummary:
        """Run the bounded raw fixture workflow with deterministic resume."""
        if mode != "raw":
            raise GeoRawProcessingError("only raw mode is supported")
        if not fixture:
            raise GeoRawProcessingError("--fixture is required for raw mode")
        data = self._load_fixture()
        study = _mapping(data["study"], "study")
        counting = _mapping(data["counting"], "counting")
        study_object, qc_rows, contrasts, pairs, matched, unmatched = self._process_study(
            study, counting
        )
        resume_material = {
            "study": study_object,
            "qc": qc_rows,
            "contrasts": contrasts,
        }
        resume_key = _sha256(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "counts": self.output_root / "raw_counts.json",
            "samples": self.output_root / "sample_metadata.json",
            "qc": self.output_root / "within_study_qc.json",
            "contrasts": self.output_root / "contrast_summaries.json",
            "excluded": self.output_root / "exclusion_ledger.json",
            "receipt": self.output_root / "processing_receipt.json",
            "log": self.output_root / "processing_log.json",
            "manifest": self.output_root / "processing_manifest.json",
        }
        raw_payloads = {
            "counts": {"schema_version": 1, "studies": [study_object]},
            "samples": {"schema_version": 1, "samples": study_object["sample_metadata"]},
            "qc": {
                "schema_version": 1,
                "studies": qc_rows,
                "within_study_only": True,
                "cross_study_batch_merge": False,
            },
            "contrasts": {"schema_version": 1, "contrasts": contrasts},
            "excluded": {"schema_version": 1, "append_only": True, "entries": []},
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root))
                if path.is_relative_to(self.root)
                else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "mode": "raw",
            "fixture": True,
            "study_accession": study_object["study_accession"],
            "source_file_sha256": study_object["source_file_sha256"],
            "reference_version": study_object["reference_version"],
            "counting_rule": study_object["counting_rule"],
            "studies_attempted": 1,
            "studies_passed": 1,
            "excluded_studies": 0,
            "samples": len(study_object["sample_metadata"]),
            "pairs": pairs,
            "matched_pairs": matched,
            "unmatched_pairs": unmatched,
            "raw_downloaded": False,
            "locked_payload_accessed": False,
            "real_network_accessed": False,
            "cross_study_batch_merge": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {
                    "event": "public_manageable_study_verified",
                    "accession": study_object["study_accession"],
                },
                {
                    "event": "versioned_reference_verified",
                    "reference_version": study_object["reference_version"],
                },
                {"event": "paired_end_exact_counts_recovered", "matched_pairs": matched},
                {"event": "unmatched_reads_retained_in_qc", "unmatched_pairs": unmatched},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "mode": "raw",
            "resume_supported": True,
            "resume_key": resume_key,
            "studies_attempted": 1,
            "studies_passed": 1,
            "excluded_studies": 0,
            "genes": len(study_object["counts"][0]["counts"]),
            "samples": len(study_object["sample_metadata"]),
            "pairs": pairs,
            "matched_pairs": matched,
            "unmatched_pairs": unmatched,
            "cross_study_batch_merge": False,
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path),
                    "sha256": _sha256(payload_bytes[name]),
                    "bytes": len(payload_bytes[name]),
                }
                for name, path in paths.items()
                if name in payload_bytes
            },
        }
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise GeoRawProcessingError("existing GEO raw receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise GeoRawProcessingError(f"existing GEO raw artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return GeoRawProcessingSummary(
            studies_attempted=1,
            studies_passed=1,
            excluded_studies=0,
            genes=len(study_object["counts"][0]["counts"]),
            samples=len(study_object["sample_metadata"]),
            pairs=pairs,
            matched_pairs=matched,
            unmatched_pairs=unmatched,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
