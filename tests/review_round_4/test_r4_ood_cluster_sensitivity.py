from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from biointerfaceos.r4_ood_cluster_sensitivity import (
    R4OODClusterSensitivityError,
    R4OODClusterSensitivityWorkflow,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    source_map = tmp_path / "data/source_map.csv"
    source_map.parent.mkdir(parents=True)
    source_fields = [
        "laboratory_anchor",
        "measurement_batch_id",
        "biological_unit_id",
        "rank_target_eligible",
    ]
    source_rows: list[dict[str, str]] = []
    for batch_id, unit_id in (("batch_1", "POOLED_HUMAN_PLASMA"), ("batch_2", "DONOR_1")):
        for _index in range(2):
            source_rows.append(
                {
                    "laboratory_anchor": "fixture-lab",
                    "measurement_batch_id": batch_id,
                    "biological_unit_id": unit_id,
                    "rank_target_eligible": "true",
                }
            )
    with source_map.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=source_fields)
        writer.writeheader()
        writer.writerows(source_rows)

    batch_metrics = tmp_path / "reports/batch_metrics.csv"
    batch_metrics.parent.mkdir(parents=True, exist_ok=True)
    metric_fields = ["model_id", "measurement_batch_id", "spearman", "spearman_status"]
    metric_rows = [
        {
            "model_id": "SEQUENCE_RIDGE_FULL",
            "measurement_batch_id": "batch_1",
            "spearman": "0.8",
            "spearman_status": "DEFINED",
        },
        {
            "model_id": "SEQUENCE_RIDGE_FULL",
            "measurement_batch_id": "batch_2",
            "spearman": "0.2",
            "spearman_status": "DEFINED",
        },
        {
            "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
            "measurement_batch_id": "batch_1",
            "spearman": "0.6",
            "spearman_status": "DEFINED",
        },
        {
            "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
            "measurement_batch_id": "batch_2",
            "spearman": "0.3",
            "spearman_status": "DEFINED",
        },
    ]
    with batch_metrics.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=metric_fields)
        writer.writeheader()
        writer.writerows(metric_rows)

    upstream = tmp_path / "reports/upstream_ood.json"
    _write_json(upstream, {"audit": "fixture"})
    protocol = tmp_path / "docs/cluster_protocol.json"
    _write_json(
        protocol,
        {
            "schema_version": 1,
            "protocol_id": "bioif-r4-ood-cluster-sensitivity-v1.0.0",
            "frozen_at": "2026-08-13T00:00:00+00:00",
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "source_map": {
                "relative_path": "data/source_map.csv",
                "sha256": _sha256(source_map),
            },
            "batch_metrics": {
                "relative_path": "reports/batch_metrics.csv",
                "sha256": _sha256(batch_metrics),
            },
            "upstream_ood_report": {
                "relative_path": "reports/upstream_ood.json",
                "sha256": _sha256(upstream),
            },
            "cluster_unit": "biological_unit_id",
            "pooled_unit_rule": "fixture pooled rule",
            "models": ["SEQUENCE_RIDGE_FULL", "SEQUENCE_RIDGE_COMPOSITION_ONLY"],
            "paired_ablation": "paired full minus composition within measurement batch",
            "uncertainty": {
                "method": "equal-weight biological-unit bootstrap over unit-level means",
                "resamples": 2000,
                "random_seed": 20260827,
            },
            "claim_boundary": "fixture exploratory sensitivity only",
        },
    )
    return source_map, protocol, tmp_path / "reports/cluster_sensitivity"


def test_cluster_sensitivity_reports_unit_weighted_paired_delta(tmp_path: Path) -> None:
    _source_map, protocol, output_root = _write_fixture(tmp_path)
    workflow = R4OODClusterSensitivityWorkflow(
        tmp_path,
        protocol_path=protocol,
        output_root=output_root,
    )

    summary = workflow.run(strict=True)

    assert summary.batch_count == 2
    assert summary.biological_unit_count == 2
    assert summary.laboratory_count == 1
    report = json.loads(summary.report_path.read_text(encoding="utf-8"))
    assert report["paired_ablation"][
        "batch_weighted_mean_full_minus_composition"
    ] == pytest.approx(0.05)
    assert report["paired_ablation"][
        "unit_weighted_mean_full_minus_composition"
    ] == pytest.approx(0.05)
    assert report["scientific_submission_ready"] is False
    assert workflow.verify() == summary


def test_cluster_sensitivity_requires_strict_mode(tmp_path: Path) -> None:
    _source_map, protocol, output_root = _write_fixture(tmp_path)

    with pytest.raises(R4OODClusterSensitivityError, match="requires --strict"):
        R4OODClusterSensitivityWorkflow(
            tmp_path,
            protocol_path=protocol,
            output_root=output_root,
        ).run()
