"""Audit source- and study-level heterogeneity without refitting frozen models.

T214 turns the T211 editorial requirement for a source-by-model interaction
audit into a deterministic, claim-bounded workflow.  It consumes existing
T195/T197/T198/T203/T209 receipts and does not pool non-independent routes:
T197 is retained as a source-availability sensitivity of the T195 lineage,
not as three additional studies.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4T214SourceHeterogeneityError(RuntimeError):
    """Raised when the T214 source heterogeneity audit cannot close."""


@dataclass(frozen=True)
class R4T214SourceHeterogeneitySummary:
    effect_row_count: int
    primary_effect_unit_count: int
    positive_effect_count: int
    negative_effect_count: int
    receipt_path: Path


class R4T214SourceHeterogeneityWorkflow:
    """Create a descriptive study-level heterogeneity audit from frozen receipts."""

    AUDIT_ID = "bioif-r4-t214-source-heterogeneity-v1.1.0"
    STATUS = "T214_SOURCE_HETEROGENEITY_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T214_SOURCE_HETEROGENEITY_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t214_source_heterogeneity/v1.1.0"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}

    INPUTS = (
        "reports/review_round_4/t195_three_lab_common_target_execution/v1.0.0/paired_composition_ablation.csv",
        "reports/review_round_4/t197_source_availability_execution/v1.0.0/paired_composition_ablation.csv",
        "reports/review_round_4/t198_paper_cohort_missingness/v1.0.0/threshold_paired_ablation.csv",
        "reports/review_round_4/pmc10257194_paper_ood/v1.0.0/r4_external_ood_report.json",
        "reports/review_round_4/manchester_nanoomic_ood/v1.1.0/r4_manchester_nanoomic_ood_report.json",
    )

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T214SourceHeterogeneityError("T214 output must remain under repository root")
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
            value = json.loads(path.read_text(encoding="utf-8"))
            return _mapping(value, label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise R4T214SourceHeterogeneityError(f"cannot parse {label}") from exc

    @staticmethod
    def _csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T214SourceHeterogeneityError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T214SourceHeterogeneityError(f"{label} is empty")
        return rows

    def _file(self, relative: str, label: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T214SourceHeterogeneityError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T214SourceHeterogeneityError(f"{label} is missing")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T214SourceHeterogeneityError(f"{label} reference fields are invalid")
        path = self._file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T214SourceHeterogeneityError(f"{label} checksum differs")
        return path

    @staticmethod
    def _effect_status(value: float, *, tolerance: float = 1e-6) -> str:
        if value > tolerance:
            return "POSITIVE"
        if value < -tolerance:
            return "NEGATIVE"
        return "NEAR_ZERO"

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        return float(value)

    def _fold_rows(self, rows: Sequence[Mapping[str, str]], *, route: str, source_field: str) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for row in rows:
            effect = float(row["full_minus_composition_mean_spearman"])
            output.append(
                {
                    "route": route,
                    "source_id": row[source_field],
                    "source_label": row[source_field],
                    "evidence_class": "DEVELOPMENT_OBSERVATION",
                    "independence_unit": "laboratory_or_source_anchor",
                    "independence_status": "not_independent_biological_cohort",
                    "measurement_batch_count": int(row["paired_measurement_batch_count"]),
                    "biological_unit_count": None,
                    "reported_paper_unit_count": None,
                    "unit_count_semantics": "biological_unit_not_resolved_in_fold_receipt",
                    "effect_full_minus_composition_spearman": effect,
                    "lower_95": float(row["lower_95"]),
                    "upper_95": float(row["upper_95"]),
                    "effect_status": R4T214SourceHeterogeneityWorkflow._effect_status(effect),
                    "claim_status": "DESCRIPTIVE_EXPLORATORY_ONLY",
                }
            )
        return output

    def _paper_row(self, report: Mapping[str, Any], *, route: str, source_id: str, label: str) -> dict[str, Any]:
        paired = _mapping(report["paired_composition_ablation"], f"{route} paired ablation")
        effect_key = (
            "full_minus_composition_patient_equal_mean_spearman"
            if "full_minus_composition_patient_equal_mean_spearman" in paired
            else "full_minus_composition_mean_spearman"
        )
        effect = float(paired[effect_key])
        if "biological_unit_count" in report:
            biological_unit_count = int(report["biological_unit_count"])
            reported_paper_unit_count = None
            unit_count_semantics = "biological_unit_count_explicit_in_receipt"
        elif "external_measurement_batch_count" in report:
            biological_unit_count = None
            reported_paper_unit_count = int(report["external_measurement_batch_count"])
            unit_count_semantics = "paper_reported_measurement_batch_count_not_biological_n"
        else:
            biological_unit_count = None
            reported_paper_unit_count = None
            unit_count_semantics = "paper_unit_count_not_exposed_in_receipt"
        return {
            "route": route,
            "source_id": source_id,
            "source_label": label,
            "evidence_class": report.get("evidence_class"),
            "independence_unit": "paper_cohort_unit",
            "independence_status": "author_run_analysis_only",
            "measurement_batch_count": int(paired["paired_measurement_batch_count"]),
            "biological_unit_count": biological_unit_count,
            "reported_paper_unit_count": reported_paper_unit_count,
            "unit_count_semantics": unit_count_semantics,
            "effect_full_minus_composition_spearman": effect,
            "lower_95": float(paired["lower_95"]),
            "upper_95": float(paired["upper_95"]),
            "effect_status": R4T214SourceHeterogeneityWorkflow._effect_status(effect),
            "claim_status": "DESCRIPTIVE_EXPLORATORY_ONLY",
        }

    @staticmethod
    def _summary(rows: Sequence[Mapping[str, Any]], *, label: str) -> dict[str, Any]:
        effects = [float(row["effect_full_minus_composition_spearman"]) for row in rows]
        batches = [int(row["measurement_batch_count"]) for row in rows]
        weighted = sum(effect * batch for effect, batch in zip(effects, batches, strict=True)) / sum(batches)
        statuses = Counter(str(row["effect_status"]) for row in rows)
        return {
            "label": label,
            "row_count": len(rows),
            "measurement_batch_count_sum": sum(batches),
            "batch_weighted_descriptive_effect": weighted,
            "minimum_effect": min(effects),
            "maximum_effect": max(effects),
            "effect_range": max(effects) - min(effects),
            "effect_status_counts": dict(sorted(statuses.items())),
            "pooling_allowed": False,
            "claim_status": "DESCRIPTIVE_EXPLORATORY_ONLY",
        }

    def _input_references(self, protocol: Mapping[str, Any]) -> dict[str, dict[str, str]]:
        references = _mapping(protocol["input_artifacts"], "T214 input artifacts")
        output: dict[str, dict[str, str]] = {}
        for label, value in references.items():
            output[label] = {
                "relative_path": _string(_mapping(value, label)["relative_path"], label),
                "sha256": _checksum(_mapping(value, label)["sha256"], label),
            }
            self._reference(output[label], label)
        return output

    def run(self, *, strict: bool = False) -> R4T214SourceHeterogeneitySummary:
        if not strict:
            raise R4T214SourceHeterogeneityError("T214 execution requires --strict")
        if self.output_root.exists():
            raise R4T214SourceHeterogeneityError("T214 execution already exists")
        protocol = self._json(self._file(self.PROTOCOL_RELATIVE, "T214 protocol"), "T214 protocol")
        if protocol.get("protocol_id") != self.AUDIT_ID or protocol.get("scientific_submission_ready") is not False:
            raise R4T214SourceHeterogeneityError("T214 protocol identity or claim boundary is invalid")
        input_references = self._input_references(protocol)
        t195 = self._fold_rows(
            self._csv(self._reference(input_references["t195_paired_ablation"], "T195 paired ablation"), "T195 paired ablation"),
            route="T195_common_target_laboratory_holdout",
            source_field="held_out_laboratory_anchor",
        )
        t197 = self._fold_rows(
            self._csv(self._reference(input_references["t197_paired_ablation"], "T197 paired ablation"), "T197 paired ablation"),
            route="T197_source_availability_sensitivity",
            source_field="held_out_source_id",
        )
        t198 = self._csv(self._reference(input_references["t198_threshold_ablation"], "T198 threshold ablation"), "T198 threshold ablation")
        t203_report = self._json(self._reference(input_references["t203_ood_report"], "T203 OOD report"), "T203 OOD report")
        manchester_report = self._json(self._reference(input_references["manchester_ood_report"], "Manchester OOD report"), "Manchester OOD report")
        t203 = [self._paper_row(t203_report, route="T203_paper_cohort_ood", source_id="PMC10257194", label="PMC10257194 paper cohort")]
        manchester = [self._paper_row(manchester_report, route="T209_manchester_paper_cohort_ood", source_id="PMC13212878", label="PMC13212878 Manchester cohort")]
        effects = [*t195, *t197, *t203, *manchester]
        primary = [*t195, *t203, *manchester]
        threshold_rows = [
            {
                "threshold": int(row["threshold"]),
                "qualified_batch_count": int(row["paired_measurement_batch_count"]),
                "effect_full_minus_composition_spearman": float(row["full_minus_composition_batch_mean_spearman"]),
                "lower_95": float(row["lower_95"]),
                "upper_95": float(row["upper_95"]),
                "effect_status": self._effect_status(float(row["full_minus_composition_batch_mean_spearman"])),
                "claim_status": "MISSINGNESS_SENSITIVITY_DESCRIPTIVE_ONLY",
            }
            for row in t198
        ]
        fields = [
            "route", "source_id", "source_label", "evidence_class", "independence_unit", "independence_status",
            "measurement_batch_count", "biological_unit_count", "reported_paper_unit_count", "unit_count_semantics",
            "effect_full_minus_composition_spearman",
            "lower_95", "upper_95", "effect_status", "claim_status",
        ]
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        paths = {
            "study_level_effects": output / "study_level_effects.csv",
            "missingness_threshold_sensitivity": output / "missingness_threshold_sensitivity.csv",
            "heterogeneity_summary": output / "heterogeneity_summary.json",
        }
        self._write_csv(paths["study_level_effects"], fields, effects)
        self._write_csv(paths["missingness_threshold_sensitivity"], list(threshold_rows[0]), threshold_rows)
        statuses = Counter(str(row["effect_status"]) for row in primary)
        summary = {
            "schema_version": 1,
            "primary_effect_unit_count": len(primary),
            "primary_effect_status_counts": dict(sorted(statuses.items())),
            "primary_effect_minimum": min(float(row["effect_full_minus_composition_spearman"]) for row in primary),
            "primary_effect_maximum": max(float(row["effect_full_minus_composition_spearman"]) for row in primary),
            "primary_effect_range": max(float(row["effect_full_minus_composition_spearman"]) for row in primary) - min(float(row["effect_full_minus_composition_spearman"]) for row in primary),
            "route_summaries": [
                self._summary(t195, label="T195_common_target_laboratory_holdout"),
                self._summary(t197, label="T197_source_availability_sensitivity"),
                self._summary(t203, label="T203_paper_cohort_ood"),
                self._summary(manchester, label="T209_manchester_paper_cohort_ood"),
            ],
            "missingness_threshold_count": len(threshold_rows),
            "missingness_effect_minimum": min(float(row["effect_full_minus_composition_spearman"]) for row in threshold_rows),
            "missingness_effect_maximum": max(float(row["effect_full_minus_composition_spearman"]) for row in threshold_rows),
            "pooling_policy": "PROHIBITED_ACROSS_NON_INDEPENDENT_ROUTES",
            "primary_estimand": protocol["primary_estimand"],
            "claim_status": "DESCRIPTIVE_EXPLORATORY_ONLY",
        }
        self._write_json(paths["heterogeneity_summary"], summary)
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(self._file(self.PROTOCOL_RELATIVE, "T214 protocol")),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "status": self.STATUS,
            "evidence_class": "PAPER_DATA_REANALYSIS_AUDIT",
            "allowed_claim_level": "EXPLORATORY",
            "input_references": input_references,
            "artifacts": artifacts,
            "effect_row_count": len(effects),
            "primary_effect_unit_count": len(primary),
            "positive_effect_count": statuses.get("POSITIVE", 0),
            "negative_effect_count": statuses.get("NEGATIVE", 0),
            "pooling_prohibited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        report_path = output / "t214_source_heterogeneity_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "effect_row_count": len(effects),
            "primary_effect_unit_count": len(primary),
            "positive_effect_count": statuses.get("POSITIVE", 0),
            "negative_effect_count": statuses.get("NEGATIVE", 0),
            "pooling_prohibited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = output / "t214_source_heterogeneity_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T214SourceHeterogeneitySummary(len(effects), len(primary), statuses.get("POSITIVE", 0), statuses.get("NEGATIVE", 0), receipt_path)

    def verify(self, *, strict: bool = True) -> R4T214SourceHeterogeneitySummary:
        if not strict:
            raise R4T214SourceHeterogeneityError("T214 verification requires --strict")
        report_path = self._file(f"{self.OUTPUT_RELATIVE}/t214_source_heterogeneity_report.json", "T214 report")
        receipt_path = self._file(f"{self.OUTPUT_RELATIVE}/t214_source_heterogeneity_receipt.json", "T214 receipt")
        report = self._json(report_path, "T214 report")
        receipt = self._json(receipt_path, "T214 receipt")
        artifacts = _mapping(report.get("artifacts"), "T214 artifacts")
        for value in artifacts.values():
            item = _mapping(value, "T214 artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                raise R4T214SourceHeterogeneityError("T214 artifact reference fields are invalid")
            path = self._reference(item, "T214 artifact")
            if not path.is_file():
                raise R4T214SourceHeterogeneityError("T214 artifact is missing")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("pooling_prohibited") is not True
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("pooling_prohibited") is not True
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T214SourceHeterogeneityError("T214 receipt is invalid")
        return R4T214SourceHeterogeneitySummary(
            int(receipt["effect_row_count"]),
            int(receipt["primary_effect_unit_count"]),
            int(receipt["positive_effect_count"]),
            int(receipt["negative_effect_count"]),
            receipt_path,
        )
