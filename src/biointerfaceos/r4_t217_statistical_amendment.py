"""Freeze and audit the project-wide statistical role hierarchy for paper data.

T217 is a reporting amendment, not a model-fitting task.  It makes the
paper-derived routes comparable at the level of denominators and claim
boundaries while preserving the non-exchangeability of the underlying
laboratory/source anchors.  The primary estimand is the already executed
T195 leave-one-anchor-out contrast; T197, T198, T203 and T209 remain explicit
sensitivity or secondary OOD routes.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4T217StatisticalAmendmentError(RuntimeError):
    """Raised when the T217 statistical amendment cannot close."""


@dataclass(frozen=True)
class R4T217StatisticalAmendmentSummary:
    availability_row_count: int
    missingness_row_count: int
    multiplicity_row_count: int
    receipt_path: Path


class R4T217StatisticalAmendmentWorkflow:
    """Audit frozen paper-derived receipts without refitting any model."""

    AUDIT_ID = "bioif-r4-t217-statistical-amendment-v1.0.0"
    STATUS = "T217_STATISTICAL_AMENDMENT_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T217_STATISTICAL_AMENDMENT_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t217_statistical_amendment/v1.0.0"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    TARGET_STATES = (
        "POSITIVE_FINITE",
        "AUTHOR_NA",
        "AUTHOR_EXPLICIT_ZERO",
        "NOT_MAPPED",
        "NOT_SHARED",
    )
    STRATA = ("biological_unit_id", "clinical_group", "particle")

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T217StatisticalAmendmentError("T217 output must remain under repository root")
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
            raise R4T217StatisticalAmendmentError(f"cannot parse {label}") from exc

    @staticmethod
    def _csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T217StatisticalAmendmentError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T217StatisticalAmendmentError(f"{label} is empty")
        return rows

    def _file(self, relative: str, label: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T217StatisticalAmendmentError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T217StatisticalAmendmentError(f"{label} is missing")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T217StatisticalAmendmentError(f"{label} reference fields are invalid")
        path = self._file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T217StatisticalAmendmentError(f"{label} checksum differs")
        return path

    @staticmethod
    def _int(value: Any, label: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise R4T217StatisticalAmendmentError(f"{label} is not an integer") from exc

    @staticmethod
    def _state(row: Mapping[str, str]) -> str:
        state = str(row.get("author_value_state", "")).strip() or "NOT_MAPPED"
        return state if state in R4T217StatisticalAmendmentWorkflow.TARGET_STATES else "NOT_MAPPED"

    @staticmethod
    def _bool(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def _holm(values: Sequence[float]) -> list[float]:
        indexed = sorted(enumerate(values), key=lambda item: item[1])
        adjusted = [0.0] * len(values)
        running = 0.0
        for rank, (index, value) in enumerate(indexed, start=1):
            running = max(running, min(1.0, (len(values) - rank + 1) * value))
            adjusted[index] = running
        return adjusted

    @staticmethod
    def _fraction(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    def _availability_rows(
        self,
        t195: Mapping[str, Any],
        t197: Mapping[str, Any],
        t198_summary: Sequence[Mapping[str, str]],
        t203: Mapping[str, Any],
        t209: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        def add(**values: Any) -> None:
            rows.append(
                {
                    "route": values.get("route"),
                    "role": values.get("role"),
                    "source_id": values.get("source_id"),
                    "outer_fold_id": values.get("outer_fold_id"),
                    "denominator_type": values.get("denominator_type"),
                    "candidate_count": values.get("candidate_count"),
                    "retained_count": values.get("retained_count"),
                    "retention_fraction": values.get("retention_fraction"),
                    "candidate_observation_count": values.get("candidate_observation_count"),
                    "retained_observation_count": values.get("retained_observation_count"),
                    "candidate_measurement_batch_count": values.get("candidate_measurement_batch_count"),
                    "retained_measurement_batch_count": values.get("retained_measurement_batch_count"),
                    "candidate_biological_unit_count": values.get("candidate_biological_unit_count"),
                    "retained_biological_unit_count": values.get("retained_biological_unit_count"),
                    "reported_paper_unit_count": values.get("reported_paper_unit_count"),
                    "exclusion_reason": values.get("exclusion_reason"),
                    "evidence_class": values.get("evidence_class"),
                    "independence_status": values.get("independence_status"),
                    "claim_status": values.get("claim_status"),
                }
            )

        target_count = self._int(t195["target_universe"]["count"], "T195 target count")
        for source_id, meta in sorted(_mapping(t195["source_accounting"], "T195 source accounting").items()):
            source = _mapping(meta, f"T195 source accounting {source_id}")
            observations = self._int(source["observation_count"], f"T195 observations {source_id}")
            batches = self._int(source["measurement_batch_count"], f"T195 batches {source_id}")
            add(
                route="T195",
                role="PRIMARY_ESTIMAND_EXECUTION",
                source_id=source_id,
                denominator_type="pre_frozen_common_target_set",
                candidate_count=target_count,
                retained_count=target_count,
                retention_fraction=1.0,
                candidate_observation_count=observations,
                retained_observation_count=observations,
                candidate_measurement_batch_count=batches,
                retained_measurement_batch_count=batches,
                exclusion_reason="none; exact nine-accession intersection retained",
                evidence_class="DEVELOPMENT_OBSERVATION",
                independence_status="laboratory_or_source_anchor_not_independent_biological_cohort",
                claim_status="EXPLORATORY_PORTABILITY_SENSITIVITY",
            )

        for fold in sorted(t197.get("fold_targets", []), key=lambda item: str(item.get("outer_fold_id"))):
            item = _mapping(fold, "T197 fold target row")
            candidate = self._int(item["development_only_target_count"], "T197 candidate targets")
            retained = self._int(item["test_available_target_count"], "T197 retained targets")
            observations = self._int(item["test_observation_count"], "T197 observations")
            batches = self._int(item["test_measurement_batch_count"], "T197 batches")
            add(
                route="T197",
                role="SECONDARY_SOURCE_AVAILABILITY_SENSITIVITY",
                source_id=item["held_out_source_id"],
                outer_fold_id=item["outer_fold_id"],
                denominator_type="development_target_set_to_held_out_available_target_set",
                candidate_count=candidate,
                retained_count=retained,
                retention_fraction=self._fraction(retained, candidate),
                candidate_observation_count=None,
                retained_observation_count=observations,
                candidate_measurement_batch_count=None,
                retained_measurement_batch_count=batches,
                exclusion_reason=f"{candidate - retained} development-only targets unavailable in held-out source",
                evidence_class="DEVELOPMENT_OBSERVATION",
                independence_status="same_three_source_lineage_as_T195",
                claim_status="DESCRIPTIVE_ONLY",
            )

        candidate_batches = None
        candidate_units = None
        for summary in t198_summary:
            threshold = self._int(summary["minimum_mapped_positive_proteins_per_batch"], "T198 threshold")
            if candidate_batches is None:
                candidate_batches = self._int(
                    summary["all_source_map_measurement_batch_count"], "T198 candidate batches"
                )
                candidate_units = self._int(summary["biological_unit_count"], "T198 candidate units")
            retained_batches = self._int(summary["measurement_batch_count"], "T198 retained batches")
            retained_units = self._int(summary["biological_unit_count"], "T198 retained units")
            add(
                route="T198",
                role="SECONDARY_MISSINGNESS_AND_QUALIFICATION_SENSITIVITY",
                source_id="PXD017052_NSCLC_PAPER_COHORT",
                denominator_type=f"source_map_measurement_batches_threshold_{threshold}",
                candidate_count=candidate_batches,
                retained_count=retained_batches,
                retention_fraction=self._fraction(retained_batches, candidate_batches),
                candidate_observation_count=None,
                retained_observation_count=self._int(summary["external_observation_count"], "T198 observations"),
                candidate_measurement_batch_count=candidate_batches,
                retained_measurement_batch_count=retained_batches,
                candidate_biological_unit_count=candidate_units,
                retained_biological_unit_count=retained_units,
                exclusion_reason=f"batches below {threshold} mapped-positive qualification threshold",
                evidence_class="DEVELOPMENT_OBSERVATION",
                independence_status="single_paper_attached_cohort",
                claim_status="DESCRIPTIVE_ONLY",
            )

        for route, report, label in (
            ("T203", t203, "PMC10257194_PAPER_COHORT"),
            ("T209", t209, "MANCHESTER_NANOOMIC_PAPER_COHORT"),
        ):
            candidate = self._int(report["development_canonical_protein_count"], f"{route} development proteins")
            retained = self._int(report["external_shared_canonical_protein_count"], f"{route} shared proteins")
            batches = self._int(report["external_measurement_batch_count"], f"{route} batches")
            observations = self._int(report["external_observation_count"], f"{route} observations")
            biological = report.get("biological_unit_count")
            add(
                route=route,
                role="SECONDARY_AUTHOR_RUN_PAPER_DATA_OOD",
                source_id=label,
                denominator_type="development_canonical_targets_to_external_shared_targets",
                candidate_count=candidate,
                retained_count=retained,
                retention_fraction=self._fraction(retained, candidate),
                candidate_observation_count=None,
                retained_observation_count=observations,
                candidate_measurement_batch_count=None,
                retained_measurement_batch_count=batches,
                candidate_biological_unit_count=None,
                retained_biological_unit_count=(
                    self._int(biological, f"{route} biological units") if biological is not None else None
                ),
                reported_paper_unit_count=(batches if route == "T203" else None),
                exclusion_reason=f"{candidate - retained} development proteins not shared by the paper-derived OOD route",  # noqa: E501
                evidence_class=str(report.get("evidence_class", "DEVELOPMENT_OBSERVATION")),
                independence_status="author_run_analysis_only;not_independent_external_validation",
                claim_status="ANALYSIS_ONLY_EXPLORATORY",
            )
        return rows

    def _missingness_rows(
        self,
        source_rows: Sequence[Mapping[str, str]],
        threshold_summary: Sequence[Mapping[str, str]],
    ) -> list[dict[str, Any]]:
        threshold = 10
        primary_summary = next(
            (
                row
                for row in threshold_summary
                if self._int(row["minimum_mapped_positive_proteins_per_batch"], "T198 threshold") == threshold
            ),
            None,
        )
        if primary_summary is None:
            raise R4T217StatisticalAmendmentError("T198 primary threshold 10 is missing")
        groups: list[tuple[str, str, list[Mapping[str, str]]]] = [("overall", "ALL", list(source_rows))]
        for dimension in self.STRATA:
            values = sorted({str(row.get(dimension, "")) for row in source_rows})
            for value in values:
                groups.append(
                    (
                        dimension,
                        value,
                        [row for row in source_rows if str(row.get(dimension, "")) == value],
                    )
                )

        rows: list[dict[str, Any]] = []
        for dimension, stratum, selected in groups:
            states = Counter(self._state(row) for row in selected)
            batches: dict[str, list[Mapping[str, str]]] = defaultdict(list)
            for row in selected:
                batches[str(row.get("measurement_batch_id", ""))].append(row)
            qualified = [
                batch_rows
                for batch_rows in batches.values()
                if sum(self._state(row) == "POSITIVE_FINITE" for row in batch_rows) >= threshold
            ]
            all_units = {str(row.get("biological_unit_id", "")) for row in selected}
            qualified_units = {str(row.get("biological_unit_id", "")) for batch_rows in qualified for row in batch_rows}
            row_count = len(selected)
            rows.append(
                {
                    "dimension": dimension,
                    "stratum": stratum,
                    "qualification_threshold": threshold,
                    "source_row_count": row_count,
                    "positive_finite_row_count": states["POSITIVE_FINITE"],
                    "author_na_row_count": states["AUTHOR_NA"],
                    "explicit_zero_row_count": states["AUTHOR_EXPLICIT_ZERO"],
                    "not_mapped_row_count": states["NOT_MAPPED"],
                    "not_shared_row_count": states["NOT_SHARED"],
                    "na_fraction": self._fraction(states["AUTHOR_NA"], row_count),
                    "candidate_measurement_batch_count": len(batches),
                    "retained_measurement_batch_count_at_primary_threshold": len(qualified),
                    "batch_retention_fraction_at_primary_threshold": self._fraction(len(qualified), len(batches)),
                    "candidate_biological_unit_count": len(all_units),
                    "retained_biological_unit_count_at_primary_threshold": len(qualified_units),
                    "imputation": "NONE",
                    "missingness_assumption": "NONE_CLAIMED",
                    "selection_bias_status": "POTENTIALLY_INFORMATIVE_SOURCE_AVAILABILITY",
                    "claim_status": "DESCRIPTIVE_DENOMINATOR_AUDIT_ONLY",
                }
            )
        overall = rows[0]
        expected_batches = self._int(primary_summary["measurement_batch_count"], "T198 primary retained batches")
        expected_units = self._int(primary_summary["biological_unit_count"], "T198 primary retained units")
        if (
            overall["retained_measurement_batch_count_at_primary_threshold"] != expected_batches
            or overall["retained_biological_unit_count_at_primary_threshold"] != expected_units
        ):
            raise R4T217StatisticalAmendmentError("T217 missingness flow disagrees with T198 primary threshold summary")
        return rows

    def _multiplicity_rows(
        self,
        protocol: Mapping[str, Any],
        t197: Mapping[str, Any],
        t198_summary: Sequence[Mapping[str, str]],
        t203: Mapping[str, Any],
        t209: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [
            {
                "family_id": "T217_PRIMARY_EFFECT_AND_INTERVAL",
                "route": "T195",
                "hypothesis_id": "T195_full_minus_composition_effect_vector",
                "endpoint_count": 1,
                "raw_p": None,
                "holm_adjusted_p": None,
                "p_value_status": "NOT_ESTIMATED",
                "adjustment": "NONE",
                "claim_status": "EFFECT_SIZE_AND_CLUSTER_INTERVAL_ONLY",
            }
        ]
        negative = [
            row for row in t197.get("negative_control_summary", []) if row.get("one_sided_upper_tail_p") is not None
        ]
        raw = [float(row["one_sided_upper_tail_p"]) for row in negative]
        adjusted = self._holm(raw)
        for index, item in enumerate(negative):
            rows.append(
                {
                    "family_id": "T197_WITHIN_BATCH_NEGATIVE_CONTROL",
                    "route": "T197",
                    "hypothesis_id": f"{item['outer_fold_id']}_negative_control",
                    "endpoint_count": len(negative),
                    "raw_p": raw[index],
                    "holm_adjusted_p": adjusted[index],
                    "p_value_status": "HOLM_ADJUSTED_QC_ONLY",
                    "adjustment": "Holm step-down across three T197 outer-fold QC p-values",
                    "claim_status": "QC_CALIBRATION_ONLY_NOT_SCIENTIFIC_EFFECT",
                }
            )
        secondary = (
            ("T197", "T197_source_availability_route", "SECONDARY_SOURCE_AVAILABILITY_SENSITIVITY"),
            ("T198", "T198_threshold_10_and_grid", "SECONDARY_MISSINGNESS_SENSITIVITY"),
            ("T203", "T203_paper_data_OOD", "SECONDARY_AUTHOR_RUN_PAPER_DATA_OOD"),
            ("T209", "T209_paper_data_OOD", "SECONDARY_AUTHOR_RUN_PAPER_DATA_OOD"),
        )
        for route, hypothesis, claim in secondary:
            rows.append(
                {
                    "family_id": "T217_SECONDARY_DESCRIPTIVE_ROUTES",
                    "route": route,
                    "hypothesis_id": hypothesis,
                    "endpoint_count": 0,
                    "raw_p": None,
                    "holm_adjusted_p": None,
                    "p_value_status": "PROHIBITED",
                    "adjustment": "NO_INFERENTIAL_P_VALUES",
                    "claim_status": claim,
                }
            )
        if len(negative) != 3 or len(t198_summary) != 8 or not t203 or not t209:
            raise R4T217StatisticalAmendmentError("T217 multiplicity ledger did not observe the frozen route inventory")
        return rows

    @staticmethod
    def _execution_rows(protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in protocol["route_roles"]:
            route = _mapping(item, "T217 route role")
            route_name = str(route["route"])
            rows.append(
                {
                    "route": route_name,
                    "role": route["role"],
                    "study_held_out": bool(route["study_held_out"]),
                    "nested_selection": bool(route["nested_selection"]),
                    "cluster_aware": bool(route["cluster_aware"]),
                    "external_data_used_for_selection": "NO_UNAUTHORIZED_EXTERNAL_SELECTION",
                    "biological_independence_status": "UNRESOLVED"
                    if route_name
                    in {
                        "T195_common_target_laboratory_holdout",
                        "T197_source_availability_sensitivity",
                    }
                    else "NOT_A_VALIDATED_EXTERNAL_COHORT",
                    "selection_status": "FROZEN_OR_ROUTE_LOCAL_AS_SPECIFIED",
                    "claim_status": route["claim_status"],
                    "independent_validation": False,
                    "external_scientific_reproduction": False,
                }
            )
        return rows

    def run(self, *, strict: bool = False) -> R4T217StatisticalAmendmentSummary:
        if not strict:
            raise R4T217StatisticalAmendmentError("T217 execution requires --strict")
        if self.output_root.exists():
            raise R4T217StatisticalAmendmentError("T217 execution already exists")
        protocol_path = self._file(self.PROTOCOL_RELATIVE, "T217 protocol")
        protocol = self._json(protocol_path, "T217 protocol")
        if protocol.get("protocol_id") != self.AUDIT_ID or protocol.get("scientific_submission_ready") is not False:
            raise R4T217StatisticalAmendmentError("T217 protocol identity or claim boundary is invalid")
        input_paths = {
            name: self._reference(value, f"T217 input {name}")
            for name, value in _mapping(protocol["input_artifacts"], "T217 input artifacts").items()
        }
        t195 = self._json(input_paths["t195_report"], "T195 report")
        t197 = self._json(input_paths["t197_report"], "T197 report")
        self._json(input_paths["t198_report"], "T198 report")
        t203 = self._json(input_paths["t203_ood_report"], "T203 report")
        t209 = self._json(input_paths["t209_ood_report"], "T209 report")
        t198_summary = self._csv(input_paths["t198_threshold_summary"], "T198 threshold summary")
        source_rows = self._csv(input_paths["t198_source_map"], "T198 source map")

        availability = self._availability_rows(t195, t197, t198_summary, t203, t209)
        missingness = self._missingness_rows(source_rows, t198_summary)
        multiplicity = self._multiplicity_rows(protocol, t197, t198_summary, t203, t209)
        execution = self._execution_rows(protocol)
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        fields = list(availability[0])
        paths = {
            "primary_estimand_contract": output / "primary_estimand_contract.json",
            "availability_flow": output / "availability_flow.csv",
            "missingness_flow": output / "missingness_flow.csv",
            "multiplicity_ledger": output / "multiplicity_ledger.csv",
            "execution_evidence": output / "execution_evidence.csv",
        }
        self._write_json(
            paths["primary_estimand_contract"],
            {
                "primary_estimand": protocol["primary_estimand"],
                "route_roles": protocol["route_roles"],
                "availability_policy": protocol["availability_policy"],
                "missingness_policy": protocol["missingness_policy"],
                "multiplicity_policy": protocol["multiplicity_policy"],
                "effective_n_policy": protocol["effective_n_policy"],
            },
        )
        self._write_csv(paths["availability_flow"], fields, availability)
        self._write_csv(paths["missingness_flow"], list(missingness[0]), missingness)
        self._write_csv(paths["multiplicity_ledger"], list(multiplicity[0]), multiplicity)
        self._write_csv(paths["execution_evidence"], list(execution[0]), execution)
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
        }
        input_references = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in input_paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(protocol_path),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "status": self.STATUS,
            "evidence_class": "PAPER_DATA_REANALYSIS_AUDIT",
            "allowed_claim_level": "EXPLORATORY",
            "input_references": input_references,
            "availability_row_count": len(availability),
            "missingness_row_count": len(missingness),
            "multiplicity_row_count": len(multiplicity),
            "primary_estimand_frozen": True,
            "availability_denominators_audited": True,
            "missingness_policy_frozen": True,
            "project_multiplicity_ledger_frozen": True,
            "artifacts": artifacts,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "protected_lockbox_evaluator_receipt": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "doi_archived": False,
            "scientific_submission_ready": False,
        }
        report_path = output / "t217_statistical_amendment_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "availability_row_count": len(availability),
            "missingness_row_count": len(missingness),
            "multiplicity_row_count": len(multiplicity),
            "primary_estimand_frozen": True,
            "availability_denominators_audited": True,
            "missingness_policy_frozen": True,
            "project_multiplicity_ledger_frozen": True,
            "independent_validation": False,
            "protected_lockbox_evaluator_receipt": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "doi_archived": False,
            "scientific_submission_ready": False,
        }
        receipt_path = output / "t217_statistical_amendment_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T217StatisticalAmendmentSummary(len(availability), len(missingness), len(multiplicity), receipt_path)

    def verify(self, *, strict: bool = True) -> R4T217StatisticalAmendmentSummary:
        if not strict:
            raise R4T217StatisticalAmendmentError("T217 verification requires --strict")
        protocol_path = self._file(self.PROTOCOL_RELATIVE, "T217 protocol")
        protocol = self._json(protocol_path, "T217 protocol")
        if protocol.get("protocol_id") != self.AUDIT_ID:
            raise R4T217StatisticalAmendmentError("T217 protocol identity is invalid")
        for name, value in _mapping(protocol["input_artifacts"], "T217 input artifacts").items():
            self._reference(value, f"T217 input {name}")
        report_path = self._file(f"{self.OUTPUT_RELATIVE}/t217_statistical_amendment_report.json", "T217 report")
        receipt_path = self._file(f"{self.OUTPUT_RELATIVE}/t217_statistical_amendment_receipt.json", "T217 receipt")
        report = self._json(report_path, "T217 report")
        receipt = self._json(receipt_path, "T217 receipt")
        if report.get("artifacts") is None:
            raise R4T217StatisticalAmendmentError("T217 artifacts are missing")
        for name, value in _mapping(report["artifacts"], "T217 artifacts").items():
            self._reference(value, f"T217 artifact {name}")
        expected_flags = {
            "primary_estimand_frozen": True,
            "availability_denominators_audited": True,
            "missingness_policy_frozen": True,
            "project_multiplicity_ledger_frozen": True,
            "independent_validation": False,
            "protected_lockbox_evaluator_receipt": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "doi_archived": False,
            "scientific_submission_ready": False,
        }
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("protocol_sha256") != _sha256(protocol_path)
            or _sha256(report_path) != receipt.get("report_sha256")
        ):
            raise R4T217StatisticalAmendmentError("T217 report or receipt identity is invalid")
        if any(report.get(key) != value or receipt.get(key) != value for key, value in expected_flags.items()):
            raise R4T217StatisticalAmendmentError("T217 claim-boundary flags are invalid")
        availability_path = self._file(f"{self.OUTPUT_RELATIVE}/availability_flow.csv", "T217 availability flow")
        missingness_path = self._file(f"{self.OUTPUT_RELATIVE}/missingness_flow.csv", "T217 missingness flow")
        multiplicity_path = self._file(f"{self.OUTPUT_RELATIVE}/multiplicity_ledger.csv", "T217 multiplicity ledger")
        availability = self._csv(availability_path, "T217 availability flow")
        missingness = self._csv(missingness_path, "T217 missingness flow")
        multiplicity = self._csv(multiplicity_path, "T217 multiplicity ledger")
        if (
            len(availability) != int(report["availability_row_count"])
            or len(missingness) != int(report["missingness_row_count"])
            or len(multiplicity) != int(report["multiplicity_row_count"])
        ):
            raise R4T217StatisticalAmendmentError("T217 row counts do not match report")
        primary = [row for row in availability if row.get("route") == "T195"]
        if len(primary) != 3 or any(
            row.get("candidate_count") != "9" or row.get("retained_count") != "9" for row in primary
        ):
            raise R4T217StatisticalAmendmentError("T217 primary availability denominator is invalid")
        if not any(
            row.get("dimension") == "overall" and row.get("author_na_row_count") == "6640" for row in missingness
        ):
            raise R4T217StatisticalAmendmentError("T217 overall missingness row is invalid")
        if sum(row.get("family_id") == "T197_WITHIN_BATCH_NEGATIVE_CONTROL" for row in multiplicity) != 3:
            raise R4T217StatisticalAmendmentError("T217 QC multiplicity family is invalid")
        return R4T217StatisticalAmendmentSummary(len(availability), len(missingness), len(multiplicity), receipt_path)
