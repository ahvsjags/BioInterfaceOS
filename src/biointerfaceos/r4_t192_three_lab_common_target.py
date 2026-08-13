"""Audit a redistributable common target across three independent lab anchors.

T192 is deliberately a development-only asset audit.  It freezes the exact
intersection of row-traceable, strictly positive target accessions across
three separately licensed source packages before any new model is fitted.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4T192ThreeLabCommonTargetError(RuntimeError):
    """Raised when the frozen T192 admission cannot be reproduced."""


@dataclass(frozen=True)
class R4T192ThreeLabCommonTargetSummary:
    source_count: int
    laboratory_anchor_count: int
    common_target_count: int
    common_row_count: int
    source_cell_count: int
    rank_eligible_cell_count: int
    source_batch_counts: dict[str, int]
    receipt_path: Path


class R4T192ThreeLabCommonTargetWorkflow:
    """Recompute and verify the frozen Edinburgh-Dalian-UCD target asset."""

    AUDIT_ID = "bioif-r4-t192-three-lab-redistributable-common-target-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/three_lab_redistributable_common_target/v1.0.0"
    STATUS = "THREE_INDEPENDENT_LABORATORY_COMMON_TARGET_VERIFIED_RESTRICTED_DEVELOPMENT"
    LEDGER_FIELDS = [
        "target_observation_id",
        "source_id",
        "laboratory_anchor",
        "source_license",
        "canonical_accession",
        "measurement_batch_id",
        "biological_unit_id",
        "source_asset_id",
        "source_worksheet",
        "source_row",
        "source_coordinate",
        "source_identifier",
        "source_sample",
        "condition_label",
        "technical_replicate_id",
        "author_quantity_type",
        "author_numeric_value",
        "author_value_state",
        "rank_target_eligible",
        "common_target_member",
        "source_local_rank_percentile",
        "source_batch_positive_count",
        "cross_source_scale_use",
    ]

    def __init__(
        self,
        root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4T192ThreeLabCommonTargetError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4T192ThreeLabCommonTargetError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T192ThreeLabCommonTargetError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T192ThreeLabCommonTargetError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        item = _mapping(value, label)
        if set(item) != {"relative_path", "sha256"}:
            raise R4T192ThreeLabCommonTargetError(f"{label} reference fields are invalid")
        path = self._root_file(_string(item["relative_path"], label), label)
        if _sha256(path) != _checksum(item["sha256"], label):
            raise R4T192ThreeLabCommonTargetError(f"{label} checksum differs")
        return path

    def _documents(self) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T192 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "target_freeze",
            "sources",
            "output_contract",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T192ThreeLabCommonTargetError("T192 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != self.STATUS
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T192ThreeLabCommonTargetError("T192 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T192 protocol")
        protocol = self._json(protocol_path, "T192 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_FOR_DEVELOPMENT_ADMISSION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T192ThreeLabCommonTargetError("T192 protocol identity or boundary is invalid")
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 3:
            raise R4T192ThreeLabCommonTargetError("T192 registry must contain exactly three sources")
        return registry, protocol, [_mapping(source, "T192 source") for source in sources]

    def _validate_source_metadata(self, source: Mapping[str, Any]) -> tuple[Path, list[dict[str, str]]]:
        required = {
            "source_id",
            "laboratory_anchor",
            "license",
            "source_lineage",
            "biological_unit_semantics",
            "source_locator",
            "source_registry",
            "source_audit_report",
            "source_audit_receipt",
            "source_cell_map",
            "raw_assets",
            "expected_accounting",
        }
        if set(source) != required:
            raise R4T192ThreeLabCommonTargetError("T192 source fields are invalid")
        if source["license"] not in {"CC0", "CC0-1.0", "CC-BY-4.0"}:
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} license is not redistributable")
        registry_path = self._reference(source["source_registry"], f"{source['source_id']} source registry")
        report_path = self._reference(source["source_audit_report"], f"{source['source_id']} audit report")
        receipt_path = self._reference(source["source_audit_receipt"], f"{source['source_id']} audit receipt")
        map_path = self._reference(source["source_cell_map"], f"{source['source_id']} source-cell map")
        for index, asset in enumerate(source["raw_assets"]):
            self._reference(asset, f"{source['source_id']} raw asset {index}")
        source_registry = self._json(registry_path, f"{source['source_id']} source registry")
        report = self._json(report_path, f"{source['source_id']} audit report")
        receipt = self._json(receipt_path, f"{source['source_id']} audit receipt")
        if report.get("scientific_submission_ready") is not False or receipt.get("scientific_submission_ready") is not False:
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} source boundary is invalid")
        if receipt.get("report", {}).get("sha256") not in {None, _sha256(report_path)} and receipt.get("report_sha256") != _sha256(report_path):
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} receipt does not close audit report")
        if source["source_id"] not in str(source_registry) and source["source_id"] not in str(report):
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} source identity is not present in audit artifacts")
        with map_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
        required_map = {
            "source_id",
            "laboratory_anchor",
            "source_asset_id",
            "source_row",
            "source_coordinate",
            "source_identifier",
            "canonical_accession",
            "measurement_batch_id",
            "author_numeric_value",
            "rank_target_eligible",
        }
        if reader.fieldnames is None or not required_map.issubset(reader.fieldnames):
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} source map schema is invalid")
        if not rows:
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} source map is empty")
        eligible: list[dict[str, str]] = []
        for row in rows:
            if row.get("source_id") != source["source_id"] or row.get("laboratory_anchor") != source["laboratory_anchor"]:
                raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} source identity differs in map")
            for field in required_map - {"author_numeric_value", "rank_target_eligible"}:
                if not str(row.get(field, "")).strip():
                    raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} map has blank {field}")
            candidate = row.get("analysis_candidate_eligible", "true").strip().lower() == "true"
            rank_eligible = row.get("rank_target_eligible", "").strip().lower() == "true"
            if rank_eligible and candidate:
                try:
                    value = float(row["author_numeric_value"])
                except (TypeError, ValueError) as exc:
                    raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} eligible value is not numeric") from exc
                if not math.isfinite(value) or value <= 0:
                    raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} eligible value is not strictly positive")
                if not row.get("canonical_accession", "").strip():
                    raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} eligible accession is blank")
                eligible.append(row)
        expected = _mapping(source["expected_accounting"], f"{source['source_id']} expected accounting")
        targets = {row["canonical_accession"] for row in eligible}
        batches = {row["measurement_batch_id"] for row in eligible}
        if (
            len(rows) != expected["raw_map_rows"]
            or len(eligible) != expected["rank_eligible_rows"]
            or len(targets) != expected["rank_eligible_target_count"]
            or len(batches) != expected["rank_eligible_batch_count"]
        ):
            raise R4T192ThreeLabCommonTargetError(f"{source['source_id']} source accounting differs")
        return map_path, eligible

    @staticmethod
    def _rank_rows(rows: list[dict[str, str]]) -> dict[int, tuple[float, int]]:
        by_batch: dict[str, list[tuple[int, float]]] = defaultdict(list)
        for index, row in enumerate(rows):
            by_batch[row["measurement_batch_id"]].append((index, float(row["author_numeric_value"])))
        ranks: dict[int, tuple[float, int]] = {}
        for batch_rows in by_batch.values():
            ordered = sorted(batch_rows, key=lambda item: (-item[1], item[0]))
            count = len(ordered)
            cursor = 0
            while cursor < count:
                end = cursor + 1
                while end < count and ordered[end][1] == ordered[cursor][1]:
                    end += 1
                midrank = (cursor + 1 + end) / 2.0
                percentile = 0.5 if count == 1 else (count - midrank) / (count - 1)
                for position in range(cursor, end):
                    ranks[ordered[position][0]] = (percentile, count)
                cursor = end
        return ranks

    def _execute(self) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
        registry, protocol, sources = self._documents()
        all_eligible: dict[str, list[dict[str, str]]] = {}
        map_paths: dict[str, Path] = {}
        for source in sources:
            map_path, rows = self._validate_source_metadata(source)
            map_paths[source["source_id"]] = map_path
            all_eligible[source["source_id"]] = rows
        target_sets = {source_id: {row["canonical_accession"] for row in rows} for source_id, rows in all_eligible.items()}
        common_targets = set.intersection(*target_sets.values())
        freeze = _mapping(registry["target_freeze"], "T192 target freeze")
        expected_targets = set(freeze["common_targets"])
        if common_targets != expected_targets or len(common_targets) != freeze["common_target_count"]:
            raise R4T192ThreeLabCommonTargetError("T192 target intersection differs from frozen target set")
        source_by_id = {source["source_id"]: source for source in sources}
        ledger_rows: list[dict[str, str]] = []
        source_accounting: dict[str, dict[str, Any]] = {}
        for source_id in sorted(all_eligible):
            source = source_by_id[source_id]
            rows = all_eligible[source_id]
            ranks = self._rank_rows(rows)
            common = [row for row in rows if row["canonical_accession"] in common_targets]
            common_pairs = {(row["canonical_accession"], row["measurement_batch_id"]) for row in common}
            expected = _mapping(source["expected_accounting"], f"{source_id} expected accounting")
            if len(common) != expected["common_rows"] or len(common_pairs) != expected["common_target_batch_pairs"]:
                raise R4T192ThreeLabCommonTargetError(f"{source_id} common accounting differs")
            source_accounting[source_id] = {
                "laboratory_anchor": source["laboratory_anchor"],
                "license": source["license"],
                "raw_map_rows": expected["raw_map_rows"],
                "rank_eligible_rows": len(rows),
                "rank_eligible_target_count": len(target_sets[source_id]),
                "rank_eligible_batch_count": len({row["measurement_batch_id"] for row in rows}),
                "common_rows": len(common),
                "common_target_batch_pairs": len(common_pairs),
                "source_cell_map": source["source_cell_map"],
                "biological_unit_semantics": source["biological_unit_semantics"],
            }
            for row_index, row in sorted(enumerate(common), key=lambda item: (item[1]["measurement_batch_id"], item[1]["canonical_accession"], item[1]["source_coordinate"])):
                percentile, positive_count = ranks[rows.index(row)]
                ledger_rows.append(
                    {
                        "target_observation_id": f"T192_{source_id}_{len(ledger_rows) + 1:06d}",
                        "source_id": source_id,
                        "laboratory_anchor": source["laboratory_anchor"],
                        "source_license": source["license"],
                        "canonical_accession": row["canonical_accession"],
                        "measurement_batch_id": row["measurement_batch_id"],
                        "biological_unit_id": row.get("biological_unit_id", ""),
                        "source_asset_id": row["source_asset_id"],
                        "source_worksheet": row.get("source_worksheet", ""),
                        "source_row": row["source_row"],
                        "source_coordinate": row["source_coordinate"],
                        "source_identifier": row["source_identifier"],
                        "source_sample": row.get("source_sample", ""),
                        "condition_label": row.get("condition_label", ""),
                        "technical_replicate_id": row.get("technical_replicate_id", ""),
                        "author_quantity_type": row.get("author_quantity_type", ""),
                        "author_numeric_value": row["author_numeric_value"],
                        "author_value_state": row.get("author_value_state", ""),
                        "rank_target_eligible": "true",
                        "common_target_member": "true",
                        "source_local_rank_percentile": format(percentile, ".17g"),
                        "source_batch_positive_count": str(positive_count),
                        "cross_source_scale_use": "PROHIBITED",
                    }
                )
        output_contract = _mapping(registry["output_contract"], "T192 output contract")
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "status": self.STATUS,
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "scientific_submission_ready": False,
            "laboratory_anchors": sorted({source["laboratory_anchor"] for source in sources}),
            "laboratory_anchor_count": len(sources),
            "source_count": len(sources),
            "common_target_count": len(common_targets),
            "common_targets": sorted(common_targets),
            "common_row_count": len(ledger_rows),
            "source_cell_count": sum(
                _mapping(source["expected_accounting"], f"{source['source_id']} expected accounting")["raw_map_rows"]
                for source in sources
            ),
            "rank_eligible_cell_count": sum(len(rows) for rows in all_eligible.values()),
            "source_batch_counts": {source_id: len({row["measurement_batch_id"] for row in rows}) for source_id, rows in all_eligible.items()},
            "source_accounting": source_accounting,
            "input_references": {
                "protocol": {"relative_path": self.PROTOCOL_RELATIVE, "sha256": _sha256(self.root / self.PROTOCOL_RELATIVE)},
                "registry": {"relative_path": self.REGISTRY_RELATIVE, "sha256": _sha256(self.registry_path)},
                "source_cell_maps": {
                    source_id: {"relative_path": str(map_paths[source_id].relative_to(self.root).as_posix()), "sha256": _sha256(map_paths[source_id])}
                    for source_id in sorted(map_paths)
                },
            },
            "output_contract": output_contract,
            "claim_boundary": registry["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
        }
        return report, ledger_rows, registry

    def run(self, *, strict: bool = False) -> R4T192ThreeLabCommonTargetSummary:
        if not strict:
            raise R4T192ThreeLabCommonTargetError("T192 audit requires --strict")
        if self.output_root.exists():
            raise R4T192ThreeLabCommonTargetError("T192 audit already executed")
        report, ledger_rows, _ = self._execute()
        self.output_root.mkdir(parents=True, exist_ok=False)
        ledger_path = self.output_root / "r4_t192_three_lab_common_target_ledger.csv"
        self._write_csv(ledger_path, self.LEDGER_FIELDS, ledger_rows)
        try:
            ledger_relative_path = ledger_path.relative_to(self.root).as_posix()
        except ValueError:
            ledger_relative_path = ledger_path.relative_to(self.output_root).as_posix()
        report["ledger"] = {"relative_path": ledger_relative_path, "sha256": _sha256(ledger_path), "row_count": len(ledger_rows)}
        report_path = self.output_root / "r4_t192_three_lab_common_target_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "ledger_sha256": _sha256(ledger_path),
            "source_count": report["source_count"],
            "laboratory_anchor_count": report["laboratory_anchor_count"],
            "common_target_count": report["common_target_count"],
            "common_row_count": report["common_row_count"],
            "source_cell_count": report["source_cell_count"],
            "rank_eligible_cell_count": report["rank_eligible_cell_count"],
            "source_batch_counts": report["source_batch_counts"],
            "scientific_submission_ready": False,
            "independent_validation": False,
        }
        receipt_path = self.output_root / "r4_t192_three_lab_common_target_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T192ThreeLabCommonTargetSummary(
            report["source_count"], report["laboratory_anchor_count"], report["common_target_count"],
            report["common_row_count"], report["source_cell_count"], report["rank_eligible_cell_count"],
            report["source_batch_counts"], receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T192ThreeLabCommonTargetSummary:
        if not strict:
            raise R4T192ThreeLabCommonTargetError("T192 verify requires --strict")
        ledger_path = self.output_root / "r4_t192_three_lab_common_target_ledger.csv"
        report_path = self.output_root / "r4_t192_three_lab_common_target_report.json"
        receipt_path = self.output_root / "r4_t192_three_lab_common_target_receipt.json"
        report = self._json(report_path, "T192 report")
        receipt = self._json(receipt_path, "T192 receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("ledger_sha256") != _sha256(ledger_path)
            or report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T192ThreeLabCommonTargetError("T192 report, receipt or ledger identity differs")
        recomputed, ledger_rows, _ = self._execute()
        report_comparable = (
            "source_count", "laboratory_anchor_count", "common_target_count", "common_row_count",
            "source_cell_count", "rank_eligible_cell_count", "source_batch_counts", "common_targets",
        )
        receipt_comparable = (
            "source_count", "laboratory_anchor_count", "common_target_count", "common_row_count",
            "source_cell_count", "rank_eligible_cell_count", "source_batch_counts",
        )
        if any(report.get(key) != recomputed.get(key) for key in report_comparable) or any(
            receipt.get(key) != recomputed.get(key) for key in receipt_comparable
        ):
            raise R4T192ThreeLabCommonTargetError("T192 accounting differs from current inputs")
        with ledger_path.open(newline="", encoding="utf-8") as stream:
            current_rows = list(csv.DictReader(stream))
        expected_rows = [{field: row[field] for field in self.LEDGER_FIELDS} for row in ledger_rows]
        if current_rows != expected_rows:
            raise R4T192ThreeLabCommonTargetError("T192 ledger differs from current inputs")
        return R4T192ThreeLabCommonTargetSummary(
            recomputed["source_count"], recomputed["laboratory_anchor_count"], recomputed["common_target_count"],
            recomputed["common_row_count"], recomputed["source_cell_count"], recomputed["rank_eligible_cell_count"],
            recomputed["source_batch_counts"], receipt_path,
        )
