"""Summarize frozen paper-derived OOD effects without cross-route pooling."""

from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4T284PaperOodSynthesisError(RuntimeError):
    """Raised when the frozen T284 paper-OOD synthesis cannot close."""


@dataclass(frozen=True)
class R4T284PaperOodSynthesisSummary:
    route_count: int
    positive_effect_count: int
    negative_effect_count: int
    near_zero_effect_count: int
    receipt_path: Path


class R4T284PaperOodSynthesisWorkflow:
    AUDIT_ID = "bioif-r4-t284-paper-ood-synthesis-v1.0.0"
    STATUS = "T284_PAPER_OOD_SYNTHESIS_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T284_PAPER_OOD_SYNTHESIS_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t284_paper_ood_synthesis/v1.0.0"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}

    ROUTES = (
        (
            "T203_PMC10257194",
            "paper_biological_cohort",
            "r4_external_ood_model_metrics.csv",
            "t203_pmc10257194_metrics",
        ),
        (
            "T159_SMALL_MOLECULE",
            "paper_same_lineage_cohort",
            "r4_external_ood_model_metrics.csv",
            "t159_small_molecule_metrics",
        ),
        (
            "T209_MANCHESTER",
            "paper_biological_cohort",
            "r4_manchester_ood_model_metrics.csv",
            "t209_manchester_metrics",
        ),
        (
            "T181_PXD017052",
            "paper_biological_cohort",
            "r4_pxd017052_nsclc_ood_model_metrics.csv",
            "t181_pxd017052_metrics",
        ),
        ("T176_PXD068107", "paper_technical_source", "r4_pxd068107_ood_model_metrics.csv", "t176_pxd068107_metrics"),
        (
            "T177_PMC13106918",
            "paper_technical_source",
            "r4_pmc13106918_ood_model_metrics.csv",
            "t177_pmc13106918_metrics",
        ),
    )

    ROUTE_PATHS = {
        "T203_PMC10257194": "reports/review_round_4/pmc10257194_paper_ood/v1.0.0",
        "T159_SMALL_MOLECULE": "reports/review_round_4/small_molecule_corona_ood/v1.0.0",
        "T209_MANCHESTER": "reports/review_round_4/manchester_nanoomic_ood/v1.1.0",
        "T181_PXD017052": "reports/review_round_4/pxd017052_nsclc_biological_ood/v1.0.0",
        "T176_PXD068107": "reports/review_round_4/pxd068107_technical_ood/v1.0.0",
        "T177_PMC13106918": "reports/review_round_4/pmc13106918_technical_ood/v1.0.0",
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T284PaperOodSynthesisError("T284 output must remain under repository root")
        self.output_root = candidate

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: "" if row.get(field) is None else row.get(field) for field in fields})

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise R4T284PaperOodSynthesisError(f"cannot parse {label}") from exc

    @staticmethod
    def _csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T284PaperOodSynthesisError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T284PaperOodSynthesisError(f"{label} is empty")
        return rows

    def _file(self, relative: str, label: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T284PaperOodSynthesisError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T284PaperOodSynthesisError(f"{label} is missing")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T284PaperOodSynthesisError(f"{label} reference fields are invalid")
        path = self._file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T284PaperOodSynthesisError(f"{label} checksum differs")
        return path

    @staticmethod
    def _metric(row: Mapping[str, str], prefix: str = "") -> tuple[float, float, float]:
        if row.get(f"{prefix}mean_spearman") not in (None, ""):
            key = "mean_spearman"
            lo = "mean_spearman_lower_95"
            hi = "mean_spearman_upper_95"
        else:
            key = "subject_equal_mean_spearman"
            lo = "subject_equal_mean_spearman_lower_95"
            hi = "subject_equal_mean_spearman_upper_95"
        return float(row[key]), float(row[lo]), float(row[hi])

    @staticmethod
    def _status(delta: float) -> str:
        if delta > 1e-6:
            return "POSITIVE"
        if delta < -1e-6:
            return "NEGATIVE"
        return "NEAR_ZERO"

    def _paper_rows(self, protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
        references = _mapping(protocol["input_artifacts"], "T284 input artifacts")
        rows: list[dict[str, Any]] = []
        for route_id, evidence_class, filename, reference_name in self.ROUTES:
            path = self._reference(references[reference_name], reference_name)
            source_rows = self._csv(path, reference_name)
            full = next((row for row in source_rows if row.get("model_id") == "SEQUENCE_RIDGE_FULL"), None)
            composition = next(
                (row for row in source_rows if row.get("model_id") == "SEQUENCE_RIDGE_COMPOSITION_ONLY"), None
            )
            if full is None or composition is None:
                raise R4T284PaperOodSynthesisError(f"{route_id} is missing full/composition rows")
            full_metric = self._metric(full)
            composition_metric = self._metric(composition)
            rows.append(
                self._row(
                    route_id,
                    evidence_class,
                    "author_run_paper_ood_analysis_only",
                    full,
                    full_metric,
                    composition_metric,
                    filename,
                )
            )

        t282_path = self._reference(references["t282_primary_outer_metrics"], "t282_primary_outer_metrics")
        t282_rows = self._csv(t282_path, "t282_primary_outer_metrics")
        for fold in sorted({row["outer_fold_id"] for row in t282_rows}):
            fold_rows = [row for row in t282_rows if row["outer_fold_id"] == fold]
            full = next(row for row in fold_rows if row["model_id"] == "SEQUENCE_RIDGE_FULL")
            composition = next(row for row in fold_rows if row["model_id"] == "SEQUENCE_RIDGE_COMPOSITION_ONLY")
            rows.append(
                self._row(
                    fold,
                    "primary_three_lab_holdout",
                    "author_run_primary_route_cross_environment_verified",
                    full,
                    self._metric(full),
                    self._metric(composition),
                    "outer_fold_metrics.csv",
                )
            )
        if len(rows) != 9:
            raise R4T284PaperOodSynthesisError(f"expected 9 route rows, found {len(rows)}")
        return rows

    @staticmethod
    def _row(
        route_id: str,
        evidence_class: str,
        independence_status: str,
        full: Mapping[str, str],
        full_metric: tuple[float, float, float],
        composition_metric: tuple[float, float, float],
        source_filename: str,
    ) -> dict[str, Any]:
        full_value, full_lower, full_upper = full_metric
        composition_value, composition_lower, composition_upper = composition_metric
        return {
            "route_id": route_id,
            "evidence_class": evidence_class,
            "independence_status": independence_status,
            "source_filename": source_filename,
            "observation_count": int(
                full.get("external_observation_count") or full.get("held_out_observation_count") or 0
            ),
            "measurement_batch_count": int(
                full.get("external_measurement_batch_count")
                or full.get("measurement_batch_count")
                or full.get("held_out_measurement_batch_count")
                or 0
            ),
            "biological_unit_count": full.get("biological_unit_count") or "",
            "full_mean_spearman": full_value,
            "full_lower_95": full_lower,
            "full_upper_95": full_upper,
            "composition_mean_spearman": composition_value,
            "composition_lower_95": composition_lower,
            "composition_upper_95": composition_upper,
            "full_minus_composition_spearman": full_value - composition_value,
            "effect_status": R4T284PaperOodSynthesisWorkflow._status(full_value - composition_value),
            "claim_status": "DESCRIPTIVE_EXPLORATORY_ONLY",
        }

    def run(self, *, strict: bool = False) -> R4T284PaperOodSynthesisSummary:
        if not strict:
            raise R4T284PaperOodSynthesisError("T284 execution requires --strict")
        if self.output_root.exists():
            raise R4T284PaperOodSynthesisError("T284 execution already exists")
        protocol_path = self._file(self.PROTOCOL_RELATIVE, "T284 protocol")
        protocol = self._json(protocol_path, "T284 protocol")
        if protocol.get("protocol_id") != self.AUDIT_ID or protocol.get("scientific_submission_ready") is not False:
            raise R4T284PaperOodSynthesisError("T284 protocol identity or claim boundary is invalid")
        rows = self._paper_rows(protocol)
        fields = list(rows[0])
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        effects_path = output / "paper_ood_model_effects.csv"
        self._write_csv(effects_path, fields, rows)
        statuses = Counter(str(row["effect_status"]) for row in rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_sha256": _sha256(protocol_path),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "status": self.STATUS,
            "evidence_class": "AUTHOR_RUN_PAPER_DATA_OOD_SYNTHESIS",
            "route_count": len(rows),
            "positive_effect_count": statuses.get("POSITIVE", 0),
            "negative_effect_count": statuses.get("NEGATIVE", 0),
            "near_zero_effect_count": statuses.get("NEAR_ZERO", 0),
            "effect_minimum": min(float(row["full_minus_composition_spearman"]) for row in rows),
            "effect_maximum": max(float(row["full_minus_composition_spearman"]) for row in rows),
            "pooling_prohibited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "routes": rows,
            "artifacts": {
                "paper_ood_model_effects": {
                    "relative_path": effects_path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(effects_path),
                }
            },
            "claim_boundary": protocol["claim_boundary"],
        }
        report_path = output / "t284_paper_ood_synthesis_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "route_count": len(rows),
            "positive_effect_count": statuses.get("POSITIVE", 0),
            "negative_effect_count": statuses.get("NEGATIVE", 0),
            "near_zero_effect_count": statuses.get("NEAR_ZERO", 0),
            "pooling_prohibited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = output / "t284_paper_ood_synthesis_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T284PaperOodSynthesisSummary(
            len(rows),
            statuses.get("POSITIVE", 0),
            statuses.get("NEGATIVE", 0),
            statuses.get("NEAR_ZERO", 0),
            receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T284PaperOodSynthesisSummary:
        if not strict:
            raise R4T284PaperOodSynthesisError("T284 verification requires --strict")
        report_path = self._file(f"{self.OUTPUT_RELATIVE}/t284_paper_ood_synthesis_report.json", "T284 report")
        receipt_path = self._file(f"{self.OUTPUT_RELATIVE}/t284_paper_ood_synthesis_receipt.json", "T284 receipt")
        report = self._json(report_path, "T284 report")
        receipt = self._json(receipt_path, "T284 receipt")
        artifact = _mapping(
            _mapping(report["artifacts"], "T284 artifacts")["paper_ood_model_effects"], "T284 effects artifact"
        )
        effects_path = self._reference(artifact, "T284 effects artifact")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("route_count") != 9
            or report.get("pooling_prohibited") is not True
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("route_count") != 9
            or receipt.get("scientific_submission_ready") is not False
            or not effects_path.is_file()
        ):
            raise R4T284PaperOodSynthesisError("T284 receipt is invalid")
        return R4T284PaperOodSynthesisSummary(
            int(receipt["route_count"]),
            int(receipt["positive_effect_count"]),
            int(receipt["negative_effect_count"]),
            int(receipt["near_zero_effect_count"]),
            receipt_path,
        )
