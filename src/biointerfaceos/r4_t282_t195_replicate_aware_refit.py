"""Refit the T195 redistributable primary route after pre-model replicate collapse."""

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
from biointerfaceos.r4_t195_three_lab_common_target_execution import (
    R4T195ThreeLabCommonTargetExecutionWorkflow,
)
from biointerfaceos.r4_t277_t250_replicate_aware_refit import (
    R4T277T250ReplicateAwareRefitWorkflow,
)


class R4T282T195ReplicateAwareRefitError(R4T193ThreeLabExecutionError):
    """Raised when the T282 primary-route refit cannot close."""


class R4T282T195ReplicateAwareRefitWorkflow(R4T195ThreeLabCommonTargetExecutionWorkflow):
    """Run T195 after collapsing source/batch/target technical replicates."""

    AUDIT_ID = "bioif-r4-t282-t195-replicate-aware-refit-v1.0.0"
    STATUS = "T282_T195_REPLICATE_AWARE_REFIT_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T282_T195_REPLICATE_AWARE_REFIT_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T282_T195_REPLICATE_AWARE_REFIT_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t282_t195_replicate_aware_refit/v1.0.0"
    REPORT_NAME = "t282_t195_replicate_aware_refit_report.json"
    RECEIPT_NAME = "t282_t195_replicate_aware_refit_receipt.json"
    FOLD_PREFIX = "T282"
    OBSERVATION_PREFIX = "T282"
    TARGET_SOURCE = "R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY"
    TARGET_COUNT = 9
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
    _round_numbers = staticmethod(R4T277T250ReplicateAwareRefitWorkflow._round_numbers)

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        super().__init__(root, output_root=output_root)
        self._collapse_trace: list[dict[str, Any]] = []
        self._raw_observation_count = 0
        self._collapsed_group_count = 0

    def _registry(self):  # type: ignore[no-untyped-def]
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T282 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "t192_source_registry",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "target_universe",
            "sources",
            "expected_accounting",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T282T195ReplicateAwareRefitError("T282 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T282_T195_REPLICATE_AWARE_REFIT_REGISTERED"
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T282T195ReplicateAwareRefitError("T282 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T282 protocol")
        protocol = self._json(protocol_path, "T282 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T282_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T282T195ReplicateAwareRefitError("T282 protocol identity or boundary is invalid")
        refs = {
            "t192_source_registry": self._reference(registry["t192_source_registry"], "T282 T192 registry"),
            "r3_common_target_ledger": self._reference(
                registry["r3_common_target_ledger"], "T282 common ledger"
            ),
            "r3_sequence_feature_table": self._reference(
                registry["r3_sequence_feature_table"], "T282 feature table"
            ),
        }
        targets = _mapping(protocol["target_universe"], "T282 target universe")
        common_targets = targets.get("common_targets")
        if (
            not isinstance(common_targets, list)
            or len(common_targets) != self.TARGET_COUNT
            or len(set(common_targets)) != self.TARGET_COUNT
        ):
            raise R4T282T195ReplicateAwareRefitError("T282 common target set is invalid")
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 3:
            raise R4T282T195ReplicateAwareRefitError("T282 requires exactly three source summaries")
        expected = _mapping(registry["expected_accounting"], "T282 expected accounting")
        if expected != {
            "source_count": 3,
            "laboratory_anchor_count": 3,
            "target_universe_count": 9,
            "raw_observation_count": 809,
            "observation_count": 644,
            "collapsed_group_count": 165,
            "outer_fold_count": 3,
            "model_count": 3,
        }:
            raise R4T282T195ReplicateAwareRefitError("T282 expected accounting is invalid")
        t192_sources = self._json(refs["t192_source_registry"], "T282 T192 registry").get("sources")
        if not isinstance(t192_sources, list) or len(t192_sources) != 3:
            raise R4T282T195ReplicateAwareRefitError("T282 T192 sources are invalid")
        return registry, protocol, refs, [_mapping(item, "T282 T192 source") for item in t192_sources]

    @staticmethod
    def _joined_values(rows: Sequence[Mapping[str, Any]], field: str) -> str:
        return ";".join(sorted({str(row.get(field, "")) for row in rows if str(row.get(field, ""))}))

    def _source_observations(
        self,
        t192: Any,
        sources: Sequence[Mapping[str, Any]],
        features: Mapping[str, tuple[float, ...]],
        target_universe: set[str],
        registry: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, dict[str, Any]]]:
        raw_registry = dict(registry)
        raw_expected = dict(_mapping(registry["expected_accounting"], "T282 expected accounting"))
        raw_expected["observation_count"] = raw_expected["raw_observation_count"]
        raw_registry["expected_accounting"] = raw_expected
        raw_observations, raw_ledger, accounting = R4T193ThreeLabPrefrozenExecutionWorkflow._source_observations(
            self, t192, sources, features, target_universe, raw_registry
        )
        self._raw_observation_count = len(raw_observations)
        ledger_by_id = {str(row["target_observation_id"]): row for row in raw_ledger}
        grouped: dict[tuple[str, str, str], list[_Observation]] = defaultdict(list)
        for observation in raw_observations:
            grouped[(observation.source_id, observation.measurement_batch_id, observation.canonical_accession)].append(
                observation
            )
        collapsed: list[_Observation] = []
        collapsed_ledger: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        duplicate_counts: Counter[str] = Counter()
        raw_counts: Counter[str] = Counter()
        for key in sorted(grouped):
            members = sorted(grouped[key], key=lambda item: item.target_observation_id)
            member_ledgers = [ledger_by_id[item.target_observation_id] for item in members]
            source_id, batch_id, accession = key
            raw_counts[source_id] += len(members)
            if len({item.feature_values for item in members}) != 1:
                raise R4T282T195ReplicateAwareRefitError("replicate rows disagree on feature vector")
            mean_rank = float(np.mean([item.target for item in members]))
            if len(members) == 1:
                collapsed.append(members[0])
                collapsed_ledger.append(member_ledgers[0])
                continue
            duplicate_counts[source_id] += 1
            identity = "|".join(("T282_COLLAPSED", source_id, batch_id, accession))
            collapsed_id = "T282_COLLAPSED_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
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
            values["collapsed_group_count"] = duplicate_counts[source_id]
            values["collapsed_observation_count"] = raw_counts[source_id] - duplicate_counts[source_id]
            values["observation_count"] = values["collapsed_observation_count"]
        if len(collapsed) != 644 or len(trace) != 165:
            raise R4T282T195ReplicateAwareRefitError("T282 collapsed accounting differs")
        return sorted(collapsed, key=lambda row: row.target_observation_id), sorted(
            collapsed_ledger, key=lambda row: row["target_observation_id"]
        ), accounting

    def _execute_models(
        self, observations: Sequence[_Observation], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        return R4T277T250ReplicateAwareRefitWorkflow._execute_models(self, observations, protocol)

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T282T195ReplicateAwareRefitError("T282 execution requires --strict")
        summary = super().run(strict=True)
        trace_path = self.output_root / "technical_replicate_collapse_trace.csv"
        self._write_csv(trace_path, self.TRACE_FIELDS, self._collapse_trace)
        report_path = self.output_root / self.REPORT_NAME
        report = self._json(report_path, "T282 report")
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
        receipt = self._json(receipt_path, "T282 receipt")
        receipt.update(
            {
                "raw_observation_count": self._raw_observation_count,
                "observation_count": summary.observation_count,
                "collapsed_group_count": self._collapsed_group_count,
                "refit_status": "REFIT_AFTER_PREMODEL_TECHNICAL_REPLICATE_COLLAPSE",
                "technical_replicate_trace_sha256": _sha256(trace_path),
                "report_sha256": _sha256(report_path),
            }
        )
        self._write_json(receipt_path, receipt)
        return replace(summary, receipt_path=receipt_path)

    def verify(self, *, strict: bool = True) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T282T195ReplicateAwareRefitError("T282 verification requires --strict")
        self._registry()
        summary = super().verify(strict=True)
        report = self._json(self.output_root / self.REPORT_NAME, "T282 report")
        receipt = self._json(self.output_root / self.RECEIPT_NAME, "T282 receipt")
        collapse = _mapping(report.get("technical_replicate_collapse"), "T282 collapse")
        trace = _mapping(collapse.get("trace"), "T282 collapse trace")
        trace_path = self._root_file(_string(trace["relative_path"], "T282 trace path"), "T282 trace")
        if (
            _sha256(trace_path) != _string(trace["sha256"], "T282 trace checksum")
            or receipt.get("raw_observation_count") != 809
            or receipt.get("observation_count") != 644
            or receipt.get("collapsed_group_count") != 165
            or receipt.get("refit_status") != "REFIT_AFTER_PREMODEL_TECHNICAL_REPLICATE_COLLAPSE"
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T282T195ReplicateAwareRefitError("T282 replicate-aware receipt is invalid")
        return summary
