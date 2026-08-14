"""Execute the T265 three-cohort biological common-target route.

T265 is deliberately analysis-only because two of the paper-attached assets
are not redistributable under the public release contract.  It closes a
different scientific gap than the T192/T249 pooled-source route: all three
source maps expose biological-unit identifiers, the target set is the strict
positive intersection of the three maps, and the outer split leaves one
laboratory cohort out at a time.
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import _Observation
from biointerfaceos.r3_uniprot_mapping import _sha256, _string
from biointerfaceos.r4_t192_three_lab_common_target import (
    R4T192ThreeLabCommonTargetWorkflow,
)
from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
    R4T193ThreeLabExecutionError,
    R4T193ThreeLabExecutionSummary,
    R4T193ThreeLabPrefrozenExecutionWorkflow,
)


class R4T265BiologicalCommonTargetError(R4T193ThreeLabExecutionError):
    """Raised when the T265 biological common-target route is invalid."""


class _T265SourceWorkflow:
    """Minimal source provider used by the inherited T193 execution engine."""

    def __init__(self, sources: Sequence[Mapping[str, Any]]) -> None:
        self.sources = [dict(source) for source in sources]

    def _documents(self) -> tuple[None, None, list[dict[str, Any]]]:
        return None, None, self.sources


class R4T265BiologicalCommonTargetWorkflow(R4T193ThreeLabPrefrozenExecutionWorkflow):
    """Run a frozen three-independent-cohort common-target analysis."""

    AUDIT_ID = "bioif-r4-t265-three-lab-biological-common-target-v1.0.0"
    STATUS = "T265_BIOLOGICAL_COMMON_TARGET_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T265_THREE_LAB_BIOLOGICAL_COMMON_TARGET_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T265_THREE_LAB_BIOLOGICAL_COMMON_TARGET_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t265_biological_common_target/v1.0.0"
    REPORT_NAME = "t265_biological_common_target_report.json"
    RECEIPT_NAME = "t265_biological_common_target_receipt.json"
    OBSERVATION_PREFIX = "T265"
    FOLD_PREFIX = "T265"
    TARGET_SOURCE = "T265_strict_three_source_positive_intersection"
    LEDGER_FIELDS = R4T193ThreeLabPrefrozenExecutionWorkflow.LEDGER_FIELDS + ["model_metric_eligible"]

    def _reference_from_registry(self, value: Any, label: str) -> Path:
        try:
            return self._reference(value, label)
        except R4T193ThreeLabExecutionError as exc:
            raise R4T265BiologicalCommonTargetError(str(exc)) from exc

    def _registry(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], list[dict[str, Any]]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T265 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "target_freeze",
            "protocol_parameters",
            "sources",
            "expected_accounting",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T265BiologicalCommonTargetError("T265 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T265_BIOLOGICAL_COMMON_TARGET_REGISTERED"
            or registry.get("evidence_class") != "EXTERNAL_PUBLIC_ANALYSIS_ONLY"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T265BiologicalCommonTargetError("T265 registry identity or boundary is invalid")
        protocol_path = self._reference_from_registry(registry["protocol"], "T265 protocol")
        protocol = self._json(protocol_path, "T265 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T265_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T265BiologicalCommonTargetError("T265 protocol identity or boundary is invalid")
        refs = {
            "t265_registry": self.root / self.REGISTRY_RELATIVE,
            "r3_common_target_ledger": self._reference_from_registry(
                registry["r3_common_target_ledger"], "R3 common target ledger"
            ),
            "r3_sequence_feature_table": self._reference_from_registry(
                registry["r3_sequence_feature_table"], "R3 sequence feature table"
            ),
        }
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 3:
            raise R4T265BiologicalCommonTargetError("T265 requires exactly three source cohorts")
        normalized = [dict(source) for source in sources]
        if len({str(source.get("source_id")) for source in normalized}) != 3:
            raise R4T265BiologicalCommonTargetError("T265 source IDs must be unique")
        if len({str(source.get("laboratory_anchor")) for source in normalized}) != 3:
            raise R4T265BiologicalCommonTargetError("T265 laboratory anchors must be unique")
        for index, source in enumerate(normalized):
            for key in ("source_registry", "source_audit_report", "source_audit_receipt", "source_cell_map"):
                path = self._reference_from_registry(source[key], f"T265 source {index} {key}")
                refs[f"source_{index}_{key}"] = path
            if not source.get("biological_unit_semantics"):
                raise R4T265BiologicalCommonTargetError("T265 source biological-unit semantics are missing")
        return registry, protocol, refs, normalized

    def _features_and_targets(
        self, refs: Mapping[str, Path], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, tuple[float, ...]], set[str]]:
        rows = self._read_csv(refs["r3_sequence_feature_table"], "R3 sequence feature table")
        expected_columns = {"canonical_accession", *self.MODEL_FEATURE_NAMES}
        if set(rows[0]) != expected_columns:
            raise R4T265BiologicalCommonTargetError("R3 sequence feature table schema differs")
        target_freeze = protocol.get("target_freeze")
        if not isinstance(target_freeze, Mapping):
            raise R4T265BiologicalCommonTargetError("T265 target freeze is missing")
        targets = {str(value) for value in target_freeze.get("common_targets", [])}
        if len(targets) != int(target_freeze.get("common_target_count", -1)) or not targets:
            raise R4T265BiologicalCommonTargetError("T265 target freeze count is invalid")
        features: dict[str, tuple[float, ...]] = {}
        for row in rows:
            accession = _string(row.get("canonical_accession"), "feature accession")
            if accession not in targets:
                continue
            if accession in features:
                raise R4T265BiologicalCommonTargetError("T265 feature table repeats a target")
            try:
                values = tuple(float(row[name]) for name in self.MODEL_FEATURE_NAMES)
            except (TypeError, ValueError) as exc:
                raise R4T265BiologicalCommonTargetError("T265 feature value is invalid") from exc
            if not all(math.isfinite(value) for value in values):
                raise R4T265BiologicalCommonTargetError("T265 feature value is not finite")
            features[accession] = values
        if set(features) != targets:
            raise R4T265BiologicalCommonTargetError("T265 target freeze does not close feature table")
        return features, targets

    @property
    def MODEL_FEATURE_NAMES(self) -> tuple[str, ...]:
        from biointerfaceos.r3_model_evaluation import R3ModelEvaluationWorkflow

        return tuple(R3ModelEvaluationWorkflow.FEATURE_NAMES)

    def _source_workflow(self, refs: Mapping[str, Path]) -> _T265SourceWorkflow:
        _, _, _, sources = self._registry()
        return _T265SourceWorkflow(sources)

    def _source_observations(
        self,
        _unused_source_workflow: Any,
        sources: Sequence[Mapping[str, Any]],
        features: Mapping[str, tuple[float, ...]],
        target_universe: set[str],
        registry: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, dict[str, Any]]]:
        by_source: dict[str, list[dict[str, str]]] = {}
        source_meta = {str(source["source_id"]): source for source in registry["sources"]}
        for source in sources:
            source_id = _string(source.get("source_id"), "T265 source ID")
            if source_id not in source_meta:
                raise R4T265BiologicalCommonTargetError(f"T265 source is not registered: {source_id}")
            map_reference = source["source_cell_map"]
            map_path = self._reference_from_registry(map_reference, f"{source_id} source cell map")
            rows = self._read_csv(map_path, f"{source_id} source cell map")
            eligible: list[dict[str, str]] = []
            for row in rows:
                if row.get("source_id") != source_id or row.get("laboratory_anchor") != source["laboratory_anchor"]:
                    raise R4T265BiologicalCommonTargetError(f"{source_id} source identity differs in map")
                candidate = row.get("analysis_candidate_eligible", "true").strip().lower() == "true"
                if row.get("rank_target_eligible", "").strip().lower() != "true" or not candidate:
                    continue
                accession = row.get("canonical_accession", "").strip()
                if not accession or not row.get("measurement_batch_id", "").strip():
                    raise R4T265BiologicalCommonTargetError(f"{source_id} eligible row lacks identity")
                try:
                    value = float(row.get("author_numeric_value", ""))
                except (TypeError, ValueError) as exc:
                    raise R4T265BiologicalCommonTargetError(f"{source_id} eligible value is invalid") from exc
                if not math.isfinite(value) or value <= 0:
                    raise R4T265BiologicalCommonTargetError(f"{source_id} eligible value is not strictly positive")
                if not row.get("biological_unit_id", "").strip():
                    raise R4T265BiologicalCommonTargetError(f"{source_id} eligible row lacks biological unit")
                eligible.append(row)
            by_source[source_id] = eligible
        target_sets = {source_id: {row["canonical_accession"] for row in rows} for source_id, rows in by_source.items()}
        common_targets = set.intersection(*target_sets.values())
        declared = set(str(value) for value in registry["target_freeze"]["common_targets"])
        if common_targets != declared or common_targets != target_universe:
            raise R4T265BiologicalCommonTargetError("T265 strict positive target intersection differs from freeze")
        minimum = int(registry["protocol_parameters"]["minimum_common_targets_per_metric_batch"])
        observations: list[_Observation] = []
        ledger: list[dict[str, Any]] = []
        accounting: dict[str, dict[str, Any]] = {}
        for source in sources:
            source_id = _string(source.get("source_id"), "T265 source ID")
            eligible = by_source[source_id]
            ranks = R4T192ThreeLabCommonTargetWorkflow._rank_rows(eligible)
            common = [row for row in eligible if row["canonical_accession"] in common_targets]
            by_batch: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in common:
                by_batch[row["measurement_batch_id"]].append(row)
            qualified_batches = {batch for batch, rows in by_batch.items() if len(rows) >= minimum}
            meta = dict(source_meta[source_id])
            expected = dict(meta["expected_accounting"])
            observed = {
                "raw_map_rows": len(
                    self._read_csv(self._reference_from_registry(source["source_cell_map"], "source map"), "source map")
                ),
                "rank_eligible_rows": len(eligible),
                "rank_eligible_target_count": len(target_sets[source_id]),
                "rank_eligible_batch_count": len({row["measurement_batch_id"] for row in eligible}),
                "common_rows": len(common),
                "common_target_batch_pairs": len(
                    {(row["canonical_accession"], row["measurement_batch_id"]) for row in common}
                ),
                "biological_unit_count": len({row["biological_unit_id"] for row in common}),
                "qualified_measurement_batch_count": len(qualified_batches),
                "qualified_biological_unit_count": len(
                    {row["biological_unit_id"] for row in common if row["measurement_batch_id"] in qualified_batches}
                ),
            }
            for key in (
                "raw_map_rows",
                "rank_eligible_rows",
                "rank_eligible_target_count",
                "rank_eligible_batch_count",
                "common_rows",
                "common_target_batch_pairs",
            ):
                if int(expected[key]) != observed[key]:
                    raise R4T265BiologicalCommonTargetError(f"{source_id} accounting differs for {key}")
            accounting[source_id] = {
                "laboratory_anchor": source["laboratory_anchor"],
                "license": source["license"],
                "access_condition": source["access_condition"],
                "biological_unit_semantics": source["biological_unit_semantics"],
                **observed,
            }
            row_indices = {id(row): index for index, row in enumerate(eligible)}
            for row in sorted(
                common,
                key=lambda item: (item["measurement_batch_id"], item["canonical_accession"], item["source_coordinate"]),
            ):
                percentile, positive_count = ranks[row_indices[id(row)]]
                identity = "|".join((source_id, row["source_coordinate"], row["canonical_accession"]))
                observation_id = "T265_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                if row["measurement_batch_id"] in qualified_batches:
                    observations.append(
                        _Observation(
                            target_observation_id=observation_id,
                            source_id=source_id,
                            canonical_accession=row["canonical_accession"],
                            laboratory_anchor=source["laboratory_anchor"],
                            measurement_batch_id=row["measurement_batch_id"],
                            target=percentile,
                            feature_values=features[row["canonical_accession"]],
                        )
                    )
                ledger.append(
                    {
                        "target_observation_id": observation_id,
                        "source_id": source_id,
                        "laboratory_anchor": source["laboratory_anchor"],
                        "source_license": source["license"],
                        "canonical_accession": row["canonical_accession"],
                        "measurement_batch_id": row["measurement_batch_id"],
                        "biological_unit_id": row["biological_unit_id"],
                        "source_asset_id": row.get("source_asset_id", row.get("source_file", "")),
                        "source_worksheet": row.get("source_worksheet", row.get("source_file", "")),
                        "source_row": row.get("source_row", ""),
                        "source_coordinate": row["source_coordinate"],
                        "source_identifier": row.get("source_identifier", ""),
                        "source_sample": row.get("source_sample", row.get("particle", row.get("cohort", ""))),
                        "condition_label": row.get("condition_label", row.get("clinical_group", row.get("cohort", ""))),
                        "technical_replicate_id": row.get("technical_replicate_id", ""),
                        "author_quantity_type": row.get("author_quantity_type", ""),
                        "author_numeric_value": row["author_numeric_value"],
                        "author_value_state": row.get("author_value_state", ""),
                        "rank_target_eligible": "true",
                        "prefrozen_target_universe_member": "true",
                        "multi_accession_group_flag": "true" if ";" in row.get("source_identifier", "") else "false",
                        "source_local_rank_percentile": format(percentile, ".17g"),
                        "source_batch_positive_count": positive_count,
                        "cross_source_scale_use": "PROHIBITED",
                        "model_metric_eligible": "true"
                        if row["measurement_batch_id"] in qualified_batches
                        else "false",
                    }
                )
        expected_total = int(registry["expected_accounting"]["observation_count"])
        if len(observations) != expected_total:
            raise R4T265BiologicalCommonTargetError("T265 total observation count differs")
        return (
            sorted(observations, key=lambda row: row.target_observation_id),
            sorted(ledger, key=lambda row: row["target_observation_id"]),
            accounting,
        )

    @staticmethod
    def _cluster_interval(values: Sequence[float], seed: int, resamples: int) -> dict[str, Any] | None:
        if not values:
            return None
        array = np.asarray(values, dtype=float)
        rng = np.random.default_rng(seed)
        samples = array[rng.integers(0, len(array), size=(resamples, len(array)))].mean(axis=1)
        lower, upper = np.quantile(samples, [0.025, 0.975], method="linear")
        return {
            "mean": float(np.mean(array)),
            "lower_95": float(lower),
            "upper_95": float(upper),
            "cluster_count": int(len(array)),
            "resamples": resamples,
            "seed": seed,
        }

    @staticmethod
    def _round_numbers(value: Any) -> Any:
        """Quantize numeric artifacts so BLAS implementations serialize identically."""
        if isinstance(value, (float, np.floating)):
            # Eight decimal places preserve publication-scale estimates while
            # collapsing small BLAS/CPU-specific coefficient drift.
            return float(f"{float(value):.8f}")
        if isinstance(value, dict):
            return {key: R4T265BiologicalCommonTargetWorkflow._round_numbers(item) for key, item in value.items()}
        if isinstance(value, list):
            return [R4T265BiologicalCommonTargetWorkflow._round_numbers(item) for item in value]
        if isinstance(value, tuple):
            return tuple(R4T265BiologicalCommonTargetWorkflow._round_numbers(item) for item in value)
        return value

    def _execute_models(
        self, observations: Sequence[_Observation], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        artifacts, fold_contract = super()._execute_models(observations, protocol)
        return self._round_numbers(artifacts), self._round_numbers(fold_contract)

    def _augment_cluster_artifact(self) -> None:
        report_path = self.output_root / self.REPORT_NAME
        receipt_path = self.output_root / self.RECEIPT_NAME
        report = self._json(report_path, "T265 report")
        receipt = self._json(receipt_path, "T265 receipt")
        ledger_path = self.output_root / "source_local_prefrozen_target_ledger.csv"
        metrics_path = self.output_root / "measurement_batch_metrics.csv"
        with ledger_path.open(encoding="utf-8", newline="") as stream:
            ledger = list(csv.DictReader(stream))
        with metrics_path.open(encoding="utf-8", newline="") as stream:
            metrics = list(csv.DictReader(stream))
        batch_to_unit = {row["measurement_batch_id"]: row["biological_unit_id"] for row in ledger}
        unit_summary: list[dict[str, Any]] = []
        for fold_id in sorted({row["outer_fold_id"] for row in metrics}):
            held_out = next(row["held_out_laboratory_anchor"] for row in metrics if row["outer_fold_id"] == fold_id)
            for model_id in self.MODEL_IDS:
                rows = [row for row in metrics if row["outer_fold_id"] == fold_id and row["model_id"] == model_id]
                by_unit: dict[str, list[float]] = defaultdict(list)
                for row in rows:
                    value = row.get("spearman", "")
                    if value not in {"", "None", "nan"}:
                        by_unit[batch_to_unit[row["measurement_batch_id"]]].append(float(value))
                unit_values = [float(np.mean(values)) for _, values in sorted(by_unit.items()) if values]
                summary = self._cluster_interval(unit_values, 20260814 + len(unit_summary), 2000)
                unit_summary.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out,
                        "model_id": model_id,
                        "primary_metric": "biological_unit_equal_mean_of_batch_spearman",
                        "measurement_batch_count": len(rows),
                        "biological_unit_count": 0 if summary is None else summary["cluster_count"],
                        "mean_spearman": None if summary is None else summary["mean"],
                        "mean_spearman_lower_95": None if summary is None else summary["lower_95"],
                        "mean_spearman_upper_95": None if summary is None else summary["upper_95"],
                        "bootstrap_resamples": 2000,
                    }
                )
        paired_summary: list[dict[str, Any]] = []
        for fold_id in sorted({row["outer_fold_id"] for row in metrics}):
            full = {
                row["measurement_batch_id"]: row
                for row in metrics
                if row["outer_fold_id"] == fold_id and row["model_id"] == "SEQUENCE_RIDGE_FULL"
            }
            composition = {
                row["measurement_batch_id"]: row
                for row in metrics
                if row["outer_fold_id"] == fold_id and row["model_id"] == "SEQUENCE_RIDGE_COMPOSITION_ONLY"
            }
            by_unit: dict[str, list[float]] = defaultdict(list)
            for batch, full_row in full.items():
                comp_row = composition.get(batch)
                if comp_row is None or not full_row.get("spearman") or not comp_row.get("spearman"):
                    continue
                by_unit[batch_to_unit[batch]].append(float(full_row["spearman"]) - float(comp_row["spearman"]))
            values = [float(np.mean(items)) for _, items in sorted(by_unit.items()) if items]
            interval = self._cluster_interval(values, 20261800 + len(paired_summary), 2000)
            paired_summary.append(
                {
                    "outer_fold_id": fold_id,
                    "primary_metric": "biological_unit_equal_mean_full_minus_composition_spearman",
                    "biological_unit_count": 0 if interval is None else interval["cluster_count"],
                    "mean_full_minus_composition_spearman": None if interval is None else interval["mean"],
                    "lower_95": None if interval is None else interval["lower_95"],
                    "upper_95": None if interval is None else interval["upper_95"],
                    "bootstrap_resamples": 2000,
                }
            )
        cluster = {
            "schema_version": 1,
            "cluster_key": "biological_unit_id",
            "unit_rule": (
                "patient/donor/sample-native biological_unit_id; repeated timepoints remain within unit; "
                "technical replicate IDs are not units"
            ),
            "uncertainty": (
                "cluster bootstrap over biological units after within-unit mean across qualified measurement batches"
            ),
            "unit_equal_metrics": unit_summary,
            "paired_ablation": paired_summary,
        }
        cluster_path = self.output_root / "biological_unit_cluster_summary.json"
        self._write_json(cluster_path, cluster)
        report.setdefault("artifacts", {})["biological_unit_cluster_summary"] = {
            "relative_path": cluster_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(cluster_path),
        }
        report["biological_cluster_uncertainty"] = cluster
        report["frozen_cohort"]["biological_unit_count"] = len(set(batch_to_unit.values()))
        report["target_universe"]["source"] = self.TARGET_SOURCE
        report["frozen_cohort"]["qualified_measurement_batch_count"] = sum(
            int(item["measurement_batch_count"]) for item in unit_summary if item["model_id"] == "SEQUENCE_RIDGE_FULL"
        )
        report["frozen_cohort"]["source_map_common_row_count"] = sum(
            int(item["common_rows"]) for item in report["source_accounting"].values()
        )
        self._write_json(report_path, report)
        receipt["report_sha256"] = _sha256(report_path)
        receipt["biological_unit_count"] = len(set(batch_to_unit.values()))
        receipt["cluster_uncertainty_artifact"] = {
            "relative_path": cluster_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(cluster_path),
        }
        self._write_json(receipt_path, receipt)

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T265BiologicalCommonTargetError("T265 execution requires --strict")
        summary = super().run(strict=True)
        self._augment_cluster_artifact()
        return summary
