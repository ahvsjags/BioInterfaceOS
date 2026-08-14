"""Run the paper-data multicore technical sensitivity execution for T246."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import R3ModelEvaluationWorkflow, _Observation


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data/raw/r4_candidate_pmc11328176/derived/R4_PMC11328176_MULTICORE_source_cell_map.csv"
TARGETS = ROOT / "data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv"
FEATURES = ROOT / "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv"
OUT = ROOT / "reports/review_round_4/pmc11328176_multicore_technical_execution/v1.0.0"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rank_values(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (-values[index], index))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        midrank = (cursor + 1 + end) / 2.0
        percentile = 0.5 if len(order) == 1 else (len(order) - midrank) / (len(order) - 1)
        for position in range(cursor, end):
            ranks[order[position]] = percentile
        cursor = end
    return ranks


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row[field] for field in fields})


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def build_observations() -> tuple[list[_Observation], dict[str, int], dict[str, int]]:
    target_rows = read_csv(TARGETS)
    targets = {
        row["canonical_accession"]
        for row in target_rows
        if row.get("common_rank_target_member") == "true"
    }
    feature_rows = read_csv(FEATURES)
    feature_names = R3ModelEvaluationWorkflow.FEATURE_NAMES
    feature_values = {
        row["canonical_accession"]: tuple(float(row[name]) for name in feature_names)
        for row in feature_rows
    }
    if set(feature_values) != targets:
        raise RuntimeError("feature table and frozen target universe differ")

    source_rows = read_csv(MAP)
    by_core: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        by_core[row["core_facility_code"]].append(row)
    observations: list[_Observation] = []
    target_counts: dict[str, int] = {}
    raw_target_counts: dict[str, int] = {}
    for core in sorted(by_core):
        rows = sorted(by_core[core], key=lambda row: row["protein_ids"])
        values: list[float] = []
        for row in rows:
            replicates = [
                float(row[name])
                for name in ("replicate_1", "replicate_2", "replicate_3")
                if row.get(name, "") != ""
            ]
            if not replicates or not all(math.isfinite(value) and value > 0.0 for value in replicates):
                raise RuntimeError("source replicate is not positive finite")
            values.append(float(np.mean(replicates)))
        ranks = rank_values(values)
        selected = 0
        for row, rank in zip(rows, ranks, strict=True):
            accession = row["protein_ids"]
            if accession not in targets:
                continue
            identity = f"PMC11328176|{core}|{accession}|{row['source_row']}"
            observation_id = "T246_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
            observations.append(
                _Observation(
                    target_observation_id=observation_id,
                    source_id="PMC11328176_MULTICORE",
                    canonical_accession=accession,
                    laboratory_anchor=f"PMC11328176_CORE_{core}",
                    measurement_batch_id=f"PMC11328176_CORE_{core}",
                    target=rank,
                    feature_values=feature_values[accession],
                )
            )
            selected += 1
        target_counts[core] = selected
        raw_target_counts[core] = sum(row["protein_ids"] in targets for row in rows) * 3
    if len(observations) != 203 or len(by_core) != 6 or min(target_counts.values()) < 10:
        raise RuntimeError(f"unexpected accounting: {len(observations)=}, {target_counts=}")
    return sorted(observations, key=lambda row: row.target_observation_id), target_counts, raw_target_counts


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"output already exists: {OUT}")
    observations, target_counts, raw_target_counts = build_observations()
    helper = R3ModelEvaluationWorkflow(ROOT, ROOT / "data/raw", ROOT / "data/raw/r3_uniprot_sequence_features")
    full_indices = tuple(range(len(helper.FEATURE_NAMES)))
    composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
    outer = sorted({row.laboratory_anchor for row in observations})
    predictions: list[dict[str, Any]] = []
    fold_metrics: list[dict[str, Any]] = []
    batch_metrics: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    ablations: list[dict[str, Any]] = []
    negative_rows: list[dict[str, Any]] = []
    fold_primary: dict[tuple[str, str], float] = {}
    parameters: dict[str, Any] = {}
    minimum_proteins = 10
    for fold_index, held_out in enumerate(outer, start=1):
        fold_id = f"T246_OUTER_{fold_index:02d}"
        development = [row for row in observations if row.laboratory_anchor != held_out]
        testing = [row for row in observations if row.laboratory_anchor == held_out]
        full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=minimum_proteins)
        comp_alpha, comp_selection = helper._select_alpha(
            development, composition_indices, minimum_proteins=minimum_proteins
        )
        for model_id, alpha, rows in (
            ("SEQUENCE_RIDGE_FULL", full_alpha, full_selection),
            ("SEQUENCE_RIDGE_COMPOSITION_ONLY", comp_alpha, comp_selection),
        ):
            selections.extend(
                {
                    "outer_fold_id": fold_id,
                    "held_out_core": held_out,
                    "model_id": model_id,
                    **row,
                    "selected_alpha": alpha,
                }
                for row in rows
            )
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        comp_model = helper._fit_ridge(development, composition_indices, comp_alpha)
        constant = np.full(len(testing), np.mean([row.target for row in development]), dtype=float)
        model_predictions = {
            "CONSTANT_TRAINING_MEAN": constant,
            "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, testing),
            "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(comp_model, testing),
        }
        parameters[fold_id] = {
            "held_out_core": held_out,
            "development_observation_count": len(development),
            "held_out_observation_count": len(testing),
            "full_alpha": full_alpha,
            "composition_only_alpha": comp_alpha,
        }
        fold_metric_by_model: dict[str, dict[str, Any]] = {}
        for model_id in helper.MODEL_IDS:
            metrics = helper._batch_metrics(testing, model_predictions[model_id], minimum_proteins=minimum_proteins)
            aggregate = helper._aggregate(metrics)
            fold_metric_by_model[model_id] = aggregate
            fold_primary[(fold_id, model_id)] = float(aggregate["mean_spearman"]) if aggregate["mean_spearman"] is not None else math.nan
            fold_metrics.append(
                {
                    "outer_fold_id": fold_id,
                    "held_out_core": held_out,
                    "model_id": model_id,
                    "held_out_observation_count": len(testing),
                    **aggregate,
                    "primary_metric_status": "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED",
                }
            )
            for metric in metrics:
                batch_metrics.append({"outer_fold_id": fold_id, "held_out_core": held_out, "model_id": model_id, **metric})
            for row, prediction in zip(testing, model_predictions[model_id], strict=True):
                predictions.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_core": held_out,
                        "model_id": model_id,
                        "target_observation_id": row.target_observation_id,
                        "canonical_accession": row.canonical_accession,
                        "observed_rank_percentile_descending": row.target,
                        "predicted_rank_percentile_descending": float(prediction),
                    }
                )
        full_score = fold_metric_by_model["SEQUENCE_RIDGE_FULL"]["mean_spearman"]
        comp_score = fold_metric_by_model["SEQUENCE_RIDGE_COMPOSITION_ONLY"]["mean_spearman"]
        if full_score is None or comp_score is None:
            raise RuntimeError("undefined ablation metric")
        ablations.append(
            {
                "outer_fold_id": fold_id,
                "held_out_core": held_out,
                "full_minus_composition_mean_spearman": float(full_score) - float(comp_score),
            }
        )
        development_targets = np.asarray([row.target for row in development], dtype=float)
        by_batch: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(development):
            by_batch[row.measurement_batch_id].append(index)
        rng = np.random.default_rng(246000 + fold_index)
        null_scores: list[float] = []
        for resample in range(1, 257):
            permuted = development_targets.copy()
            for indices in by_batch.values():
                permuted[indices] = rng.permutation(permuted[indices])
            null_model = helper._fit_ridge(development, full_indices, full_alpha, targets=permuted)
            null_metric = helper._aggregate(
                helper._batch_metrics(testing, helper._predict_ridge(null_model, testing), minimum_proteins=minimum_proteins)
            )["mean_spearman"]
            if null_metric is None:
                raise RuntimeError("undefined negative-control metric")
            null_scores.append(float(null_metric))
            negative_rows.append(
                {
                    "outer_fold_id": fold_id,
                    "held_out_core": held_out,
                    "resample": resample,
                    "null_mean_spearman": float(null_metric),
                }
            )
        observed = float(full_score)
        parameters[fold_id]["negative_control_upper_tail_p"] = (1 + sum(score >= observed for score in null_scores)) / (1 + len(null_scores))

    model_bootstrap: dict[str, Any] = {}
    for model_id in helper.MODEL_IDS:
        values = [fold_primary[(fold_id, model_id)] for fold_id in [f"T246_OUTER_{i:02d}" for i in range(1, 7)]]
        if model_id == "CONSTANT_TRAINING_MEAN":
            model_bootstrap[model_id] = {"status": "UNDEFINED_CONSTANT_PREDICTION"}
        else:
            model_bootstrap[model_id] = helper._bootstrap(values, resamples=2000, seed=246017)

    OUT.mkdir(parents=True)
    write_csv(OUT / "outer_fold_predictions.csv", list(predictions[0]), predictions)
    write_csv(OUT / "outer_fold_metrics.csv", list(fold_metrics[0]), fold_metrics)
    write_csv(OUT / "core_batch_metrics.csv", list(batch_metrics[0]), batch_metrics)
    write_csv(OUT / "nested_inner_selection.csv", list(selections[0]), selections)
    write_csv(OUT / "paired_ablation.csv", list(ablations[0]), ablations)
    write_csv(OUT / "within_core_rank_permutation.csv", list(negative_rows[0]), negative_rows)
    json_write(OUT / "outer_fold_model_parameters.json", parameters)
    artifact_paths = [
        OUT / "outer_fold_predictions.csv",
        OUT / "outer_fold_metrics.csv",
        OUT / "core_batch_metrics.csv",
        OUT / "nested_inner_selection.csv",
        OUT / "paired_ablation.csv",
        OUT / "within_core_rank_permutation.csv",
        OUT / "outer_fold_model_parameters.json",
    ]
    report = {
        "schema_version": 1,
        "audit_id": "bioif-r4-t246-pmc11328176-multicore-technical-execution-v1.0.0",
        "status": "T246_PMC11328176_MULTICORE_TECHNICAL_EXECUTION_COMPLETED_EXPLORATORY",
        "evidence_class": "DEVELOPMENT_OBSERVATION",
        "allowed_claim_level": "EXPLORATORY",
        "input_references": {
            "source_map": {"relative_path": str(MAP.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(MAP)},
            "target_ledger": {"relative_path": str(TARGETS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(TARGETS)},
            "feature_table": {"relative_path": str(FEATURES.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(FEATURES)},
        },
        "source_semantics": {
            "source_article": "10.1021/acs.nanolett.4c02076",
            "source_pmcid": "PMC11328176",
            "biological_unit_count": 1,
            "biological_unit_semantics": "one common prepared corona/plasma material",
            "technical_core_count": 6,
            "technical_replicates_per_core": 3,
            "target_count_by_core": target_counts,
            "raw_target_rows_by_core": raw_target_counts,
        },
        "frozen_cohort": {
            "observation_count": len(observations),
            "target_universe_count": 99,
            "outer_fold_count": 6,
            "measurement_batch_count": 6,
            "model_count": 3,
            "minimum_proteins_per_batch": 10,
        },
        "model_results": fold_metrics,
        "core_cluster_bootstrap": model_bootstrap,
        "paired_composition_ablation": ablations,
        "artifacts": {
            str(path.name): {"relative_path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(path)}
            for path in artifact_paths
        },
        "claim_boundary": "Technical cross-core portability sensitivity only; no independent biological validation, lockbox evaluation, no-author reproduction, external adoption, or submission readiness.",
        "independent_validation": False,
        "external_scientific_reproduction": False,
        "external_user_adoption": False,
        "scientific_submission_ready": False,
    }
    report_path = OUT / "pmc11328176_multicore_technical_execution_report.json"
    json_write(report_path, report)
    receipt = {
        "schema_version": 1,
        "audit_id": report["audit_id"],
        "status": report["status"],
        "report_sha256": sha256(report_path),
        "observation_count": len(observations),
        "target_universe_count": 99,
        "technical_core_count": 6,
        "measurement_batch_count": 6,
        "model_count": 3,
        "nested_selection_executed": True,
        "paired_ablation_executed": True,
        "negative_control_executed": True,
        "cluster_bootstrap_resamples": 2000,
        "independent_validation": False,
        "external_scientific_reproduction": False,
        "scientific_submission_ready": False,
    }
    json_write(OUT / "pmc11328176_multicore_technical_execution_receipt.json", receipt)
    print(json.dumps({"report": str(report_path), "observations": len(observations), "target_counts": target_counts, "bootstrap": model_bootstrap}, indent=2))


if __name__ == "__main__":
    main()
