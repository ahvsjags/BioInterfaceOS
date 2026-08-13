from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from biointerfaceos.r4_ood_effective_n_audit import (
    R4OODEffectiveNAuditError,
    R4OODEffectiveNAuditWorkflow,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    source_map = tmp_path / "data/source_map.csv"
    source_map.parent.mkdir(parents=True)
    fieldnames = [
        "source_id",
        "laboratory_anchor",
        "source_asset_id",
        "measurement_batch_id",
        "biological_unit_id",
        "condition_label",
        "analysis_candidate_eligible",
        "author_value_state",
        "rank_target_eligible",
    ]
    rows: list[dict[str, str]] = []
    for batch_id, unit_id, positive_count in (
        ("batch_1", "POOLED_HUMAN_PLASMA", 10),
        ("batch_2", "DONOR_1", 9),
    ):
        for _index in range(positive_count):
            rows.append(
                {
                    "source_id": "fixture-source",
                    "laboratory_anchor": "fixture-lab",
                    "source_asset_id": "fixture-asset",
                    "measurement_batch_id": batch_id,
                    "biological_unit_id": unit_id,
                    "condition_label": "fixture-condition",
                    "analysis_candidate_eligible": "true",
                    "author_value_state": "POSITIVE_FINITE",
                    "rank_target_eligible": "true",
                }
            )
        rows.append(
            {
                "source_id": "fixture-source",
                "laboratory_anchor": "fixture-lab",
                "source_asset_id": "fixture-asset",
                "measurement_batch_id": batch_id,
                "biological_unit_id": unit_id,
                "condition_label": "fixture-condition",
                "analysis_candidate_eligible": "true",
                "author_value_state": "SOURCE_NA",
                "rank_target_eligible": "false",
            }
        )
    with source_map.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    upstream = tmp_path / "docs/upstream.json"
    _write_json(upstream, {"protocol": "fixture"})
    protocol = tmp_path / "docs/protocol.json"
    _write_json(
        protocol,
        {
            "schema_version": 1,
            "protocol_id": "bioif-r4-ood-effective-n-missingness-v1.0.0",
            "frozen_at": "2026-08-13T00:00:00+00:00",
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "source_map": {
                "relative_path": "data/source_map.csv",
                "sha256": _sha256(source_map),
            },
            "upstream_ood_protocol": {
                "relative_path": "docs/upstream.json",
                "sha256": _sha256(upstream),
            },
            "eligibility": {
                "analysis_candidate_flag": "true",
                "rank_target_flag": "true",
                "source_na_policy": "report_as_missing_without_imputation",
                "primary_minimum_rank_eligible_proteins_per_batch": 10,
            },
            "effective_n_groups": [
                "laboratory_anchor",
                "source_asset_id",
                "biological_unit_id",
                "condition_label",
                "measurement_batch_id",
            ],
            "pooled_unit_rule": "fixture pooled rule",
            "threshold_sensitivity": {
                "minimum_rank_eligible_proteins_per_batch": [1, 10, 20, 40, 50, 60, 70, 80]
            },
            "missingness_outputs": [
                "source_value_state_counts",
                "source_na_counts_by_biological_unit",
                "analysis_candidate_to_rank_target_retention",
                "eligible_batch_counts_by_threshold",
            ],
            "claim_boundary": "fixture only",
        },
    )
    return source_map, protocol, tmp_path / "reports/effective_n"


def test_effective_n_audit_reports_units_and_missingness(tmp_path: Path) -> None:
    source_map, protocol, output_root = _write_fixture(tmp_path)
    workflow = R4OODEffectiveNAuditWorkflow(
        tmp_path,
        source_map_path=source_map,
        protocol_path=protocol,
        output_root=output_root,
    )

    summary = workflow.run(strict=True)

    assert summary.source_row_count == 21
    assert summary.measurement_batch_count == 2
    assert summary.primary_rank_eligible_batch_count == 1
    assert summary.biological_unit_count == 2
    assert summary.laboratory_count == 1
    report = json.loads(summary.report_path.read_text(encoding="utf-8"))
    assert report["source_value_state_counts"] == {"POSITIVE_FINITE": 19, "SOURCE_NA": 2}
    assert report["scientific_submission_ready"] is False
    assert workflow.verify() == summary


def test_effective_n_audit_requires_strict_mode(tmp_path: Path) -> None:
    source_map, protocol, output_root = _write_fixture(tmp_path)

    with pytest.raises(R4OODEffectiveNAuditError, match="requires --strict"):
        R4OODEffectiveNAuditWorkflow(
            tmp_path,
            source_map_path=source_map,
            protocol_path=protocol,
            output_root=output_root,
        ).run()
