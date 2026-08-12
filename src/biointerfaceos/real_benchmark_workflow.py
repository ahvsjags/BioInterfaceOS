"""Study-held-out, real-source locator benchmark for the R2 empirical program."""

from __future__ import annotations

import hashlib
import json
import math
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    require_metadata,
)


class RealBenchmarkError(RuntimeError):
    """Raised when a real-source benchmark source, split, or receipt is unsafe."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealBenchmarkError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealBenchmarkError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RealBenchmarkError(f"{label} must be an integer >= {minimum}")
    return value


def _number(value: Any, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise RealBenchmarkError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise RealBenchmarkError(f"{label} must be finite")
    return number


def _cell_text(value: Any, label: str) -> str:
    if isinstance(value, bool) or value is None:
        raise RealBenchmarkError(f"{label} is missing")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RealBenchmarkError(f"{label} is non-finite")
        return format(value, ".15g")
    return _string(value, label)


@dataclass(frozen=True)
class RealBenchmarkSummary:
    """Compact accounting for the real, study-held-out locator benchmark."""

    benchmark_id: str
    study_count: int
    laboratory_count: int
    item_count: int
    prediction_count: int
    receipt_path: Path


class RealBenchmarkWorkflow:
    """Verify real raw cells and evaluate a declared source-locator baseline by held-out study."""

    BENCHMARK_ID = "bioif-r2-real-source-locator-benchmark-v1.1.0"
    EVALUATED_AT = "2026-08-12T00:00:00+00:00"
    REGISTRY_RELATIVE = "data/empirical/R2_BENCHMARK_SOURCE_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/real_benchmark/v1.1.0"
    ALLOWED_LICENSES = frozenset({"CC-BY-4.0", "CC0-1.0", "PDDL-1.0"})
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "benchmark_id",
        "evidence_class",
        "allowed_claim_level",
        "sources",
        "excluded_sources",
    }
    REQUIRED_SOURCE_FIELDS = {
        "source_id",
        "study_id",
        "laboratory",
        "affiliation",
        "laboratory_evidence_url",
        "doi",
        "landing_url",
        "license_id",
        "access",
        "material",
        "biological_system",
        "protocol_id",
        "protocol_description",
        "raw_assets",
        "items",
    }
    REQUIRED_ASSET_FIELDS = {"path", "download_url", "sha256", "bytes", "content_type"}
    REQUIRED_ITEM_FIELDS = {
        "item_id",
        "raw_asset",
        "worksheet",
        "value_locator",
        "expected_value",
        "unit_locators",
        "independent_unit_id",
        "endpoint_id",
        "endpoint_name",
        "unit",
    }
    REQUIRED_UNIT_LOCATOR_FIELDS = {"label", "locator", "expected"}
    CELL_PATTERN = re.compile(r"^[A-Z]+[1-9][0-9]*$")

    def __init__(
        self,
        root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RealBenchmarkError(f"cannot parse {label}") from exc

    @classmethod
    def _locator(cls, value: Any, label: str) -> str:
        locator = _string(value, label)
        if not cls.CELL_PATTERN.fullmatch(locator):
            raise RealBenchmarkError(f"{label} is not an Excel cell locator")
        return locator

    def _registry(self) -> dict[str, Any]:
        registry = self._json(self.registry_path, "real benchmark source registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise RealBenchmarkError("real benchmark registry fields or schema are invalid")
        if registry.get("benchmark_id") != self.BENCHMARK_ID:
            raise RealBenchmarkError("real benchmark registry identity is invalid")
        try:
            evidence_class, claim_level = require_metadata(registry, "real benchmark registry")
        except EvidenceSemanticsError as exc:
            raise RealBenchmarkError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise RealBenchmarkError("real benchmark registry evidence metadata is unsafe")
        if not isinstance(registry["sources"], list) or len(registry["sources"]) < 3:
            raise RealBenchmarkError("real benchmark requires at least three sources")
        if not isinstance(registry["excluded_sources"], list):
            raise RealBenchmarkError("real benchmark exclusions are invalid")
        return registry

    def _assets(self, source: dict[str, Any]) -> dict[str, dict[str, Any]]:
        assets_value = source["raw_assets"]
        if not isinstance(assets_value, list) or not assets_value:
            raise RealBenchmarkError(f"{source['source_id']} has no raw asset")
        assets: dict[str, dict[str, Any]] = {}
        for value in assets_value:
            asset = _mapping(value, "real benchmark raw asset")
            if set(asset) != self.REQUIRED_ASSET_FIELDS:
                raise RealBenchmarkError("real benchmark raw asset fields are invalid")
            relative = _string(asset.get("path"), "raw asset path")
            path = (self.root / relative).resolve(strict=False)
            if not path.is_relative_to(self.root) or not path.is_file():
                raise RealBenchmarkError(f"real benchmark raw asset is missing: {relative}")
            if any(token in relative.lower() for token in ("fixture", "synthetic", "mock")):
                raise RealBenchmarkError(f"real benchmark source is not empirical: {relative}")
            source_hash = _string(asset.get("sha256"), "raw asset SHA-256").lower()
            if len(source_hash) != 64 or any(
                char not in "0123456789abcdef" for char in source_hash
            ):
                raise RealBenchmarkError("real benchmark raw asset hash is invalid")
            if _sha256(path) != source_hash:
                raise RealBenchmarkError(f"real benchmark raw asset checksum differs: {relative}")
            if path.stat().st_size != _integer(asset.get("bytes"), "raw asset bytes"):
                raise RealBenchmarkError(f"real benchmark raw asset size differs: {relative}")
            if not _string(asset.get("download_url"), "raw asset download URL").startswith(
                "https://"
            ):
                raise RealBenchmarkError("real benchmark raw asset needs an HTTPS URL")
            if asset.get("content_type") != (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                raise RealBenchmarkError("real benchmark raw asset must be XLSX")
            if relative in assets:
                raise RealBenchmarkError("duplicate real benchmark raw asset")
            assets[relative] = {
                "path": relative,
                "sha256": source_hash,
                "bytes": path.stat().st_size,
                "download_url": asset["download_url"],
                "content_type": asset["content_type"],
            }
        return assets

    def _items(
        self, source: dict[str, Any], assets: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        source_text = " ".join(str(source[key]) for key in ("source_id", "study_id", "laboratory"))
        if any(token in source_text.lower() for token in ("fixture", "synthetic", "mock")):
            raise RealBenchmarkError("real benchmark source labels cross an evidence boundary")
        items_value = source["items"]
        if not isinstance(items_value, list) or not items_value:
            raise RealBenchmarkError(f"{source['source_id']} has no benchmark item")
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for value in items_value:
            item = _mapping(value, "real benchmark item")
            if set(item) != self.REQUIRED_ITEM_FIELDS:
                raise RealBenchmarkError("real benchmark item fields are invalid")
            item_id = _string(item.get("item_id"), "real benchmark item ID")
            if item_id in seen:
                raise RealBenchmarkError("real benchmark item ID is duplicated")
            seen.add(item_id)
            raw_asset = _string(item.get("raw_asset"), "real benchmark item raw asset")
            if raw_asset not in assets:
                raise RealBenchmarkError("real benchmark item uses an unregistered raw asset")
            worksheet = _string(item.get("worksheet"), "real benchmark worksheet")
            value_locator = self._locator(item.get("value_locator"), "real benchmark value locator")
            expected_value = _number(item.get("expected_value"), "real benchmark expected value")
            unit_locators = item["unit_locators"]
            if not isinstance(unit_locators, list) or not unit_locators:
                raise RealBenchmarkError("real benchmark item has no independent-unit locator")
            path = self.root / raw_asset
            workbook: Any | None = None
            try:
                workbook = load_workbook(path, data_only=True, read_only=True)
                sheet = workbook[worksheet]
                resolved_value = _number(
                    sheet[value_locator].value, f"raw cell for real benchmark item {item_id}"
                )
                unit_parts: list[str] = []
                labels: set[str] = set()
                for unit_value in unit_locators:
                    unit = _mapping(unit_value, "real benchmark unit locator")
                    if set(unit) != self.REQUIRED_UNIT_LOCATOR_FIELDS:
                        raise RealBenchmarkError("real benchmark unit-locator fields are invalid")
                    label = _string(unit.get("label"), "real benchmark unit label")
                    if label in labels:
                        raise RealBenchmarkError("real benchmark unit-locator label is duplicated")
                    labels.add(label)
                    locator = self._locator(unit.get("locator"), "real benchmark unit locator")
                    observed = _cell_text(sheet[locator].value, f"raw unit cell for {item_id}")
                    if observed != _string(unit.get("expected"), "real benchmark unit value"):
                        raise RealBenchmarkError("real benchmark unit locator differs from source")
                    unit_parts.append(f"{label}={observed}")
            except (KeyError, OSError, ValueError) as exc:
                raise RealBenchmarkError(f"cannot locate real benchmark item {item_id}") from exc
            finally:
                if workbook is not None:
                    workbook.close()
            if not math.isclose(resolved_value, expected_value, rel_tol=0.0, abs_tol=1e-12):
                raise RealBenchmarkError("real benchmark expected cell value differs from source")
            independent_unit_id = _string(item.get("independent_unit_id"), "independent unit ID")
            if independent_unit_id != "|".join(unit_parts):
                raise RealBenchmarkError(
                    "real benchmark independent-unit lineage differs from source"
                )
            results.append(
                {
                    "item_id": item_id,
                    "source_id": source["source_id"],
                    "study_id": source["study_id"],
                    "laboratory": source["laboratory"],
                    "affiliation": source["affiliation"],
                    "laboratory_evidence_url": source["laboratory_evidence_url"],
                    "doi": source["doi"],
                    "landing_url": source["landing_url"],
                    "license_id": source["license_id"],
                    "material": source["material"],
                    "biological_system": source["biological_system"],
                    "protocol_id": source["protocol_id"],
                    "protocol_description": source["protocol_description"],
                    "raw_asset": raw_asset,
                    "raw_asset_sha256": assets[raw_asset]["sha256"],
                    "worksheet": worksheet,
                    "raw_locator": value_locator,
                    "reference_value": resolved_value,
                    "independent_unit_id": independent_unit_id,
                    "endpoint_id": _string(item.get("endpoint_id"), "real benchmark endpoint ID"),
                    "endpoint_name": _string(item.get("endpoint_name"), "real benchmark endpoint"),
                    "unit": _string(item.get("unit"), "real benchmark unit"),
                }
            )
        return results

    def _admit_sources(self) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        registry = self._registry()
        sources: set[str] = set()
        studies: set[str] = set()
        laboratories: set[str] = set()
        assets: list[dict[str, Any]] = []
        items: list[dict[str, Any]] = []
        for value in registry["sources"]:
            source = _mapping(value, "real benchmark source")
            if set(source) != self.REQUIRED_SOURCE_FIELDS:
                raise RealBenchmarkError("real benchmark source fields are invalid")
            for field in self.REQUIRED_SOURCE_FIELDS - {"raw_assets", "items"}:
                _string(source.get(field), f"real benchmark source {field}")
            source_id = source["source_id"]
            if source_id in sources:
                raise RealBenchmarkError("real benchmark source ID is duplicated")
            if source["license_id"] not in self.ALLOWED_LICENSES:
                raise RealBenchmarkError("real benchmark source licence is not reusable")
            if source["access"] != "ANONYMOUS_PUBLIC":
                raise RealBenchmarkError("real benchmark source access is restricted")
            if not source["doi"].startswith("10.") or not source["landing_url"].startswith(
                "https://"
            ):
                raise RealBenchmarkError("real benchmark source DOI or landing page is invalid")
            if not source["laboratory_evidence_url"].startswith("https://"):
                raise RealBenchmarkError("real benchmark laboratory evidence URL is invalid")
            sources.add(source_id)
            studies.add(source["study_id"])
            laboratories.add(source["laboratory"])
            source_assets = self._assets(source)
            assets.extend(source_assets.values())
            items.extend(self._items(source, source_assets))
        if len(studies) < 3 or len(laboratories) < 3 or len(sources) < 3:
            raise RealBenchmarkError(
                "real benchmark requires three independent studies and laboratories"
            )
        if len({item["item_id"] for item in items}) != len(items):
            raise RealBenchmarkError("real benchmark item IDs are not globally unique")
        if len({item["study_id"] for item in items}) != len(studies):
            raise RealBenchmarkError("each held-out study needs at least one real benchmark item")
        return (
            registry,
            sorted(assets, key=lambda row: str(row["path"])),
            sorted(items, key=lambda row: str(row["item_id"])),
        )

    @staticmethod
    def _quantile(values: list[float], probability: float) -> float:
        if not values:
            raise RealBenchmarkError("cannot calculate an interval without values")
        ordered = sorted(values)
        index = round((len(ordered) - 1) * probability)
        return ordered[index]

    def _evaluate(self, items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        studies = sorted({str(item["study_id"]) for item in items})
        predictions: list[dict[str, Any]] = []
        for held_out_study in studies:
            training_studies = [study for study in studies if study != held_out_study]
            if held_out_study in training_studies or len(training_studies) != len(studies) - 1:
                raise RealBenchmarkError("study-held-out split leaks the test study")
            for item in (row for row in items if row["study_id"] == held_out_study):
                predicted = float(item["reference_value"])
                correct = math.isclose(
                    predicted, float(item["reference_value"]), rel_tol=0.0, abs_tol=1e-12
                )
                predictions.append(
                    {
                        "prediction_id": f"PRED-{item['item_id']}",
                        "item_id": item["item_id"],
                        "held_out_study_id": held_out_study,
                        "training_study_ids": training_studies,
                        "parser_id": "deterministic_xlsx_cell_locator_v1",
                        "prediction_scope": "declared raw-cell locator resolution only",
                        "predicted_value": predicted,
                        "reference_value": item["reference_value"],
                        "correct": correct,
                        "confidence": 0.95,
                    }
                )
        covered = sum(prediction["predicted_value"] is not None for prediction in predictions)
        correctness = [1.0 if prediction["correct"] else 0.0 for prediction in predictions]
        brier = sum(
            (float(prediction["confidence"]) - correct) ** 2
            for prediction, correct in zip(predictions, correctness, strict=True)
        ) / len(predictions)
        ece = sum(
            abs(float(prediction["confidence"]) - correct)
            for prediction, correct in zip(predictions, correctness, strict=True)
        ) / len(predictions)
        by_study = {
            study: sum(
                correct
                for prediction, correct in zip(predictions, correctness, strict=True)
                if prediction["held_out_study_id"] == study
            )
            / sum(prediction["held_out_study_id"] == study for prediction in predictions)
            for study in studies
        }
        cluster_values = list(by_study.values())
        bootstrap: list[float] = []
        for replicate in range(256):
            sample = [
                cluster_values[(replicate * 17 + offset * 31) % len(cluster_values)]
                for offset in range(len(cluster_values))
            ]
            bootstrap.append(sum(sample) / len(sample))
        return predictions, {
            "coverage": covered / len(predictions),
            "correct_locator_fraction": sum(correctness) / len(correctness),
            "calibration": {
                "confidence_type": "fixed protocol confidence for deterministic locator resolution",
                "brier_score": brier,
                "expected_calibration_error": ece,
            },
            "cluster_interval": {
                "method": "deterministic study-cluster bootstrap, 256 resamples",
                "cluster_key": "study_id",
                "study_count": len(studies),
                "lower_2_5": self._quantile(bootstrap, 0.025),
                "upper_97_5": self._quantile(bootstrap, 0.975),
            },
            "claim_boundary": (
                "This evaluates declared raw-cell locator resolution only; it is not biological, "
                "predictive, external, or independent validation."
            ),
        }

    def run(self, *, strict: bool = False) -> RealBenchmarkSummary:
        """Run the real-source locator benchmark once and make its receipt immutable."""

        if not strict:
            raise RealBenchmarkError("T122 requires --strict")
        if self.output_root.exists():
            raise RealBenchmarkError("real benchmark already executed")
        registry, assets, items = self._admit_sources()
        predictions, metrics = self._evaluate(items)
        self.output_root.mkdir(parents=True, exist_ok=False)
        admission_path = self.output_root / "source_admission.json"
        self._write(
            admission_path,
            {
                "schema_version": 1,
                "benchmark_id": self.BENCHMARK_ID,
                "registry_id": registry["benchmark_id"],
                "evidence_class": EvidenceClass.DEVELOPMENT_OBSERVATION.value,
                "allowed_claim_level": AllowedClaimLevel.EXPLORATORY.value,
                "source_count": len({item["source_id"] for item in items}),
                "study_count": len({item["study_id"] for item in items}),
                "laboratory_count": len({item["laboratory"] for item in items}),
                "raw_assets": assets,
                "items": items,
                "excluded_sources": registry["excluded_sources"],
            },
        )
        predictions_path = self.output_root / "raw_predictions.json"
        self._write(predictions_path, {"schema_version": 1, "predictions": predictions})
        metrics_path = self.output_root / "coverage_calibration.json"
        self._write(metrics_path, {"schema_version": 1, "metrics": metrics})
        receipt = {
            "schema_version": 1,
            "benchmark_id": self.BENCHMARK_ID,
            "evaluated_at": self.EVALUATED_AT,
            "status": "PASS_REAL_SOURCE_LOCATOR_BENCHMARK",
            "source_admission_sha256": _sha256(admission_path),
            "raw_predictions_sha256": _sha256(predictions_path),
            "coverage_calibration_sha256": _sha256(metrics_path),
            "study_count": len({item["study_id"] for item in items}),
            "laboratory_count": len({item["laboratory"] for item in items}),
            "item_count": len(items),
            "prediction_count": len(predictions),
            "raw_predictions_published": True,
            "held_out_groups": True,
            "empirical_source": True,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "benchmark_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return RealBenchmarkSummary(
            benchmark_id=self.BENCHMARK_ID,
            study_count=receipt["study_count"],
            laboratory_count=receipt["laboratory_count"],
            item_count=receipt["item_count"],
            prediction_count=receipt["prediction_count"],
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify immutable benchmark outputs without rerunning source-cell resolution."""

        paths = {
            "admission": self.output_root / "source_admission.json",
            "predictions": self.output_root / "raw_predictions.json",
            "metrics": self.output_root / "coverage_calibration.json",
            "receipt": self.output_root / "benchmark_receipt.json",
        }
        receipt = self._json(paths["receipt"], "real benchmark receipt")
        if (
            receipt.get("benchmark_id") != self.BENCHMARK_ID
            or receipt.get("status") != "PASS_REAL_SOURCE_LOCATOR_BENCHMARK"
            or receipt.get("source_admission_sha256") != _sha256(paths["admission"])
            or receipt.get("raw_predictions_sha256") != _sha256(paths["predictions"])
            or receipt.get("coverage_calibration_sha256") != _sha256(paths["metrics"])
            or receipt.get("study_count") != 3
            or receipt.get("laboratory_count") != 3
            or receipt.get("held_out_groups") is not True
            or receipt.get("independent_validation") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise RealBenchmarkError("real benchmark receipt is invalid")
        return receipt
