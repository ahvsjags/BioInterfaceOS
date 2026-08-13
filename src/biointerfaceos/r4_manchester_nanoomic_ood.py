"""Audit and execute the Manchester public longitudinal nano-omics OOD source.

The source is used as an analysis-only external cohort.  Its author repository
contains gene-labelled standardized abundance matrices, so gene names are
resolved against the already frozen R3 UniProt mapping.  No target selection is
performed from the external cohort and no source-derived matrix is admitted to
the public release by this workflow.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolError, R3AnalysisProtocolWorkflow
from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationError,
    R3ModelEvaluationWorkflow,
    _Observation,
)
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4ManchesterNanoOmicError(RuntimeError):
    """Raised when the Manchester source cannot be audited or executed safely."""


@dataclass(frozen=True)
class R4ManchesterNanoOmicSummary:
    source_cell_count: int
    positive_source_cell_count: int
    biological_unit_count: int
    measurement_batch_count: int
    rank_qualified_measurement_batch_count: int
    shared_canonical_protein_count: int
    external_observation_count: int
    external_measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R4ManchesterNanoOmicWorkflow:
    """Freeze and score the external longitudinal nano-omics matrices."""

    AUDIT_ID = "bioif-r4-manchester-nanoomic-source-audit-v1.0.0"
    OOD_AUDIT_ID = "bioif-r4-manchester-nanoomic-ood-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R4_T185_MANCHESTER_NANOOMIC_SOURCE_REGISTRY.json"
    PROTOCOL_RELATIVE = "docs/data/R4_T186_MANCHESTER_NANOOMIC_BIOLOGICAL_OOD_PROTOCOL.json"
    SOURCE_MAP_RELATIVE = (
        "data/raw/r4_candidate_pmc13212878/derived/R4_PMC13212878_MANCHESTER_source_cell_map.csv"
    )
    AUDIT_OUTPUT_RELATIVE = "reports/review_round_4/manchester_nanoomic_source/v1.0.0"
    OOD_OUTPUT_RELATIVE = "reports/review_round_4/manchester_nanoomic_ood/v1.0.0"
    SOURCE_ID = "PMC13212878_MANCHESTER_NANOOMIC"
    LABORATORY = "University of Manchester NanoOmics Lab / Manchester BRC"
    MATRIX_FILES = {
        "P": "data_all_samples_all_time_points_norm_P_data.txt",
        "B": "data_all_samples_all_time_points_norm_B_data.txt",
        "HA": "data_all_samples_all_time_points_norm_HA_data.txt",
    }
    MATRIX_HASHES = {
        "data_all_samples_all_time_points_norm_P_data.txt": (
            "F5502F2AE42574C44C3D6397EC1433653D8CF4175B1E45B1BC7A2B0D32A721E6"
        ),
        "data_all_samples_all_time_points_norm_B_data.txt": (
            "D2EE6CD9B6DA815803D19172B07B665DCCE91E819243D24C913F15C745D06ED0"
        ),
        "data_all_samples_all_time_points_norm_HA_data.txt": (
            "03AEC60D7A5FF148540609FE75624EE0A7EBC769346311C36037B41DF2C2F40B"
        ),
    }
    TARGET_FIELDS = (
        "external_target_observation_id",
        "source_id",
        "laboratory_anchor",
        "canonical_accession",
        "source_identifier",
        "biological_unit_id",
        "cohort",
        "timepoint",
        "measurement_batch_id",
        "source_file",
        "source_row",
        "source_coordinate",
        "author_quantity_type",
        "author_numeric_value",
        "rank_percentile_descending",
        "measurement_batch_positive_protein_count",
    )

    def __init__(self, root: Path, assets_root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.assets_root = assets_root.resolve(strict=False)
        self.output_root = output_root or self.root / self.OOD_OUTPUT_RELATIVE

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
                writer.writerow(
                    {field: "" if row.get(field) is None else row.get(field) for field in fields}
                )

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise R4ManchesterNanoOmicError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        pure = PurePosixPath(relative_path)
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if (
            pure.is_absolute()
            or not pure.parts
            or ".." in pure.parts
            or not path.is_relative_to(self.root)
            or not path.is_file()
        ):
            raise R4ManchesterNanoOmicError(f"{label} is missing or escapes repository root")
        return path

    @staticmethod
    def _read_csv(path: Path, label: str, *, delimiter: str = ",") -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=delimiter))
        except (OSError, UnicodeError, csv.Error) as exc:
            raise R4ManchesterNanoOmicError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4ManchesterNanoOmicError(f"{label} is empty")
        return rows

    def _source_files(self) -> dict[str, Path]:
        expected = (self.root / "data/raw/r4_candidate_pmc13212878/author_repo").resolve()
        if self.assets_root != expected:
            raise R4ManchesterNanoOmicError(
                "Manchester source requires the fixed author-repository root"
            )
        paths: dict[str, Path] = {}
        for cohort, filename in self.MATRIX_FILES.items():
            path = self.assets_root / filename
            if not path.is_file() or _sha256(path).upper() != self.MATRIX_HASHES[filename]:
                raise R4ManchesterNanoOmicError(f"Manchester matrix hash differs: {filename}")
            paths[cohort] = path
        return paths

    def _target_gene_map(self) -> tuple[dict[str, str], set[str]]:
        ledger_path = self.root / "data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv"
        mapping_dir = (
            self.root
            / "data/raw/r3_uniprot_v1_0_1/uniprot_human_mapping/uniprot_api_response_batches"
        )
        ledger = self._read_csv(ledger_path, "R3 common target ledger")
        targets = {
            row["canonical_accession"]
            for row in ledger
            if row.get("common_rank_target_member") == "true"
        }
        gene_to_accessions: dict[str, set[str]] = defaultdict(set)
        for path in sorted(mapping_dir.glob("*.tsv")):
            for row in self._read_csv(path, f"UniProt mapping batch {path.name}", delimiter="\t"):
                accession = row.get("Entry", "")
                if accession not in targets:
                    continue
                for gene in row.get("Gene Names", "").split():
                    if gene:
                        gene_to_accessions[gene].add(accession)
        unique = {
            gene: next(iter(accessions))
            for gene, accessions in gene_to_accessions.items()
            if len(accessions) == 1
        }
        if len(unique) < 200 or len(targets) != 99:
            raise R4ManchesterNanoOmicError("frozen R3 gene-to-UniProt mapping is incomplete")
        return unique, targets

    @staticmethod
    def _sample_columns(headers: Sequence[str]) -> list[str]:
        return [header for header in headers if re.fullmatch(r"(?:P|B|HA)\d+[A-G]", header)]

    @staticmethod
    def _cohort_label(cohort: str) -> str:
        return {"P": "prostate", "B": "bladder", "HA": "head_and_neck"}[cohort]

    def _build_source_map(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        files = self._source_files()
        gene_map, targets = self._target_gene_map()
        rows: list[dict[str, Any]] = []
        batch_target_positive: dict[str, int] = defaultdict(int)
        units: set[str] = set()
        batches: set[str] = set()
        all_positive = 0
        source_cells = 0
        source_row_number = 0
        for cohort, path in files.items():
            try:
                with path.open("r", encoding="utf-8", newline="") as stream:
                    reader = csv.DictReader(stream, delimiter="\t")
                    if reader.fieldnames is None or "gene" not in reader.fieldnames:
                        raise R4ManchesterNanoOmicError(f"{path.name} lacks the gene column")
                    columns = self._sample_columns(reader.fieldnames)
                    for source_row_number, source_row in enumerate(reader, start=2):
                        gene = (source_row.get("gene") or "").strip()
                        canonical_accession = gene_map.get(gene, "")
                        for column in columns:
                            source_cells += 1
                            match = re.fullmatch(r"(?:P|B|HA)(\d+)([A-G])", column)
                            if match is None:
                                continue
                            unit = f"{cohort}{match.group(1)}"
                            timepoint = f"t{ord(match.group(2)) - ord('A')}"
                            batch = f"{self.SOURCE_ID}:{cohort}:{unit}:{timepoint}"
                            units.add(unit)
                            batches.add(batch)
                            raw = (source_row.get(column) or "").strip()
                            try:
                                numeric = float(raw)
                            except (TypeError, ValueError):
                                numeric = math.nan
                            positive = math.isfinite(numeric) and numeric > 0.0
                            if positive:
                                all_positive += 1
                            if positive and canonical_accession:
                                batch_target_positive[batch] += 1
                            rows.append(
                                {
                                    "source_id": self.SOURCE_ID,
                                    "laboratory_anchor": self.LABORATORY,
                                    "canonical_accession": canonical_accession,
                                    "source_identifier": gene,
                                    "biological_unit_id": unit,
                                    "cohort": self._cohort_label(cohort),
                                    "timepoint": timepoint,
                                    "measurement_batch_id": batch,
                                    "source_file": path.name,
                                    "source_row": source_row_number,
                                    "source_coordinate": (
                                        f"{path.name}::{column}::{source_row_number}"
                                    ),
                                    "author_quantity_type": "STANDARDIZED_AUTHOR_ABUNDANCE",
                                    "author_numeric_value": ""
                                    if not math.isfinite(numeric)
                                    else numeric,
                                    "author_value_state": "POSITIVE_QUANTIFIED"
                                    if positive
                                    else "NOT_RANK_ELIGIBLE",
                                    "rank_target_eligible": "true" if positive else "false",
                                    "analysis_candidate_eligible": "true"
                                    if positive and canonical_accession
                                    else "false",
                                }
                            )
            except (OSError, UnicodeError, csv.Error) as exc:
                raise R4ManchesterNanoOmicError(
                    f"cannot parse Manchester matrix {path.name}"
                ) from exc
        qualified = {batch for batch, count in batch_target_positive.items() if count >= 10}
        shared = {row["canonical_accession"] for row in rows if row["canonical_accession"]}
        expected = {
            "source_cell_count": 193971,
            "positive_source_cell_count": 177636,
            "biological_unit_count": 61,
            "measurement_batch_count": 289,
            "rank_qualified_measurement_batch_count": 289,
            "shared_canonical_protein_count": 25,
            "external_candidate_positive_target_cell_count": 4169,
        }
        actual = {
            "source_cell_count": source_cells,
            "positive_source_cell_count": all_positive,
            "biological_unit_count": len(units),
            "measurement_batch_count": len(batches),
            "rank_qualified_measurement_batch_count": len(qualified),
            "shared_canonical_protein_count": len(shared),
            "external_candidate_positive_target_cell_count": sum(batch_target_positive.values()),
        }
        if actual != expected:
            raise R4ManchesterNanoOmicError(f"Manchester source accounting differs: {actual}")
        for row in rows:
            row["rank_qualified_measurement_batch"] = (
                "true" if row["measurement_batch_id"] in qualified else "false"
            )
        return rows, {
            **actual,
            "qualified_batches": sorted(qualified),
            "target_accessions": sorted(shared),
            "source_files": {
                path.name: {
                    "relative_path": path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(path),
                }
                for path in files.values()
            },
        }

    def audit(self, *, strict: bool = False) -> R4ManchesterNanoOmicSummary:
        if not strict:
            raise R4ManchesterNanoOmicError("Manchester source audit requires --strict")
        rows, accounting = self._build_source_map()
        map_path = self.root / self.SOURCE_MAP_RELATIVE
        self._write_csv(
            map_path,
            [
                "source_id",
                "laboratory_anchor",
                "canonical_accession",
                "source_identifier",
                "biological_unit_id",
                "cohort",
                "timepoint",
                "measurement_batch_id",
                "source_file",
                "source_row",
                "source_coordinate",
                "author_quantity_type",
                "author_numeric_value",
                "author_value_state",
                "rank_target_eligible",
                "analysis_candidate_eligible",
                "rank_qualified_measurement_batch",
            ],
            rows,
        )
        output = self.root / self.AUDIT_OUTPUT_RELATIVE
        output.mkdir(parents=True, exist_ok=False)
        report_path = output / "r4_manchester_nanoomic_source_report.json"
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": "R4_MANCHESTER_NANOOMIC_SOURCE_AUDITED_ANALYSIS_ONLY",
            "evidence_class": "EXTERNAL_PUBLIC_ANALYSIS_ONLY",
            "allowed_claim_level": "EXPLORATORY",
            "article": {
                "pmcid": "PMC13212878",
                "doi": "10.1038/s43856-026-01552-3",
                "title": (
                    "Longitudinal plasma nano-proteomics reveals acute systemic responses "
                    "to radiotherapy and predictive biomarkers of late toxicity"
                ),
                "full_text_locator": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13212878/",
                "data_locator": "https://github.com/assisalam/nanoOmic",
                "proteomexchange": "PXD071492",
                "article_license": "CC-BY-4.0",
            },
            "source_scope": {
                "source_id": self.SOURCE_ID,
                "laboratory_anchor": self.LABORATORY,
                "biofluid": "human plasma",
                "particle": "liposome protein corona",
                "source_unit": "patient-by-timepoint matrix column",
                "independent_biological_unit": (
                    "deidentified patient ID, clustered across timepoints"
                ),
                "target_resolution": (
                    "gene name resolved to one frozen R3 UniProt canonical accession"
                ),
            },
            "source_access_condition": {
                "status": "PUBLIC_ANALYSIS_ONLY_NO_REPOSITORY_LICENSE_ASSERTION",
                "raw_matrix_redistribution": "PROHIBITED_BY_THIS_WORKFLOW",
                "public_release_eligible": False,
                "reason": (
                    "the article is CC-BY-4.0 but the author GitHub repository has no "
                    "explicit repository license; retain source locally and publish "
                    "only hashes and summary receipts"
                ),
            },
            "input_references": accounting["source_files"],
            "source_map": {
                "relative_path": map_path.relative_to(self.root).as_posix(),
                "sha256": _sha256(map_path),
            },
            "accounting": {
                key: value for key, value in accounting.items() if key != "qualified_batches"
            },
            "claim_boundary": (
                "Author-run exploratory external OOD only; not a protected lockbox, "
                "independent evaluator receipt, no-author reproduction, clinical "
                "validation or submission-readiness evidence."
            ),
            "model_fitted": False,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        self._write_json(report_path, report)
        receipt_path = output / "r4_manchester_nanoomic_source_receipt.json"
        self._write_json(
            receipt_path,
            {
                "schema_version": 1,
                "audit_id": self.AUDIT_ID,
                "status": report["status"],
                "report_sha256": _sha256(report_path),
                "source_map": report["source_map"],
                **report["accounting"],
                "model_fitted": False,
                "independent_validation": False,
                "external_scientific_reproduction": False,
                "scientific_submission_ready": False,
            },
        )
        return R4ManchesterNanoOmicSummary(
            accounting["source_cell_count"],
            accounting["positive_source_cell_count"],
            accounting["biological_unit_count"],
            accounting["measurement_batch_count"],
            accounting["rank_qualified_measurement_batch_count"],
            accounting["shared_canonical_protein_count"],
            0,
            0,
            0,
            receipt_path,
        )

    def verify_audit(self) -> R4ManchesterNanoOmicSummary:
        output = self.root / self.AUDIT_OUTPUT_RELATIVE
        report_path = output / "r4_manchester_nanoomic_source_report.json"
        receipt_path = output / "r4_manchester_nanoomic_source_receipt.json"
        report = self._json(report_path, "Manchester source report")
        receipt = self._json(receipt_path, "Manchester source receipt")
        source_map = _mapping(report.get("source_map"), "Manchester source map")
        map_path = self._root_file(
            _string(source_map.get("relative_path"), "source map path"), "source map"
        )
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("report_sha256") != _sha256(report_path)
            or _sha256(map_path) != _checksum(source_map.get("sha256"), "source map")
            or receipt.get("scientific_submission_ready") is not False
            or receipt.get("model_fitted") is not False
        ):
            raise R4ManchesterNanoOmicError("Manchester source audit receipt is invalid")
        accounting = _mapping(report.get("accounting"), "Manchester accounting")
        return R4ManchesterNanoOmicSummary(
            int(accounting["source_cell_count"]),
            int(accounting["positive_source_cell_count"]),
            int(accounting["biological_unit_count"]),
            int(accounting["measurement_batch_count"]),
            int(accounting["rank_qualified_measurement_batch_count"]),
            int(accounting["shared_canonical_protein_count"]),
            0,
            0,
            0,
            receipt_path,
        )

    @staticmethod
    def _rank_percentiles(rows: Sequence[Mapping[str, str]]) -> dict[str, tuple[float, int]]:
        grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
        for row in rows:
            if row.get("rank_target_eligible") == "true":
                grouped[row["measurement_batch_id"]].append(row)
        ranks: dict[str, tuple[float, int]] = {}
        for batch, values in grouped.items():
            ordered = sorted(
                values,
                key=lambda row: (-float(row["author_numeric_value"]), row["source_coordinate"]),
            )
            count = len(ordered)
            start = 0
            while start < count:
                end = start + 1
                while end < count and float(ordered[end]["author_numeric_value"]) == float(
                    ordered[start]["author_numeric_value"]
                ):
                    end += 1
                midrank = (start + 1 + end) / 2.0
                percentile = 0.5 if count == 1 else (count - midrank) / (count - 1)
                for row in ordered[start:end]:
                    ranks[f"{batch}:{row['source_coordinate']}"] = (percentile, count)
                start = end
        return ranks

    @staticmethod
    def _cluster_metrics(
        metrics: Sequence[Mapping[str, Any]], batch_to_unit: Mapping[str, str]
    ) -> tuple[dict[str, float | None], dict[str, dict[str, float | None]]]:
        by_unit: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for metric in metrics:
            by_unit[batch_to_unit[str(metric["measurement_batch_id"])]].append(metric)
        unit_rows: dict[str, dict[str, float | None]] = {}
        for unit, unit_metrics in sorted(by_unit.items()):
            unit_rows[unit] = {
                name: None
                if any(item[name] is None for item in unit_metrics)
                else float(np.mean([float(item[name]) for item in unit_metrics]))
                for name in ("spearman", "mae", "rmse")
            }
        aggregate: dict[str, float | None] = {
            "biological_unit_count": float(len(unit_rows)),
            "measurement_batch_count": float(len(metrics)),
        }
        for name in ("spearman", "mae", "rmse"):
            values = [row[name] for row in unit_rows.values()]
            aggregate[f"subject_equal_mean_{name}"] = (
                None
                if any(value is None for value in values)
                else float(np.mean([float(value) for value in values]))
            )
        spearman_values = [item["spearman"] for item in metrics]
        aggregate["batch_weighted_mean_spearman"] = (
            None
            if any(value is None for value in spearman_values)
            else float(np.mean([float(value) for value in spearman_values]))
        )
        return aggregate, unit_rows

    @staticmethod
    def _cluster_bootstrap(
        unit_rows: Mapping[str, Mapping[str, float | None]], metric: str, seed: int
    ) -> tuple[float, float] | None:
        values = np.asarray(
            [float(row[metric]) for row in unit_rows.values() if row[metric] is not None],
            dtype=float,
        )
        if len(values) != len(unit_rows):
            return None
        rng = np.random.default_rng(seed)
        samples = values[rng.integers(0, len(values), size=(2000, len(values)))].mean(axis=1)
        interval = np.quantile(samples, [0.025, 0.975], method="linear")
        return float(interval[0]), float(interval[1])

    def _external_observations(
        self, feature_values: Mapping[str, tuple[float, ...]], protocol: Mapping[str, Any]
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, str]]:
        source_map = self._root_file(self.SOURCE_MAP_RELATIVE, "Manchester source map")
        rows = self._read_csv(source_map, "Manchester source map")
        ranks = self._rank_percentiles(rows)
        batch_to_unit = {row["measurement_batch_id"]: row["biological_unit_id"] for row in rows}
        target_positive: dict[str, int] = defaultdict(int)
        for row in rows:
            if row.get("analysis_candidate_eligible") == "true":
                target_positive[row["measurement_batch_id"]] += 1
        qualified = {batch for batch, count in target_positive.items() if count >= 10}
        observations: list[_Observation] = []
        target_rows: list[dict[str, Any]] = []
        for row in rows:
            if (
                row.get("analysis_candidate_eligible") != "true"
                or row["measurement_batch_id"] not in qualified
            ):
                continue
            rank = ranks.get(f"{row['measurement_batch_id']}:{row['source_coordinate']}")
            accession = row.get("canonical_accession", "")
            if rank is None or accession not in feature_values:
                continue
            percentile, positive_count = rank
            target_id = f"R4MANCHESTER:{row['measurement_batch_id']}:{row['source_coordinate']}"
            observations.append(
                _Observation(
                    target_id,
                    self.SOURCE_ID,
                    accession,
                    self.LABORATORY,
                    row["measurement_batch_id"],
                    percentile,
                    feature_values[accession],
                )
            )
            target_rows.append(
                {
                    "external_target_observation_id": target_id,
                    "source_id": self.SOURCE_ID,
                    "laboratory_anchor": self.LABORATORY,
                    "canonical_accession": accession,
                    "source_identifier": row["source_identifier"],
                    "biological_unit_id": row["biological_unit_id"],
                    "cohort": row["cohort"],
                    "timepoint": row["timepoint"],
                    "measurement_batch_id": row["measurement_batch_id"],
                    "source_file": row["source_file"],
                    "source_row": row["source_row"],
                    "source_coordinate": row["source_coordinate"],
                    "author_quantity_type": row["author_quantity_type"],
                    "author_numeric_value": row["author_numeric_value"],
                    "rank_percentile_descending": percentile,
                    "measurement_batch_positive_protein_count": positive_count,
                }
            )
        expected = protocol["external_evaluation"]
        if (
            len(observations) != expected["expected_external_observation_count"]
            or len(qualified) != expected["expected_measurement_batch_count"]
        ):
            raise R4ManchesterNanoOmicError("Manchester external observation accounting differs")
        return observations, target_rows, batch_to_unit

    def evaluate(self, *, strict: bool = False) -> R4ManchesterNanoOmicSummary:
        if not strict:
            raise R4ManchesterNanoOmicError("Manchester OOD requires --strict")
        if self.output_root.exists():
            raise R4ManchesterNanoOmicError("Manchester OOD output already exists")
        protocol_path = self.root / self.PROTOCOL_RELATIVE
        protocol = self._json(protocol_path, "Manchester OOD protocol")
        self.verify_audit()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.root / "data/raw").verify()
        except (R3AnalysisProtocolError, OSError) as exc:
            raise R4ManchesterNanoOmicError("frozen R3 protocol does not verify") from exc
        helper = R3ModelEvaluationWorkflow(
            self.root, self.root / "data/raw", self.root / "data/raw/r3_uniprot_sequence_features"
        )
        try:
            development, accessions = helper._observations(
                self.root / "data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv",
                self.root / "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/"
                "R3_uniprot_sequence_features.csv",
            )
        except R3ModelEvaluationError as exc:
            raise R4ManchesterNanoOmicError("frozen R3 development data is invalid") from exc
        if len(development) != 2724 or len(accessions) != 99:
            raise R4ManchesterNanoOmicError("frozen R3 development accounting differs")
        feature_values = {row.canonical_accession: row.feature_values for row in development}
        external, target_rows, batch_to_unit = self._external_observations(feature_values, protocol)
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(
            helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES
        )
        full_alpha, full_selection = helper._select_alpha(
            development, full_indices, minimum_proteins=10
        )
        composition_alpha, composition_selection = helper._select_alpha(
            development, composition_indices, minimum_proteins=10
        )
        constant_mean = float(np.mean([row.target for row in development]))
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
        predictions = {
            "CONSTANT_TRAINING_MEAN": np.full(len(external), constant_mean, dtype=float),
            "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, external),
            "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, external),
        }
        model_rows: list[dict[str, Any]] = []
        batch_rows: list[dict[str, Any]] = []
        prediction_rows: list[dict[str, Any]] = []
        metric_by_model_batch: dict[tuple[str, str], dict[str, Any]] = {}
        for index, model_id in enumerate(helper.MODEL_IDS, start=1):
            metrics = helper._batch_metrics(external, predictions[model_id], minimum_proteins=10)
            aggregate, unit_rows = self._cluster_metrics(metrics, batch_to_unit)
            spearman_ci = self._cluster_bootstrap(unit_rows, "spearman", 20260820 + index)
            mae_ci = self._cluster_bootstrap(unit_rows, "mae", 20260820 + index + 10)
            rmse_ci = self._cluster_bootstrap(unit_rows, "rmse", 20260820 + index + 20)
            model_rows.append(
                {
                    "model_id": model_id,
                    "external_observation_count": len(external),
                    "external_measurement_batch_count": len(metrics),
                    "biological_unit_count": int(aggregate["biological_unit_count"]),
                    "primary_metric_status": "UNDEFINED_CONSTANT_PREDICTION"
                    if model_id == "CONSTANT_TRAINING_MEAN"
                    else "DEFINED",
                    **aggregate,
                    "subject_equal_mean_spearman_lower_95": None
                    if spearman_ci is None
                    else spearman_ci[0],
                    "subject_equal_mean_spearman_upper_95": None
                    if spearman_ci is None
                    else spearman_ci[1],
                    "subject_equal_mean_mae_lower_95": None if mae_ci is None else mae_ci[0],
                    "subject_equal_mean_mae_upper_95": None if mae_ci is None else mae_ci[1],
                    "subject_equal_mean_rmse_lower_95": None if rmse_ci is None else rmse_ci[0],
                    "subject_equal_mean_rmse_upper_95": None if rmse_ci is None else rmse_ci[1],
                }
            )
            for metric in metrics:
                metric_by_model_batch[(model_id, metric["measurement_batch_id"])] = metric
                batch_rows.append(
                    {
                        "model_id": model_id,
                        **metric,
                        "biological_unit_id": batch_to_unit[metric["measurement_batch_id"]],
                    }
                )
            for observation, prediction in zip(external, predictions[model_id], strict=True):
                prediction_rows.append(
                    {
                        "model_id": model_id,
                        "external_target_observation_id": observation.target_observation_id,
                        "canonical_accession": observation.canonical_accession,
                        "measurement_batch_id": observation.measurement_batch_id,
                        "biological_unit_id": batch_to_unit[observation.measurement_batch_id],
                        "observed_rank_percentile_descending": observation.target,
                        "predicted_rank_percentile_descending": float(prediction),
                    }
                )
        full_primary = next(
            row["subject_equal_mean_spearman"]
            for row in model_rows
            if row["model_id"] == "SEQUENCE_RIDGE_FULL"
        )
        paired_batches = sorted(
            {batch for model, batch in metric_by_model_batch if model == "SEQUENCE_RIDGE_FULL"}
        )
        paired_by_unit: dict[str, list[float]] = defaultdict(list)
        paired = []
        for batch in paired_batches:
            difference = float(
                metric_by_model_batch[("SEQUENCE_RIDGE_FULL", batch)]["spearman"]
            ) - float(metric_by_model_batch[("SEQUENCE_RIDGE_COMPOSITION_ONLY", batch)]["spearman"])
            paired.append(difference)
            paired_by_unit[batch_to_unit[batch]].append(difference)
        paired_unit_means = [float(np.mean(values)) for _, values in sorted(paired_by_unit.items())]
        paired_ci = helper._bootstrap(paired_unit_means, resamples=2000, seed=202615)
        by_development_batch: dict[str, list[int]] = defaultdict(list)
        for position, observation in enumerate(development):
            by_development_batch[observation.measurement_batch_id].append(position)
        observed = np.asarray([row.target for row in development], dtype=float)
        rng = np.random.default_rng(202616)
        null_scores: list[float] = []
        null_rows: list[dict[str, Any]] = []
        for resample in range(1, 257):
            permuted = observed.copy()
            for indices in by_development_batch.values():
                permuted[indices] = rng.permutation(permuted[indices])
            permuted_development = [
                _Observation(
                    row.target_observation_id,
                    row.source_id,
                    row.canonical_accession,
                    row.laboratory_anchor,
                    row.measurement_batch_id,
                    float(target),
                    row.feature_values,
                )
                for row, target in zip(development, permuted, strict=True)
            ]
            permuted_alpha, _ = helper._select_alpha(
                permuted_development, full_indices, minimum_proteins=10
            )
            null_model = helper._fit_ridge(
                permuted_development, full_indices, permuted_alpha, targets=permuted
            )
            null_metrics, _ = self._cluster_metrics(
                helper._batch_metrics(
                    external, helper._predict_ridge(null_model, external), minimum_proteins=10
                ),
                batch_to_unit,
            )
            score = null_metrics["subject_equal_mean_spearman"]
            if score is None:
                raise R4ManchesterNanoOmicError(
                    "Manchester negative control has undefined Spearman"
                )
            null_scores.append(float(score))
            null_rows.append(
                {
                    "resample": resample,
                    "selected_alpha": permuted_alpha,
                    "null_subject_equal_mean_spearman": float(score),
                }
            )
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        paths = {
            "external_target_ledger": output / "r4_manchester_rank_target_ledger.csv",
            "predictions": output / "r4_manchester_ood_predictions.csv",
            "batch_metrics": output / "r4_manchester_measurement_batch_metrics.csv",
            "model_metrics": output / "r4_manchester_ood_model_metrics.csv",
            "selection": output / "r4_manchester_nested_selection.csv",
            "negative_control": output / "r4_manchester_within_batch_permutation.csv",
            "parameters": output / "r4_manchester_model_parameters.json",
        }
        self._write_csv(paths["external_target_ledger"], self.TARGET_FIELDS, target_rows)
        self._write_csv(
            paths["predictions"],
            [
                "model_id",
                "external_target_observation_id",
                "canonical_accession",
                "measurement_batch_id",
                "biological_unit_id",
                "observed_rank_percentile_descending",
                "predicted_rank_percentile_descending",
            ],
            prediction_rows,
        )
        self._write_csv(
            paths["batch_metrics"],
            [
                "model_id",
                "measurement_batch_id",
                "biological_unit_id",
                "protein_count",
                "spearman",
                "mae",
                "rmse",
            ],
            batch_rows,
        )
        self._write_csv(paths["model_metrics"], list(model_rows[0]), model_rows)
        self._write_csv(
            paths["selection"],
            ["model_id", "alpha", "held_out_inner_batch_id", "spearman", "selected_alpha"],
            [
                {"model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha}
                for row in full_selection
            ]
            + [
                {
                    "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
                    **row,
                    "selected_alpha": composition_alpha,
                }
                for row in composition_selection
            ],
        )
        self._write_csv(
            paths["negative_control"],
            ["resample", "selected_alpha", "null_subject_equal_mean_spearman"],
            null_rows,
        )
        negative = {
            "observed_subject_equal_mean_spearman": full_primary,
            "null_mean": float(np.mean(null_scores)),
            "null_lower_95": float(np.quantile(null_scores, 0.025)),
            "null_upper_95": float(np.quantile(null_scores, 0.975)),
            "one_sided_upper_tail_p": float(
                (1 + sum(value >= full_primary for value in null_scores)) / (1 + len(null_scores))
            ),
            "resamples": 256,
            "random_seed": 202616,
            "statistic": "subject_equal_mean_spearman_across_61_patient_clusters",
            "selection_reexecuted_per_resample": True,
        }
        self._write_json(
            paths["parameters"],
            {
                "development_observation_count": len(development),
                "external_observation_count": len(external),
                "SEQUENCE_RIDGE_FULL": {
                    **helper._ridge_parameters(full_model, helper.FEATURE_NAMES),
                    "negative_control": negative,
                },
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._ridge_parameters(
                    composition_model, helper.COMPOSITION_FEATURE_NAMES
                ),
            },
        )
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
        }
        report_path = output / "r4_manchester_nanoomic_ood_report.json"
        report = {
            "schema_version": 1,
            "audit_id": self.OOD_AUDIT_ID,
            "protocol_id": protocol.get("protocol_id"),
            "protocol_sha256": _sha256(protocol_path),
            "status": "R4_MANCHESTER_NANOOMIC_OOD_EXECUTED_EXPLORATORY",
            "evidence_class": "EXTERNAL_PUBLIC_ANALYSIS_ONLY",
            "allowed_claim_level": "EXPLORATORY",
            "development_observation_count": len(development),
            "development_canonical_protein_count": len(accessions),
            "external_observation_count": len(external),
            "external_shared_canonical_protein_count": len(
                {row.canonical_accession for row in external}
            ),
            "external_measurement_batch_count": len({row.measurement_batch_id for row in external}),
            "biological_unit_count": len(set(batch_to_unit.values())),
            "laboratory_anchor_count": 1,
            "model_results": model_rows,
            "paired_composition_ablation": {
                "paired_measurement_batch_count": len(paired),
                "paired_patient_cluster_count": len(paired_unit_means),
                "full_minus_composition_batch_weighted_mean_spearman": float(np.mean(paired)),
                "full_minus_composition_patient_equal_mean_spearman": float(
                    np.mean(paired_unit_means)
                ),
                **paired_ci,
            },
            "negative_control_summary": negative,
            "artifacts": artifacts,
            "claim_boundary": protocol.get("claim_boundary"),
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "public_release_eligible": False,
        }
        self._write_json(report_path, report)
        receipt_path = output / "r4_manchester_nanoomic_ood_receipt.json"
        self._write_json(
            receipt_path,
            {
                "schema_version": 1,
                "audit_id": self.OOD_AUDIT_ID,
                "status": report["status"],
                "report_sha256": _sha256(report_path),
                "development_observation_count": len(development),
                "external_observation_count": len(external),
                "external_shared_canonical_protein_count": report[
                    "external_shared_canonical_protein_count"
                ],
                "external_measurement_batch_count": report["external_measurement_batch_count"],
                "biological_unit_count": report["biological_unit_count"],
                "model_count": len(helper.MODEL_IDS),
                "model_fitted": True,
                "independent_validation": False,
                "external_scientific_reproduction": False,
                "scientific_submission_ready": False,
                "public_release_eligible": False,
            },
        )
        return R4ManchesterNanoOmicSummary(
            193971,
            177636,
            report["biological_unit_count"],
            report["external_measurement_batch_count"],
            report["external_measurement_batch_count"],
            report["external_shared_canonical_protein_count"],
            len(external),
            report["external_measurement_batch_count"],
            len(helper.MODEL_IDS),
            receipt_path,
        )

    def verify_ood(self) -> R4ManchesterNanoOmicSummary:
        output = self.output_root
        report_path = output / "r4_manchester_nanoomic_ood_report.json"
        receipt_path = output / "r4_manchester_nanoomic_ood_receipt.json"
        report = self._json(report_path, "Manchester OOD report")
        receipt = self._json(receipt_path, "Manchester OOD receipt")
        artifacts = _mapping(report.get("artifacts"), "Manchester OOD artifacts")
        if not artifacts:
            raise R4ManchesterNanoOmicError("Manchester OOD artifacts are empty")
        for value in artifacts.values():
            item = _mapping(value, "Manchester OOD artifact")
            path = self._root_file(_string(item.get("relative_path"), "artifact path"), "artifact")
            if _sha256(path) != _checksum(item.get("sha256"), "artifact checksum"):
                raise R4ManchesterNanoOmicError("Manchester OOD artifact checksum differs")
        if (
            report.get("audit_id") != self.OOD_AUDIT_ID
            or receipt.get("audit_id") != self.OOD_AUDIT_ID
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("model_fitted") is not True
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
            or receipt.get("public_release_eligible") is not False
        ):
            raise R4ManchesterNanoOmicError("Manchester OOD receipt boundary is invalid")
        return R4ManchesterNanoOmicSummary(
            193971,
            177636,
            int(receipt["biological_unit_count"]),
            int(receipt["external_measurement_batch_count"]),
            int(receipt["external_measurement_batch_count"]),
            int(receipt["external_shared_canonical_protein_count"]),
            int(receipt["external_observation_count"]),
            int(receipt["external_measurement_batch_count"]),
            int(receipt["model_count"]),
            receipt_path,
        )

    @staticmethod
    def _cluster_metric_rows(
        metrics: Sequence[Mapping[str, Any]], batch_to_unit: Mapping[str, str]
    ) -> list[dict[str, float]]:
        by_unit: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for metric in metrics:
            by_unit[batch_to_unit[str(metric["measurement_batch_id"])]].append(metric)
        rows: list[dict[str, float]] = []
        for values in by_unit.values():
            rows.append(
                {
                    "subject_equal_mean_spearman": float(
                        np.mean(
                            [
                                float(row["spearman"])
                                for row in values
                                if row["spearman"] is not None
                            ]
                        )
                    )
                }
            )
        return rows
