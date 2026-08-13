"""Admit a source-local protein-corona rank target across three CC-BY sources.

The target is a within-measurement-batch percentile rank of a strictly positive
author-reported quantity.  It deliberately does not make raw LFQ, intensity,
PSM or spectral-count values comparable across studies, and it preserves zero,
blank and ``NA`` source states outside the rank-eligible population.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R3CommonRankTargetError(RuntimeError):
    """Raised when a three-source rank target is incomplete or over-promoted."""


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R3CommonRankTargetError(f"{label} must contain at least {minimum} items")
    return value


def _finite(value: Any, label: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise R3CommonRankTargetError(f"{label} must be numeric") from exc
    if not math.isfinite(numeric):
        raise R3CommonRankTargetError(f"{label} must be finite")
    return numeric


@dataclass(frozen=True)
class R3CommonRankTargetSummary:
    """Accounting for an admitted target that is not yet model-enabled."""

    shared_canonical_protein_count: int
    rank_eligible_shared_canonical_protein_count: int
    eligible_rank_observation_count: int
    laboratory_anchor_count: int
    measurement_batch_count: int
    status: str
    receipt_path: Path


class R3CommonRankTargetWorkflow:
    """Generate a cell-traceable, source-local rank ledger for R3 planning."""

    AUDIT_ID = "bioif-r3-common-rank-target-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R3_T149_COMMON_RANK_TARGET_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_3/common_rank_target/v1.0.0"
    DERIVED_RELATIVE = "r3_common_rank_target/R3_common_rank_target_ledger.csv"
    STATUS = "ADMITTED_COMMON_RANK_TARGET_PROTOCOL_AMENDMENT_REQUIRED"
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "uniprot_mapping_receipt",
        "shared_source_cells",
        "source_maps",
        "target_definition",
        "minimums",
    }
    REQUIRED_MAPPING_RECEIPT = {"relative_path", "sha256"}
    REQUIRED_SHARED = {"relative_path", "sha256"}
    REQUIRED_SOURCE = {"source_id", "laboratory_anchor", "relative_path", "sha256"}
    REQUIRED_TARGET = {
        "target_id",
        "target_description",
        "rank_direction",
        "rank_eligible_source_state",
        "zero_state",
        "blank_state",
        "na_state",
        "prohibited_interpretations",
    }
    REQUIRED_MINIMUMS = {
        "shared_canonical_protein_count",
        "rank_eligible_shared_canonical_protein_count",
        "laboratory_anchor_count",
        "measurement_batch_count",
        "eligible_rank_observation_count",
    }
    SOURCE_IDS = (
        "PXD017052_SEER_BROAD",
        "PMC9633814_MSU_MULTICORE",
        "PMC7788026_OUHSC_GOLD",
    )

    def __init__(
        self,
        root: Path,
        output_data_root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.output_data_root = output_data_root.resolve(strict=False)
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
            raise R3CommonRankTargetError(f"cannot parse {label}") from exc
        try:
            return _mapping(value, label)
        except Exception as exc:
            raise R3CommonRankTargetError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R3CommonRankTargetError(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R3CommonRankTargetError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R3CommonRankTargetError(f"{label} is missing or outside repository root")
        return path

    def _verified_file(self, value: Any, label: str) -> Path:
        item = _mapping(value, label)
        if set(item) != {"relative_path", "sha256"}:
            raise R3CommonRankTargetError(f"{label} fields are invalid")
        path = self._root_file(_string(item.get("relative_path"), label), label)
        if _sha256(path) != _checksum(item.get("sha256"), label):
            raise R3CommonRankTargetError(f"{label} checksum differs")
        return path

    def _registry(self) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        registry = self._json(self.registry_path, "R3 common rank registry")
        if set(registry) != self.REQUIRED_TOP_LEVEL or registry.get("schema_version") != 1:
            raise R3CommonRankTargetError("R3 common rank registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise R3CommonRankTargetError("R3 common rank registry identity is invalid")
        if (
            registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R3CommonRankTargetError("R3 common rank evidence boundary is invalid")
        _string(registry.get("evaluated_at"), "R3 common rank evaluated_at")
        receipt_path = self._verified_file(registry.get("uniprot_mapping_receipt"), "R3 UniProt receipt")
        receipt = self._json(receipt_path, "R3 UniProt receipt")
        if (
            receipt.get("audit_id") != "bioif-r3-uniprot-human-mapping-v1.0.1"
            or receipt.get("status")
            != "CANDIDATE_SHARED_PROTEIN_UNIVERSE_PENDING_PROTOCOL_AMENDMENT"
            or receipt.get("target_status") != "CANDIDATE_COMMON_TARGET_NOT_FROZEN"
            or receipt.get("model_fitted") is not False
        ):
            raise R3CommonRankTargetError("R3 UniProt receipt boundary is invalid")
        self._verified_file(registry.get("shared_source_cells"), "R3 shared source cells")
        source_maps: dict[str, dict[str, Any]] = {}
        for value in _list(registry.get("source_maps"), "R3 source maps", minimum=3):
            source = _mapping(value, "R3 source map")
            if set(source) != self.REQUIRED_SOURCE:
                raise R3CommonRankTargetError("R3 source-map fields are invalid")
            source_id = _string(source.get("source_id"), "R3 source-map ID")
            if source_id in source_maps:
                raise R3CommonRankTargetError("R3 source-map ID is duplicated")
            path = self._root_file(_string(source.get("relative_path"), source_id), source_id)
            if _sha256(path) != _checksum(source.get("sha256"), source_id):
                raise R3CommonRankTargetError(f"R3 source-map checksum differs: {source_id}")
            source_maps[source_id] = {**source, "path": path}
        if tuple(sorted(source_maps)) != tuple(sorted(self.SOURCE_IDS)):
            raise R3CommonRankTargetError("R3 source-map laboratory roster is invalid")
        target = _mapping(registry.get("target_definition"), "R3 target definition")
        if set(target) != self.REQUIRED_TARGET or (
            target.get("target_id") != "R3_WITHIN_MEASUREMENT_BATCH_POSITIVE_QUANTIFICATION_RANK_PERCENTILE"
            or target.get("rank_direction") != "DESCENDING_MIDRANK_PERCENTILE"
            or target.get("rank_eligible_source_state") != "STRICTLY_POSITIVE_FINITE_AUTHOR_VALUE"
            or target.get("zero_state") != "RETAINED_NOT_RANK_ELIGIBLE"
            or target.get("blank_state") != "RETAINED_NOT_RANK_ELIGIBLE"
            or target.get("na_state") != "RETAINED_NOT_RANK_ELIGIBLE"
        ):
            raise R3CommonRankTargetError("R3 target definition is invalid")
        _string(target.get("target_description"), "R3 target description")
        if any(not isinstance(item, str) or not item.strip() for item in _list(target.get("prohibited_interpretations"), "R3 target prohibited interpretations", minimum=3)):
            raise R3CommonRankTargetError("R3 target prohibited interpretations are invalid")
        minimums = _mapping(registry.get("minimums"), "R3 target minimums")
        if set(minimums) != self.REQUIRED_MINIMUMS or any(
            not isinstance(value, int) or value < 1 for value in minimums.values()
        ):
            raise R3CommonRankTargetError("R3 target minimums are invalid")
        return registry, source_maps

    @staticmethod
    def _shared_accessions(shared_path: Path) -> tuple[dict[str, dict[str, str]], set[str]]:
        with shared_path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        fields = {
            "source_id",
            "canonical_accession",
            "source_identifier",
            "source_analysis_unit_id",
            "source_asset_id",
            "source_worksheet",
            "source_row",
            "source_coordinate",
        }
        if not rows or set(rows[0]) != fields:
            raise R3CommonRankTargetError("R3 shared source-cell schema is invalid")
        by_source_unit: dict[str, dict[str, str]] = {}
        accessions: set[str] = set()
        for row in rows:
            source_id = row["source_id"]
            key = f"{source_id}:{row['source_analysis_unit_id']}"
            if source_id not in R3CommonRankTargetWorkflow.SOURCE_IDS or key in by_source_unit:
                raise R3CommonRankTargetError("R3 shared source-cell identity is invalid")
            if not row["canonical_accession"] or not row["source_analysis_unit_id"]:
                raise R3CommonRankTargetError("R3 shared source-cell fields are empty")
            by_source_unit[key] = row
            accessions.add(row["canonical_accession"])
        if any(
            {row["canonical_accession"] for key, row in by_source_unit.items() if key.startswith(f"{source_id}:")}
            != accessions
            for source_id in R3CommonRankTargetWorkflow.SOURCE_IDS
        ):
            raise R3CommonRankTargetError("R3 shared source-cell canonical coverage is incomplete")
        return by_source_unit, accessions

    @staticmethod
    def _state(value: Any) -> tuple[str, float | None]:
        if value is None or value == "":
            return "SOURCE_BLANK", None
        if isinstance(value, str) and value.strip() == "NA":
            return "AUTHOR_NA", None
        number = _finite(value, "author quantification")
        if number < 0:
            raise R3CommonRankTargetError("author quantification is negative")
        if number == 0:
            return "AUTHOR_EXPLICIT_ZERO", number
        return "POSITIVE_QUANTIFIED", number

    @staticmethod
    def _rank_percentiles(
        records: list[dict[str, Any]]
    ) -> dict[str, tuple[float, int]]:
        ranked: dict[str, tuple[float, int]] = {}
        by_batch: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            if record["author_value_state"] == "POSITIVE_QUANTIFIED":
                by_batch[str(record["measurement_batch_id"])].append(record)
        for batch_id, values in by_batch.items():
            if len({record["source_measurement_id"] for record in values}) != len(values):
                raise R3CommonRankTargetError("R3 source measurement identity is duplicated")
            ordered = sorted(values, key=lambda record: (-float(record["author_numeric_value"]), str(record["source_measurement_id"])))
            count = len(ordered)
            start = 0
            while start < count:
                end = start + 1
                while end < count and float(ordered[end]["author_numeric_value"]) == float(ordered[start]["author_numeric_value"]):
                    end += 1
                midrank = (start + 1 + end) / 2.0
                percentile = 0.5 if count == 1 else (count - midrank) / (count - 1)
                for record in ordered[start:end]:
                    ranked[str(record["source_measurement_id"])] = (percentile, count)
                start = end
        return ranked

    @staticmethod
    def _pxd_records(source: dict[str, Any]) -> list[dict[str, Any]]:
        with source["path"].open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        required = {
            "analysis_unit_id", "source_asset_id", "source_worksheet", "source_row", "source_cell",
            "protein_source_identifier", "particle", "assay_replicate", "author_reported_lfq", "author_value_state",
        }
        if not rows or not required.issubset(rows[0]):
            raise R3CommonRankTargetError("PXD017052 source-cell schema is invalid")
        records: list[dict[str, Any]] = []
        for row in rows:
            state, value = R3CommonRankTargetWorkflow._state(row["author_reported_lfq"])
            if row["author_value_state"] == "SOURCE_BLANK" and state != "SOURCE_BLANK":
                raise R3CommonRankTargetError("PXD017052 source blank state differs")
            if row["author_value_state"] == "NUMERIC" and state == "SOURCE_BLANK":
                raise R3CommonRankTargetError("PXD017052 numeric state differs")
            records.append(
                {
                    "source_id": "PXD017052_SEER_BROAD",
                    "measurement_batch_id": f"PXD017052:{row['particle']}:assay_replicate_{row['assay_replicate']}",
                    "source_measurement_id": row["analysis_unit_id"],
                    "source_analysis_unit_id": row["analysis_unit_id"],
                    "source_asset_id": row["source_asset_id"],
                    "source_worksheet": row["source_worksheet"],
                    "source_row": row["source_row"],
                    "source_coordinate": row["source_cell"],
                    "source_identifier": row["protein_source_identifier"],
                    "author_quantity_type": "LFQ_INTENSITY",
                    "author_numeric_value": value,
                    "author_value_state": state,
                }
            )
        return records

    @staticmethod
    def _multicore_records(source: dict[str, Any]) -> list[dict[str, Any]]:
        with source["path"].open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        required = {
            "analysis_unit_id", "source_asset_id", "source_worksheet", "source_row", "protein_ids",
            "replicate_1", "replicate_2", "replicate_3", "core_facility_code",
        }
        if not rows or not required.issubset(rows[0]):
            raise R3CommonRankTargetError("PMC9633814 source-cell schema is invalid")
        records: list[dict[str, Any]] = []
        replicate_columns = ((1, "replicate_1", "G"), (2, "replicate_2", "H"), (3, "replicate_3", "I"))
        for row in rows:
            for replicate, column, letter in replicate_columns:
                state, value = R3CommonRankTargetWorkflow._state(row[column])
                records.append(
                    {
                        "source_id": "PMC9633814_MSU_MULTICORE",
                        "measurement_batch_id": f"PMC9633814:core_{row['core_facility_code']}:technical_replicate_{replicate}",
                        "source_measurement_id": f"{row['analysis_unit_id']}:replicate_{replicate}",
                        "source_analysis_unit_id": row["analysis_unit_id"],
                        "source_asset_id": row["source_asset_id"],
                        "source_worksheet": row["source_worksheet"],
                        "source_row": row["source_row"],
                        "source_coordinate": f"{row['source_worksheet']}!{letter}{row['source_row']}",
                        "source_identifier": row["protein_ids"],
                        "author_quantity_type": "SEMIQUANTITATIVE_PROTEIN_INTENSITY",
                        "author_numeric_value": value,
                        "author_value_state": state,
                    }
                )
        return records

    @staticmethod
    def _gold_records(source: dict[str, Any]) -> list[dict[str, Any]]:
        with source["path"].open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        required = {
            "analysis_unit_id", "source_asset_id", "source_worksheet", "source_row", "source_cell_range",
            "source_condition_id", "protein_source_identifier", "quantification_column", "author_reported_quantification",
        }
        if not rows or not required.issubset(rows[0]):
            raise R3CommonRankTargetError("PMC7788026 source-cell schema is invalid")
        records: list[dict[str, Any]] = []
        for row in rows:
            state, value = R3CommonRankTargetWorkflow._state(row["author_reported_quantification"])
            records.append(
                {
                    "source_id": "PMC7788026_OUHSC_GOLD",
                    "measurement_batch_id": row["source_condition_id"],
                    "source_measurement_id": row["analysis_unit_id"],
                    "source_analysis_unit_id": row["analysis_unit_id"],
                    "source_asset_id": row["source_asset_id"],
                    "source_worksheet": row["source_worksheet"],
                    "source_row": row["source_row"],
                    "source_coordinate": row["source_cell_range"],
                    "source_identifier": row["protein_source_identifier"],
                    "author_quantity_type": row["quantification_column"],
                    "author_numeric_value": value,
                    "author_value_state": state,
                }
            )
        return records

    def run(self, *, strict: bool = False) -> R3CommonRankTargetSummary:
        if not strict:
            raise R3CommonRankTargetError("R3 common rank target requires --strict")
        if self.output_root.exists():
            raise R3CommonRankTargetError("R3 common rank target already executed")
        registry, sources = self._registry()
        shared_path = self._verified_file(registry["shared_source_cells"], "R3 shared source cells")
        shared_by_source_unit, shared_accessions = self._shared_accessions(shared_path)
        records = (
            self._pxd_records(sources["PXD017052_SEER_BROAD"])
            + self._multicore_records(sources["PMC9633814_MSU_MULTICORE"])
            + self._gold_records(sources["PMC7788026_OUHSC_GOLD"])
        )
        ranks = self._rank_percentiles(records)
        selected: list[dict[str, str]] = []
        source_states: Counter[str] = Counter()
        for record in records:
            shared = shared_by_source_unit.get(f"{record['source_id']}:{record['source_analysis_unit_id']}")
            if shared is None:
                continue
            state = str(record["author_value_state"])
            source_states[f"{record['source_id']}:{state}"] += 1
            rank = ranks.get(str(record["source_measurement_id"]))
            selected.append(
                {
                    "target_observation_id": f"R3:{record['source_measurement_id']}",
                    "source_id": str(record["source_id"]),
                    "canonical_accession": shared["canonical_accession"],
                    "laboratory_anchor": str(sources[record["source_id"]]["laboratory_anchor"]),
                    "measurement_batch_id": str(record["measurement_batch_id"]),
                    "source_analysis_unit_id": str(record["source_analysis_unit_id"]),
                    "source_measurement_id": str(record["source_measurement_id"]),
                    "source_identifier": str(record["source_identifier"]),
                    "source_asset_id": str(record["source_asset_id"]),
                    "source_worksheet": str(record["source_worksheet"]),
                    "source_row": str(record["source_row"]),
                    "source_coordinate": str(record["source_coordinate"]),
                    "author_quantity_type": str(record["author_quantity_type"]),
                    "author_numeric_value": "" if record["author_numeric_value"] is None else format(float(record["author_numeric_value"]), ".17g"),
                    "author_value_state": state,
                    "rank_percentile_descending": "" if rank is None else format(rank[0], ".17g"),
                    "measurement_batch_positive_protein_count": "" if rank is None else str(rank[1]),
                    "rank_target_eligible": "true" if rank is not None else "false",
                }
            )
        if not selected:
            raise R3CommonRankTargetError("R3 common rank target selected no shared observations")
        source_rank_eligible = [row for row in selected if row["rank_target_eligible"] == "true"]
        rank_eligible_shared_accessions = set.intersection(
            *(
                {
                    row["canonical_accession"]
                    for row in source_rank_eligible
                    if row["source_id"] == source_id
                }
                for source_id in self.SOURCE_IDS
            )
        )
        selected = [
            {
                **row,
                "common_rank_target_member": (
                    "true" if row["canonical_accession"] in rank_eligible_shared_accessions else "false"
                ),
            }
            for row in selected
        ]
        eligible = [
            row
            for row in selected
            if row["rank_target_eligible"] == "true"
            and row["common_rank_target_member"] == "true"
        ]
        laboratory_anchors = {row["laboratory_anchor"] for row in eligible}
        measurement_batches = {row["measurement_batch_id"] for row in eligible}
        source_accessions = {
            source_id: {row["canonical_accession"] for row in eligible if row["source_id"] == source_id}
            for source_id in self.SOURCE_IDS
        }
        if not rank_eligible_shared_accessions or any(
            values != rank_eligible_shared_accessions for values in source_accessions.values()
        ):
            raise R3CommonRankTargetError("R3 common rank eligible protein coverage is incomplete")
        minimums = _mapping(registry["minimums"], "R3 target minimums")
        if (
            len(shared_accessions) < minimums["shared_canonical_protein_count"]
            or len(rank_eligible_shared_accessions)
            < minimums["rank_eligible_shared_canonical_protein_count"]
            or len(laboratory_anchors) < minimums["laboratory_anchor_count"]
            or len(measurement_batches) < minimums["measurement_batch_count"]
            or len(eligible) < minimums["eligible_rank_observation_count"]
        ):
            raise R3CommonRankTargetError("R3 common rank target does not meet minimum evidence")
        ledger_path = self.output_data_root / self.DERIVED_RELATIVE
        if ledger_path.exists():
            raise R3CommonRankTargetError("R3 common rank target ledger already exists")
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(selected[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(selected)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "target_definition": registry["target_definition"],
            "source_map_sha256": {source_id: source["sha256"] for source_id, source in sources.items()},
            "shared_canonical_protein_count": len(shared_accessions),
            "rank_eligible_shared_canonical_protein_count": len(rank_eligible_shared_accessions),
            "laboratory_anchor_count": len(laboratory_anchors),
            "laboratory_anchors": sorted(laboratory_anchors),
            "measurement_batch_count": len(measurement_batches),
            "selected_source_observation_count": len(selected),
            "eligible_rank_observation_count": len(eligible),
            "non_eligible_state_counts": {
                key: value for key, value in sorted(source_states.items()) if not key.endswith(":POSITIVE_QUANTIFIED")
            },
            "source_rank_eligible_observation_count_by_source": {
                source_id: sum(1 for row in source_rank_eligible if row["source_id"] == source_id)
                for source_id in self.SOURCE_IDS
            },
            "common_target_eligible_observation_count_by_source": {
                source_id: sum(1 for row in eligible if row["source_id"] == source_id)
                for source_id in self.SOURCE_IDS
            },
            "ledger": {
                "location": self.DERIVED_RELATIVE,
                "sha256": _sha256(ledger_path),
                "coordinate_definition": "Each record retains the original source asset, worksheet, row and measurement-specific cell coordinate.",
                "transformation": "Strictly positive finite author values are converted to descending midrank percentiles within their source-defined measurement batch; zero, blank and NA values remain non-rank-eligible source states.",
            },
            "status": self.STATUS,
            "target_status": "NOT_FROZEN_PROTOCOL_AMENDMENT_REQUIRED",
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
            "shared_canonical_protein_count": len(shared_accessions),
            "rank_eligible_shared_canonical_protein_count": len(rank_eligible_shared_accessions),
            "laboratory_anchor_count": len(laboratory_anchors),
            "measurement_batch_count": len(measurement_batches),
            "eligible_rank_observation_count": len(eligible),
            "target_status": "NOT_FROZEN_PROTOCOL_AMENDMENT_REQUIRED",
            "model_fitted": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        self._write(self.output_root / "common_rank_target_report.json", report)
        self._write(self.output_root / "common_rank_target_receipt.json", receipt)
        return R3CommonRankTargetSummary(
            shared_canonical_protein_count=len(shared_accessions),
            rank_eligible_shared_canonical_protein_count=len(rank_eligible_shared_accessions),
            eligible_rank_observation_count=len(eligible),
            laboratory_anchor_count=len(laboratory_anchors),
            measurement_batch_count=len(measurement_batches),
            status=self.STATUS,
            receipt_path=self.output_root / "common_rank_target_receipt.json",
        )

    def verify(self) -> R3CommonRankTargetSummary:
        report_path = self.output_root / "common_rank_target_report.json"
        receipt_path = self.output_root / "common_rank_target_receipt.json"
        report = self._json(report_path, "R3 common rank target report")
        receipt = self._json(receipt_path, "R3 common rank target receipt")
        ledger = _mapping(report.get("ledger"), "R3 common rank ledger")
        ledger_path = self.output_data_root / _string(ledger.get("location"), "R3 common rank ledger location")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or report.get("target_status") != "NOT_FROZEN_PROTOCOL_AMENDMENT_REQUIRED"
            or report.get("model_fitted") is not False
            or report.get("scientific_submission_ready") is not False
            or not ledger_path.is_file()
            or ledger.get("sha256") != _sha256(ledger_path)
        ):
            raise R3CommonRankTargetError("R3 common rank target receipt is invalid")
        return R3CommonRankTargetSummary(
            shared_canonical_protein_count=int(receipt["shared_canonical_protein_count"]),
            rank_eligible_shared_canonical_protein_count=int(
                receipt["rank_eligible_shared_canonical_protein_count"]
            ),
            eligible_rank_observation_count=int(receipt["eligible_rank_observation_count"]),
            laboratory_anchor_count=int(receipt["laboratory_anchor_count"]),
            measurement_batch_count=int(receipt["measurement_batch_count"]),
            status=self.STATUS,
            receipt_path=receipt_path,
        )
