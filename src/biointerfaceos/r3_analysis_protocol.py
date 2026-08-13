"""Freeze the R3 study-held-out analysis protocol before model execution."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R3AnalysisProtocolError(RuntimeError):
    """Raised when an R3 protocol fails to predeclare its execution boundary."""


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise R3AnalysisProtocolError(f"{label} must contain at least {minimum} items")
    return value


@dataclass(frozen=True)
class R3AnalysisProtocolSummary:
    """Compact accounting for a frozen R3 analysis protocol and partitions."""

    eligible_observation_count: int
    canonical_protein_count: int
    laboratory_anchor_count: int
    measurement_batch_count: int
    outer_fold_count: int
    receipt_path: Path


class R3AnalysisProtocolWorkflow:
    """Freeze target, feature and split identities while remaining outcome-blind."""

    PLAN_ID = "bioif-r3-common-rank-analysis-plan-v1.0.0"
    PLAN_RELATIVE = "docs/data/R3_T151_ANALYSIS_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_3/analysis_protocol/v1.0.0"
    REQUIRED_PLAN = {
        "schema_version", "plan_id", "frozen_at", "evidence_class", "allowed_claim_level",
        "references", "target", "independent_units", "outer_evaluation", "inner_selection",
        "feature_policy", "models", "metrics", "missingness", "uncertainty", "negative_controls",
        "multiplicity", "prohibited_actions", "claim_boundary",
    }
    REQUIRED_REFERENCES = {
        "common_target_receipt", "common_target_ledger", "sequence_feature_receipt", "sequence_feature_table",
    }
    REQUIRED_REFERENCE = {"relative_path", "sha256"}

    def __init__(
        self,
        root: Path,
        output_data_root: Path,
        *,
        plan_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.output_data_root = output_data_root.resolve(strict=False)
        self.plan_path = plan_path or self.root / self.PLAN_RELATIVE
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
            raise R3AnalysisProtocolError(f"cannot parse {label}") from exc
        try:
            return _mapping(value, label)
        except Exception as exc:
            raise R3AnalysisProtocolError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R3AnalysisProtocolError(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R3AnalysisProtocolError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R3AnalysisProtocolError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R3AnalysisProtocolError(f"{label} fields are invalid")
        path = self._root_file(_string(reference.get("relative_path"), label), label)
        try:
            expected_hash = _checksum(reference.get("sha256"), label)
        except Exception as exc:
            raise R3AnalysisProtocolError(f"{label} checksum is invalid") from exc
        if _sha256(path) != expected_hash:
            raise R3AnalysisProtocolError(f"{label} checksum differs")
        return path

    @staticmethod
    def _exact(value: Any, expected: Any, label: str) -> None:
        if value != expected:
            raise R3AnalysisProtocolError(f"{label} is not frozen as required")

    def _validate_plan(self) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
        plan = self._json(self.plan_path, "R3 analysis protocol")
        if set(plan) != self.REQUIRED_PLAN or plan.get("schema_version") != 1:
            raise R3AnalysisProtocolError("R3 analysis protocol fields are invalid")
        if (
            plan.get("plan_id") != self.PLAN_ID
            or plan.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or plan.get("allowed_claim_level") != "EXPLORATORY"
            or not _string(plan.get("frozen_at"), "R3 analysis protocol frozen_at")
        ):
            raise R3AnalysisProtocolError("R3 analysis protocol identity is invalid")
        references = _mapping(plan.get("references"), "R3 analysis protocol references")
        if set(references) != self.REQUIRED_REFERENCES:
            raise R3AnalysisProtocolError("R3 analysis protocol reference fields are invalid")
        target_receipt_path = self._reference(references["common_target_receipt"], "common target receipt")
        target_receipt = self._json(target_receipt_path, "common target receipt")
        if (
            target_receipt.get("audit_id") != "bioif-r3-common-rank-target-v1.0.0"
            or target_receipt.get("status") != "ADMITTED_COMMON_RANK_TARGET_PROTOCOL_AMENDMENT_REQUIRED"
            or target_receipt.get("target_status") != "NOT_FROZEN_PROTOCOL_AMENDMENT_REQUIRED"
            or target_receipt.get("model_fitted") is not False
        ):
            raise R3AnalysisProtocolError("common target receipt is not eligible for freezing")
        ledger_path = self._reference(references["common_target_ledger"], "common target ledger")
        sequence_receipt_path = self._reference(references["sequence_feature_receipt"], "sequence feature receipt")
        sequence_receipt = self._json(sequence_receipt_path, "sequence feature receipt")
        if (
            sequence_receipt.get("audit_id") != "bioif-r3-uniprot-sequence-features-v1.0.0"
            or sequence_receipt.get("status") != "R3_SEQUENCE_FEATURES_READY_FOR_PROTOCOL_FREEZE"
            or sequence_receipt.get("model_fitted") is not False
        ):
            raise R3AnalysisProtocolError("sequence feature receipt is not eligible for freezing")
        feature_path = self._reference(references["sequence_feature_table"], "sequence feature table")
        with ledger_path.open("r", encoding="utf-8", newline="") as stream:
            ledger = list(csv.DictReader(stream))
        required_ledger = {
            "target_observation_id", "source_id", "canonical_accession", "laboratory_anchor",
            "measurement_batch_id", "rank_percentile_descending", "rank_target_eligible", "common_rank_target_member",
        }
        if not ledger or not required_ledger.issubset(ledger[0]):
            raise R3AnalysisProtocolError("common target ledger schema is invalid")
        eligible = [
            row for row in ledger
            if row["rank_target_eligible"] == "true" and row["common_rank_target_member"] == "true"
        ]
        if len(eligible) != target_receipt.get("eligible_rank_observation_count"):
            raise R3AnalysisProtocolError("common target ledger count differs from receipt")
        if any(not row["rank_percentile_descending"] for row in eligible):
            raise R3AnalysisProtocolError("eligible common target row lacks a rank")
        accessions = {row["canonical_accession"] for row in eligible}
        labs = {row["laboratory_anchor"] for row in eligible}
        batches = {row["measurement_batch_id"] for row in eligible}
        if (
            len(accessions) != target_receipt.get("rank_eligible_shared_canonical_protein_count")
            or len(labs) != target_receipt.get("laboratory_anchor_count")
            or len(batches) != target_receipt.get("measurement_batch_count")
            or len(labs) != 3
        ):
            raise R3AnalysisProtocolError("common target ledger effective sample accounting is invalid")
        with feature_path.open("r", encoding="utf-8", newline="") as stream:
            features = list(csv.DictReader(stream))
        if not features or "canonical_accession" not in features[0]:
            raise R3AnalysisProtocolError("sequence feature table schema is invalid")
        if {row["canonical_accession"] for row in features} != accessions:
            raise R3AnalysisProtocolError("sequence feature table does not close common target proteins")

        self._exact(
            plan["target"],
            {
                "target_id": "R3_WITHIN_MEASUREMENT_BATCH_POSITIVE_QUANTIFICATION_RANK_PERCENTILE",
                "analysis_population": "rows with rank_target_eligible=true and common_rank_target_member=true",
                "outcome_range": "[0,1] descending midrank percentile",
                "cross_study_raw_scale": "PROHIBITED",
            },
            "R3 target",
        )
        self._exact(
            plan["independent_units"],
            {
                "prediction_row": "protein-by-source-defined measurement batch",
                "outer_group_key": "laboratory_anchor",
                "inner_group_key": "measurement_batch_id",
                "uncertainty_cluster_key": "measurement_batch_id",
                "nesting_order": ["laboratory_anchor", "source_id", "measurement_batch_id", "canonical_accession"],
            },
            "R3 independent units",
        )
        self._exact(
            plan["outer_evaluation"],
            {
                "outer_split": "LEAVE_ONE_LABORATORY_ANCHOR_OUT",
                "outer_fold_count": 3,
                "predeclared_external_ood_lab_anchor": "University of Oklahoma Health Sciences Center",
                "held_out_access_before_selection": "PROHIBITED",
                "primary_aggregation": "equal-weight mean of measurement-batch metrics within each held-out laboratory anchor",
            },
            "R3 outer evaluation",
        )
        self._exact(
            plan["inner_selection"],
            {
                "method": "LEAVE_ONE_MEASUREMENT_BATCH_OUT_NESTED_SELECTION",
                "tuning_metric": "mean measurement-batch Spearman correlation",
                "selection_scope": "development laboratories only",
                "tie_breaker": "smaller regularization then lexical model identifier",
            },
            "R3 inner selection",
        )
        self._exact(
            plan["feature_policy"],
            {
                "allowed_feature_set": "R3_UNIPROT_SEQUENCE_COMPOSITION_PHYSICOCHEMICAL_V1",
                "feature_standardization": "fit mean and standard deviation on each inner-training partition only",
                "identity_or_provenance_feature": "PROHIBITED",
                "held_out_quantification_or_rank_feature": "PROHIBITED",
            },
            "R3 feature policy",
        )
        expected_models = [
            {"model_id": "CONSTANT_TRAINING_MEAN", "role": "non-learned baseline", "hyperparameters": {}},
            {"model_id": "SEQUENCE_RIDGE_FULL", "role": "primary sequence model", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
            {"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", "role": "paired feature ablation", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
        ]
        self._exact(plan["models"], expected_models, "R3 models")
        self._exact(
            plan["metrics"],
            {
                "primary": "mean measurement-batch Spearman correlation",
                "secondary": ["mean measurement-batch mean absolute error", "mean measurement-batch root mean square error"],
                "minimum_proteins_per_metric_batch": 10,
                "report_each_held_out_laboratory_anchor": True,
            },
            "R3 metrics",
        )
        self._exact(
            plan["missingness"],
            {
                "positive_quantification": "rank eligible",
                "author_explicit_zero": "retain and exclude from rank target; never impute",
                "source_blank": "retain and exclude from rank target; never impute",
                "author_na": "retain and exclude from rank target; never impute",
                "omitted_protein_row": "not a negative label",
            },
            "R3 missingness",
        )
        self._exact(
            plan["uncertainty"],
            {
                "method": "held-out-laboratory measurement-batch cluster bootstrap percentile interval",
                "resamples": 2000,
                "random_seed": 20260813,
                "reporting": "report fold-specific point estimates and 95% intervals; do not treat three laboratory anchors as a large-sample confirmatory population",
            },
            "R3 uncertainty",
        )
        self._exact(
            plan["negative_controls"],
            {
                "within_batch_rank_permutation": {"resamples": 256, "random_seed": 20260814, "comparison": "SEQUENCE_RIDGE_FULL primary metric"},
                "provenance_feature_leakage": "static feature-manifest rejection; no source identity model is fit",
            },
            "R3 negative controls",
        )
        self._exact(
            plan["multiplicity"],
            {"family": "three outer folds by three predeclared models for primary metric comparisons", "method": "Holm step-down", "claim_status": "exploratory"},
            "R3 multiplicity",
        )
        prohibited = {
            "use source, laboratory, facility, paper, worksheet, path, cell coordinate or protein identity as a predictive feature",
            "fit or select against any held-out laboratory anchor before its outer-fold evaluation",
            "concatenate raw LFQ, intensity, PSM, spectral-count or normalized-abundance scales across studies",
            "impute zero, blank, NA or omitted protein records as a target rank",
            "claim material-property prediction, clinical utility, causal mechanism or independent external reproduction from this benchmark alone",
        }
        if set(_list(plan.get("prohibited_actions"), "R3 prohibited actions", minimum=5)) != prohibited:
            raise R3AnalysisProtocolError("R3 prohibited-action boundary is invalid")
        _string(plan.get("claim_boundary"), "R3 claim boundary")
        return plan, eligible, features

    def run(self, *, strict: bool = False) -> R3AnalysisProtocolSummary:
        if not strict:
            raise R3AnalysisProtocolError("R3 analysis protocol requires --strict")
        if self.output_root.exists():
            raise R3AnalysisProtocolError("R3 analysis protocol already frozen")
        plan, eligible, features = self._validate_plan()
        labs = sorted({row["laboratory_anchor"] for row in eligible})
        batches = {row["measurement_batch_id"] for row in eligible}
        split_rows: list[dict[str, str]] = []
        for fold_index, held_out_lab in enumerate(labs, start=1):
            for row in eligible:
                split_rows.append(
                    {
                        "outer_fold_id": f"R3-OUTER-{fold_index:02d}",
                        "held_out_laboratory_anchor": held_out_lab,
                        "target_observation_id": row["target_observation_id"],
                        "source_id": row["source_id"],
                        "laboratory_anchor": row["laboratory_anchor"],
                        "measurement_batch_id": row["measurement_batch_id"],
                        "split_role": "TEST" if row["laboratory_anchor"] == held_out_lab else "DEVELOPMENT",
                    }
                )
        if len(split_rows) != len(eligible) * len(labs):
            raise R3AnalysisProtocolError("R3 split manifest accounting is invalid")
        self.output_root.mkdir(parents=True, exist_ok=False)
        frozen_plan_path = self.output_root / "frozen_analysis_protocol.json"
        self._write(frozen_plan_path, plan)
        split_path = self.output_root / "frozen_outer_split_manifest.csv"
        with split_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(split_rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(split_rows)
        receipt = {
            "schema_version": 1,
            "plan_id": self.PLAN_ID,
            "frozen_at": plan["frozen_at"],
            "status": "FROZEN_R3_COMMON_RANK_ANALYSIS_PROTOCOL",
            "plan_sha256": _sha256(frozen_plan_path),
            "outer_split_manifest_sha256": _sha256(split_path),
            "eligible_observation_count": len(eligible),
            "canonical_protein_count": len({row["canonical_accession"] for row in eligible}),
            "laboratory_anchor_count": len(labs),
            "measurement_batch_count": len(batches),
            "outer_fold_count": len(labs),
            "target_status": "FROZEN_R3_RANK_BENCHMARK",
            "outcome_analysis_run": False,
            "model_fitted": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "analysis_protocol_receipt.json"
        self._write(receipt_path, receipt)
        return R3AnalysisProtocolSummary(
            eligible_observation_count=len(eligible),
            canonical_protein_count=len({row["canonical_accession"] for row in eligible}),
            laboratory_anchor_count=len(labs),
            measurement_batch_count=len(batches),
            outer_fold_count=len(labs),
            receipt_path=receipt_path,
        )

    def verify(self) -> R3AnalysisProtocolSummary:
        plan_path = self.output_root / "frozen_analysis_protocol.json"
        split_path = self.output_root / "frozen_outer_split_manifest.csv"
        receipt_path = self.output_root / "analysis_protocol_receipt.json"
        receipt = self._json(receipt_path, "R3 analysis protocol receipt")
        if (
            receipt.get("plan_id") != self.PLAN_ID
            or receipt.get("status") != "FROZEN_R3_COMMON_RANK_ANALYSIS_PROTOCOL"
            or receipt.get("plan_sha256") != _sha256(plan_path)
            or receipt.get("outer_split_manifest_sha256") != _sha256(split_path)
            or receipt.get("target_status") != "FROZEN_R3_RANK_BENCHMARK"
            or receipt.get("outcome_analysis_run") is not False
            or receipt.get("model_fitted") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R3AnalysisProtocolError("R3 analysis protocol receipt is invalid")
        with split_path.open("r", encoding="utf-8", newline="") as stream:
            splits = list(csv.DictReader(stream))
        folds = {row["outer_fold_id"] for row in splits}
        if len(folds) != receipt.get("outer_fold_count"):
            raise R3AnalysisProtocolError("R3 analysis protocol split-fold count is invalid")
        return R3AnalysisProtocolSummary(
            eligible_observation_count=int(receipt["eligible_observation_count"]),
            canonical_protein_count=int(receipt["canonical_protein_count"]),
            laboratory_anchor_count=int(receipt["laboratory_anchor_count"]),
            measurement_batch_count=int(receipt["measurement_batch_count"]),
            outer_fold_count=int(receipt["outer_fold_count"]),
            receipt_path=receipt_path,
        )
