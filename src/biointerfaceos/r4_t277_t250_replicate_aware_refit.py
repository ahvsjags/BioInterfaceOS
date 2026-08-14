"""Refit the T250 model after pre-model technical-replicate collapse."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import _Observation
from biointerfaceos.r3_uniprot_mapping import _mapping, _sha256, _string
from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
    R4T193ThreeLabExecutionError,
    R4T193ThreeLabExecutionSummary,
    R4T193ThreeLabPrefrozenExecutionWorkflow,
)
from biointerfaceos.r4_t249_four_lab_common_target import R4T249FourLabCommonTargetWorkflow
from biointerfaceos.r4_t250_four_lab_common_target_execution import (
    R4T250FourLabCommonTargetExecutionWorkflow,
)


class R4T277ReplicateAwareRefitError(R4T193ThreeLabExecutionError):
    """Raised when the T277 replicate-aware refit cannot close its contract."""


class R4T277T250ReplicateAwareRefitWorkflow(R4T193ThreeLabPrefrozenExecutionWorkflow):
    """Run T250 after collapsing technical replicates before every model step."""

    AUDIT_ID = "bioif-r4-t277-t250-replicate-aware-refit-v1.0.0"
    STATUS = "T277_REPLICATE_AWARE_REFIT_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T277_T250_REPLICATE_AWARE_REFIT_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T277_T250_REPLICATE_AWARE_REFIT_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t277_t250_replicate_aware_refit/v1.0.0"
    REPORT_NAME = "t277_replicate_aware_refit_report.json"
    RECEIPT_NAME = "t277_replicate_aware_refit_receipt.json"
    TARGET_SOURCE = "R4_T249_FOUR_LAB_COMMON_TARGET_REGISTRY"
    FOLD_PREFIX = "T277"
    OBSERVATION_PREFIX = "T277"

    TRACE_FIELDS = [
        "collapsed_target_observation_id",
        "source_id",
        "measurement_batch_id",
        "canonical_accession",
        "raw_target_observation_ids",
        "raw_technical_replicate_ids",
        "raw_source_coordinates",
        "raw_source_rows",
        "raw_rank_percentiles",
        "collapsed_rank_percentile",
        "collapse_rule",
    ]

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        super().__init__(root, output_root=output_root)
        self._collapse_trace: list[dict[str, Any]] = []
        self._raw_observation_count = 0
        self._collapsed_group_count = 0

    def _registry(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], list[dict[str, Any]]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T277 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "t249_source_registry",
            "r3_common_rank_target_ledger",
            "r3_sequence_feature_table",
            "target_universe",
            "sources",
            "expected_accounting",
            "output_contract",
            "technical_replicate_policy",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T277ReplicateAwareRefitError("T277 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T277_REPLICATE_AWARE_REFIT_REGISTERED"
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T277ReplicateAwareRefitError("T277 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T277 protocol")
        protocol = self._json(protocol_path, "T277 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T277_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T277ReplicateAwareRefitError("T277 protocol identity or boundary is invalid")
        refs = {
            "t249_source_registry": self._reference(registry["t249_source_registry"], "T249 source registry"),
            "r3_common_rank_target_ledger": self._reference(
                registry["r3_common_rank_target_ledger"], "R3 target ledger"
            ),
            "r3_sequence_feature_table": self._reference(
                registry["r3_sequence_feature_table"], "R3 feature table"
            ),
        }
        target_universe = _mapping(protocol["target_universe"], "T277 target universe")
        common_targets = target_universe.get("common_targets")
        if (
            not isinstance(common_targets, list)
            or len(common_targets) != 7
            or len(set(common_targets)) != 7
            or any(not isinstance(item, str) or not item for item in common_targets)
        ):
            raise R4T277ReplicateAwareRefitError("T277 common target set is invalid")
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 4:
            raise R4T277ReplicateAwareRefitError("T277 requires exactly four source summaries")
        if len({str(_mapping(item, "T277 source")["source_id"]) for item in sources}) != 4:
            raise R4T277ReplicateAwareRefitError("T277 source IDs are not unique")
        expected = _mapping(registry["expected_accounting"], "T277 expected accounting")
        if expected != {
            "source_count": 4,
            "laboratory_anchor_count": 4,
            "target_universe_count": 7,
            "raw_observation_count": 783,
            "observation_count": 671,
            "collapsed_group_count": 112,
            "outer_fold_count": 4,
            "model_count": 3,
        }:
            raise R4T277ReplicateAwareRefitError("T277 expected accounting is invalid")
        t249 = R4T249FourLabCommonTargetWorkflow(self.root, registry_path=refs["t249_source_registry"])
        _, _, t249_sources = t249._documents()
        if {str(item["source_id"]) for item in t249_sources} != {
            str(_mapping(item, "T277 source")["source_id"]) for item in sources
        }:
            raise R4T277ReplicateAwareRefitError("T277 sources do not close T249")
        return registry, protocol, refs, t249_sources

    def _features_and_targets(
        self, refs: Mapping[str, Path], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, tuple[float, ...]], set[str]]:
        loader = R4T250FourLabCommonTargetExecutionWorkflow(self.root)
        loader_refs = {
            "r3_common_target_ledger": refs["r3_common_rank_target_ledger"],
            "r3_sequence_feature_table": refs["r3_sequence_feature_table"],
        }
        return loader._features_and_targets(loader_refs, protocol)

    def _source_workflow(self, refs: Mapping[str, Path]) -> R4T249FourLabCommonTargetWorkflow:
        return R4T249FourLabCommonTargetWorkflow(self.root, registry_path=refs["t249_source_registry"])

    @staticmethod
    def _round_numbers(value: Any) -> Any:
        """Quantize numeric artifacts so local and KAUST BLAS serialize identically."""
        if isinstance(value, float | np.floating):
            return float(f"{float(value):.7f}")
        if isinstance(value, dict):
            return {
                key: R4T277T250ReplicateAwareRefitWorkflow._round_numbers(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [R4T277T250ReplicateAwareRefitWorkflow._round_numbers(item) for item in value]
        if isinstance(value, tuple):
            return tuple(R4T277T250ReplicateAwareRefitWorkflow._round_numbers(item) for item in value)
        return value

    @staticmethod
    def _joined_values(rows: Sequence[Mapping[str, Any]], field: str) -> str:
        return ";".join(sorted({str(row.get(field, "")) for row in rows if str(row.get(field, ""))}))

    def _source_observations(
        self,
        t249: R4T249FourLabCommonTargetWorkflow,
        sources: Sequence[Mapping[str, Any]],
        features: Mapping[str, tuple[float, ...]],
        target_universe: set[str],
        registry: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, dict[str, Any]]]:
        raw_registry = dict(registry)
        raw_expected = dict(_mapping(registry["expected_accounting"], "T277 expected accounting"))
        raw_expected["observation_count"] = raw_expected["raw_observation_count"]
        raw_registry["expected_accounting"] = raw_expected
        raw_observations, raw_ledger, accounting = R4T193ThreeLabPrefrozenExecutionWorkflow._source_observations(
            self, t249, sources, features, target_universe, raw_registry
        )
        self._raw_observation_count = len(raw_observations)
        ledger_by_id = {str(row["target_observation_id"]): row for row in raw_ledger}
        grouped: dict[tuple[str, str, str], list[_Observation]] = defaultdict(list)
        for observation in raw_observations:
            grouped[
                (observation.source_id, observation.measurement_batch_id, observation.canonical_accession)
            ].append(observation)
        collapsed: list[_Observation] = []
        collapsed_ledger: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        collapsed_counts: Counter[str] = Counter()
        raw_counts: Counter[str] = Counter()
        for key in sorted(grouped):
            members = sorted(grouped[key], key=lambda item: item.target_observation_id)
            member_ledgers = [ledger_by_id[item.target_observation_id] for item in members]
            source_id, batch_id, accession = key
            raw_counts[source_id] += len(members)
            if len({item.feature_values for item in members}) != 1:
                raise R4T277ReplicateAwareRefitError("technical replicate rows disagree on feature vector")
            mean_rank = float(np.mean([item.target for item in members]))
            if len(members) == 1:
                collapsed.append(members[0])
                collapsed_ledger.append(member_ledgers[0])
                continue
            collapsed_counts[source_id] += 1
            identity = "|".join(("T277_COLLAPSED", source_id, batch_id, accession))
            collapsed_id = "T277_COLLAPSED_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
            collapsed.append(
                _Observation(
                    target_observation_id=collapsed_id,
                    source_id=source_id,
                    canonical_accession=accession,
                    laboratory_anchor=members[0].laboratory_anchor,
                    measurement_batch_id=batch_id,
                    target=mean_rank,
                    feature_values=members[0].feature_values,
                )
            )
            first = dict(member_ledgers[0])
            first.update(
                {
                    "target_observation_id": collapsed_id,
                    "source_coordinate": self._joined_values(member_ledgers, "source_coordinate"),
                    "source_row": self._joined_values(member_ledgers, "source_row"),
                    "source_identifier": self._joined_values(member_ledgers, "source_identifier"),
                    "technical_replicate_id": self._joined_values(member_ledgers, "technical_replicate_id"),
                    "author_numeric_value": self._joined_values(member_ledgers, "author_numeric_value"),
                    "author_quantity_type": "TECHNICAL_REPLICATE_MEAN_RANK",
                    "source_local_rank_percentile": format(mean_rank, ".17g"),
                    "multi_accession_group_flag": "true"
                    if any(row.get("multi_accession_group_flag") == "true" for row in member_ledgers)
                    else "false",
                }
            )
            collapsed_ledger.append(first)
            trace.append(
                {
                    "collapsed_target_observation_id": collapsed_id,
                    "source_id": source_id,
                    "measurement_batch_id": batch_id,
                    "canonical_accession": accession,
                    "raw_target_observation_ids": ";".join(item.target_observation_id for item in members),
                    "raw_technical_replicate_ids": self._joined_values(member_ledgers, "technical_replicate_id"),
                    "raw_source_coordinates": self._joined_values(member_ledgers, "source_coordinate"),
                    "raw_source_rows": self._joined_values(member_ledgers, "source_row"),
                    "raw_rank_percentiles": ";".join(format(item.target, ".17g") for item in members),
                    "collapsed_rank_percentile": format(mean_rank, ".17g"),
                    "collapse_rule": (
                        "mean available positive technical-replicate rank percentiles "
                        "before split/selection/fit"
                    ),
                }
            )
        self._collapse_trace = trace
        self._collapsed_group_count = len(trace)
        for source_id, values in accounting.items():
            values["raw_observation_count"] = raw_counts[source_id]
            values["collapsed_group_count"] = collapsed_counts[source_id]
            values["observation_count"] = raw_counts[source_id] - sum(
                len(grouped[key]) - 1 for key in grouped if key[0] == source_id
            )
            values["collapsed_observation_count"] = values["observation_count"]
        if len(collapsed) != 671 or len(trace) != 112:
            raise R4T277ReplicateAwareRefitError("T277 collapsed accounting differs")
        return (
            sorted(collapsed, key=lambda row: row.target_observation_id),
            sorted(collapsed_ledger, key=lambda row: row["target_observation_id"]),
            accounting,
        )

    def _execute_models(
        self, observations: Sequence[_Observation], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        """Reuse the frozen model path and replace its fixed-alpha null with a reselected null."""
        artifacts, fold_contract = R4T193ThreeLabPrefrozenExecutionWorkflow._execute_models(
            self, observations, protocol
        )
        helper = self._helper(self.root)
        nested = _mapping(protocol["nested_selection"], "T277 nested selection")
        minimum_proteins = int(nested["minimum_proteins_per_selection_batch"])
        negative = _mapping(protocol["negative_control"], "T277 negative control")
        negative_resamples = int(negative["resamples"])
        negative_seed = int(negative["random_seed"])
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        outer = sorted({row.laboratory_anchor for row in observations})
        selection_aware_rows: list[dict[str, Any]] = []
        parameters = artifacts["parameters"]
        for fold_index, held_out_lab in enumerate(outer, start=1):
            fold_id = f"{self.FOLD_PREFIX}_OUTER_{fold_index:02d}"
            development = [row for row in observations if row.laboratory_anchor != held_out_lab]
            testing = sorted(
                [row for row in observations if row.laboratory_anchor == held_out_lab],
                key=lambda row: (row.measurement_batch_id, row.target_observation_id),
            )
            observed = next(
                row["mean_spearman"]
                for row in artifacts["fold_metrics"]
                if row["outer_fold_id"] == fold_id and row["model_id"] == "SEQUENCE_RIDGE_FULL"
            )
            if observed is None:
                raise R4T277ReplicateAwareRefitError("T277 observed primary metric is undefined")
            development_targets = np.asarray([row.target for row in development], dtype=float)
            by_batch: dict[str, list[int]] = defaultdict(list)
            for position, row in enumerate(development):
                by_batch[row.measurement_batch_id].append(position)
            rng = np.random.default_rng(negative_seed + fold_index)
            null_values: list[float] = []
            selected_alphas: list[float] = []
            for resample in range(1, negative_resamples + 1):
                permuted = development_targets.copy()
                for positions in by_batch.values():
                    permuted[positions] = rng.permutation(permuted[positions])
                permuted_development = [
                    replace(row, target=float(permuted[position]))
                    for position, row in enumerate(development)
                ]
                null_alpha, _ = helper._select_alpha(
                    permuted_development,
                    full_indices,
                    minimum_proteins=minimum_proteins,
                )
                null_model = helper._fit_ridge(
                    permuted_development,
                    full_indices,
                    null_alpha,
                    targets=permuted,
                )
                null_metrics = helper._batch_metrics(
                    testing,
                    helper._predict_ridge(null_model, testing),
                    minimum_proteins=minimum_proteins,
                )
                null_score = helper._aggregate(null_metrics)["mean_spearman"]
                if null_score is None:
                    raise R4T277ReplicateAwareRefitError("T277 negative-control metric is undefined")
                selected_alphas.append(float(null_alpha))
                null_values.append(float(null_score))
                selection_aware_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "selected_alpha": null_alpha,
                        "resample": resample,
                        "null_mean_spearman": float(null_score),
                    }
                )
            alpha_counts = Counter(format(value, ".17g") for value in selected_alphas)
            parameters[fold_id]["SEQUENCE_RIDGE_FULL"]["negative_control"] = {
                "resamples": negative_resamples,
                "random_seed": negative_seed + fold_index,
                "selection_reexecution_per_resample": True,
                "selected_alpha_value_counts": dict(sorted(alpha_counts.items())),
                "observed_mean_spearman": float(observed),
                "null_mean_spearman_mean": float(np.mean(null_values)),
                "null_mean_spearman_lower_95": float(np.quantile(null_values, 0.025)),
                "null_mean_spearman_upper_95": float(np.quantile(null_values, 0.975)),
                "one_sided_upper_tail_p": float(
                    (1 + sum(value >= float(observed) for value in null_values))
                    / (1 + negative_resamples)
                ),
            }
        artifacts["negative_rows"] = selection_aware_rows
        return self._round_numbers(artifacts), self._round_numbers(fold_contract)

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        summary = super().run(strict=strict)
        trace_path = self.output_root / "technical_replicate_collapse_trace.csv"
        self._write_csv(trace_path, self.TRACE_FIELDS, self._collapse_trace)
        report_path = self.output_root / self.REPORT_NAME
        report = self._json(report_path, "T277 report")
        report["technical_replicate_collapse"] = {
            "raw_observation_count": self._raw_observation_count,
            "collapsed_observation_count": summary.observation_count,
            "collapsed_group_count": self._collapsed_group_count,
            "trace": {
                "relative_path": trace_path.relative_to(self.root).as_posix(),
                "sha256": _sha256(trace_path),
            },
        }
        report["frozen_cohort"]["raw_observation_count"] = self._raw_observation_count
        report["frozen_cohort"]["collapsed_group_count"] = self._collapsed_group_count
        report["artifacts"]["technical_replicate_collapse_trace"] = {
            "relative_path": trace_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(trace_path),
        }
        self._write_json(report_path, report)
        receipt_path = self.output_root / self.RECEIPT_NAME
        receipt = self._json(receipt_path, "T277 receipt")
        receipt.update(
            {
                "raw_observation_count": self._raw_observation_count,
                "collapsed_group_count": self._collapsed_group_count,
                "refit_status": "REFIT_AFTER_PREMODEL_TECHNICAL_REPLICATE_COLLAPSE",
                "technical_replicate_trace_sha256": _sha256(trace_path),
                "report_sha256": _sha256(report_path),
            }
        )
        self._write_json(receipt_path, receipt)
        return summary

    def verify(self, *, strict: bool = True) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T277ReplicateAwareRefitError("T277 verification requires --strict")
        self._registry()
        summary = super().verify(strict=True)
        report = self._json(self.output_root / self.REPORT_NAME, "T277 report")
        receipt = self._json(self.output_root / self.RECEIPT_NAME, "T277 receipt")
        collapse = _mapping(report.get("technical_replicate_collapse"), "T277 collapse")
        trace = _mapping(collapse.get("trace"), "T277 collapse trace")
        trace_path = self._root_file(_string(trace["relative_path"], "T277 trace path"), "T277 trace")
        if (
            _sha256(trace_path) != _string(trace["sha256"], "T277 trace checksum")
            or receipt.get("raw_observation_count") != 783
            or receipt.get("observation_count") != 671
            or receipt.get("collapsed_group_count") != 112
            or receipt.get("refit_status") != "REFIT_AFTER_PREMODEL_TECHNICAL_REPLICATE_COLLAPSE"
        ):
            raise R4T277ReplicateAwareRefitError("T277 replicate-aware receipt is invalid")
        return summary
