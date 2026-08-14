"""Audit a promising two-laboratory protein-corona source pair without admission.

The pair is useful because its primary articles describe human-plasma corona
experiments on 50/100 nm polystyrene particles at UCD and PNNL.  This module
freezes only article-level facts and the missing-data boundary.  It does not
pretend that article prose is a byte-level source map, that two protocols have
the same endpoint, or that either route satisfies the current CC0 cohort rule.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TwoLabCoronaPairRescreenError(RuntimeError):
    """Raised when the bounded two-laboratory pair audit is weakened."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TwoLabCoronaPairRescreenError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwoLabCoronaPairRescreenError(f"{label} must be a non-empty string")
    return value.strip()


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise TwoLabCoronaPairRescreenError(f"{label} must contain at least {minimum} items")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise TwoLabCoronaPairRescreenError(f"{label} must be an integer >= {minimum}")
    return int(value)


@dataclass(frozen=True)
class TwoLabCoronaPairRescreenSummary:
    """Non-admission accounting for the candidate source pair."""

    candidate_source_count: int
    independent_laboratory_count: int
    candidate_size_count: int
    status: str
    receipt_path: Path


class TwoLabCoronaPairRescreenWorkflow:
    """Freeze a primary-source pair and preserve all unresolved gates."""

    AUDIT_ID = "bioif-r2-two-lab-corona-pair-rescreen-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T129_TWO_LAB_CORONA_PAIR_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/two_lab_corona_pair_rescreen/v1.0.0"
    EXPECTED_SOURCE_IDS = ("PNAS-2008-LUNDQVIST", "PROTEOMICS-2011-ZHANG")
    EXPECTED_LABORATORIES = ("University College Dublin", "Pacific Northwest National Laboratory")
    EXPECTED_SIZES_NM = (50, 100)
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "source_policy",
        "pair_scope",
        "candidates",
    }
    REQUIRED_POLICY_FIELDS = {
        "cc0_cohort_unchanged",
        "require_unit_level_numeric_size_map",
        "require_shared_preprocessing_endpoint",
        "require_reusable_asset_licence",
        "prohibit_article_label_inference",
        "prohibit_model_use_before_t121_amendment",
    }
    REQUIRED_SCOPE_FIELDS = {
        "research_question",
        "primary_search_method",
        "primary_search_date",
        "candidate_selection_rule",
        "not_bulk_downloaded",
    }
    REQUIRED_CANDIDATE_FIELDS = {
        "source_id",
        "publication_title",
        "publication_year",
        "doi",
        "article_locator",
        "laboratory",
        "laboratory_locator",
        "human_matrix",
        "corona_fraction",
        "material_family",
        "numeric_particle_sizes_nm",
        "protein_endpoint",
        "quantification_workflow",
        "supplement_asset_status",
        "licence_status",
        "unit_map_status",
        "shared_endpoint_status",
        "admission",
        "model_use",
        "non_admission_reasons",
    }

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
            raise TwoLabCoronaPairRescreenError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "two-laboratory pair registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise TwoLabCoronaPairRescreenError("two-laboratory pair registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise TwoLabCoronaPairRescreenError("two-laboratory pair registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise TwoLabCoronaPairRescreenError("pair evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise TwoLabCoronaPairRescreenError("pair claim level is unsafe")
        _string(registry.get("evaluated_at"), "pair evaluated_at")
        policy = _mapping(registry.get("source_policy"), "pair source policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS or any(value is not True for value in policy.values()):
            raise TwoLabCoronaPairRescreenError("pair source policy is weakened")
        scope = _mapping(registry.get("pair_scope"), "pair scope")
        if set(scope) != self.REQUIRED_SCOPE_FIELDS:
            raise TwoLabCoronaPairRescreenError("pair scope fields are invalid")
        for field in self.REQUIRED_SCOPE_FIELDS - {"not_bulk_downloaded"}:
            _string(scope.get(field), f"pair scope {field}")
        if scope["not_bulk_downloaded"] is not True:
            raise TwoLabCoronaPairRescreenError("pair screen must not bulk download")

        candidates: list[dict[str, Any]] = []
        source_ids: set[str] = set()
        laboratories: set[str] = set()
        size_sets: set[tuple[int, ...]] = set()
        for value in _list(registry.get("candidates"), "pair candidates", minimum=2):
            candidate = self._candidate(value)
            source_id = candidate["source_id"]
            if source_id in source_ids:
                raise TwoLabCoronaPairRescreenError("pair source is duplicated")
            source_ids.add(source_id)
            laboratories.add(candidate["laboratory"])
            size_sets.add(tuple(candidate["numeric_particle_sizes_nm"]))
            candidates.append(candidate)
        if tuple(sorted(source_ids)) != tuple(sorted(self.EXPECTED_SOURCE_IDS)):
            raise TwoLabCoronaPairRescreenError("pair candidate identities are invalid")
        if tuple(sorted(laboratories)) != tuple(sorted(self.EXPECTED_LABORATORIES)):
            raise TwoLabCoronaPairRescreenError("pair laboratories are invalid")
        if size_sets != {self.EXPECTED_SIZES_NM}:
            raise TwoLabCoronaPairRescreenError("pair numeric size scope is invalid")
        return registry, sorted(candidates, key=lambda row: str(row["source_id"]))

    def _candidate(self, value: Any) -> dict[str, Any]:
        candidate = _mapping(value, "pair candidate")
        if set(candidate) != self.REQUIRED_CANDIDATE_FIELDS:
            raise TwoLabCoronaPairRescreenError("pair candidate fields are invalid")
        for field in self.REQUIRED_CANDIDATE_FIELDS - {
            "publication_year",
            "numeric_particle_sizes_nm",
            "non_admission_reasons",
        }:
            _string(candidate.get(field), f"pair candidate {field}")
        _integer(candidate.get("publication_year"), "pair candidate publication_year", minimum=1900)
        sizes = candidate["numeric_particle_sizes_nm"]
        if sizes != list(self.EXPECTED_SIZES_NM):
            raise TwoLabCoronaPairRescreenError("pair candidate sizes are invalid")
        for field in ("article_locator", "laboratory_locator"):
            if not candidate[field].startswith("https://"):
                raise TwoLabCoronaPairRescreenError(f"pair candidate {field} is invalid")
        if candidate["human_matrix"] not in {"HUMAN_PLASMA", "HUMAN_BLOOD_PLASMA"}:
            raise TwoLabCoronaPairRescreenError("pair candidate matrix is invalid")
        if candidate["material_family"] != "POLYSTYRENE":
            raise TwoLabCoronaPairRescreenError("pair material family is invalid")
        if candidate["admission"] != "NOT_ADMITTED_PAIR_RESCREEN" or candidate["model_use"] != "PROHIBITED":
            raise TwoLabCoronaPairRescreenError("pair candidate was silently promoted")
        reasons = _list(candidate["non_admission_reasons"], "pair non-admission reasons", minimum=3)
        if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            raise TwoLabCoronaPairRescreenError("pair non-admission reason is invalid")
        for field in (
            "supplement_asset_status",
            "licence_status",
            "unit_map_status",
            "shared_endpoint_status",
        ):
            if candidate[field].startswith("VERIFIED_ADMISSIBLE"):
                raise TwoLabCoronaPairRescreenError("pair candidate status silently promotes admission")
        return candidate

    def run(self, *, strict: bool = False) -> TwoLabCoronaPairRescreenSummary:
        if not strict:
            raise TwoLabCoronaPairRescreenError("two-laboratory pair rescreen requires --strict")
        if self.output_root.exists():
            raise TwoLabCoronaPairRescreenError("two-laboratory pair rescreen already executed")
        registry, candidates = self._registry()
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "candidate_source_count": len(candidates),
            "independent_laboratory_count": len({candidate["laboratory"] for candidate in candidates}),
            "candidate_size_count": len(self.EXPECTED_SIZES_NM),
            "status": "BLOCKED_PAIR_ASSET_LICENCE_UNIT_MAP_AND_SHARED_ENDPOINT_AUDIT_REQUIRED",
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "admissible_target_count": 0,
            "candidates": candidates,
            "required_next_evidence": [
                (
                    "Acquire the named first-party supplementary bytes through a normal publisher "
                    "or repository route and record SHA-256, byte count and reuse terms."
                ),
                (
                    "Build an explicit source-file/result-unit to numeric particle-size/material "
                    "map for every unit in both studies; do not use article prose or file order "
                    "as an inferred join."
                ),
                (
                    "Define one shared corona endpoint and preprocessing contract that preserves "
                    "each study's raw scale and supports study-held-out evaluation before any "
                    "T121 amendment."
                ),
                (
                    "Obtain scope-owner approval for a segregated CC-BY/analysis-only route if "
                    "either source is not CC0; do not merge it into the frozen CC0 public cohort."
                ),
            ],
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "report_sha256": hashlib.sha256(_canonical(report)).hexdigest(),
            "candidate_source_count": report["candidate_source_count"],
            "independent_laboratory_count": report["independent_laboratory_count"],
            "candidate_size_count": report["candidate_size_count"],
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        self._write(self.output_root / "pair_rescreen_report.json", report)
        self._write(self.output_root / "pair_rescreen_receipt.json", receipt)
        return TwoLabCoronaPairRescreenSummary(
            candidate_source_count=2,
            independent_laboratory_count=2,
            candidate_size_count=2,
            status=report["status"],
            receipt_path=self.output_root / "pair_rescreen_receipt.json",
        )

    def verify(self) -> TwoLabCoronaPairRescreenSummary:
        report_path = self.output_root / "pair_rescreen_report.json"
        receipt_path = self.output_root / "pair_rescreen_receipt.json"
        report = self._json(report_path, "pair rescreen report")
        receipt = self._json(receipt_path, "pair rescreen receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != receipt.get("status")
            or receipt.get("report_sha256") != hashlib.sha256(report_path.read_bytes()).hexdigest()
            or report.get("candidate_source_count") != 2
            or report.get("independent_laboratory_count") != 2
            or report.get("candidate_size_count") != 2
            or report.get("admissible_target_count") != 0
            or report.get("target_status") != "NOT_FROZEN"
            or report.get("model_use") != "PROHIBITED"
            or report.get("scientific_submission_ready") is not False
        ):
            raise TwoLabCoronaPairRescreenError("pair rescreen receipt is invalid")
        return TwoLabCoronaPairRescreenSummary(
            candidate_source_count=2,
            independent_laboratory_count=2,
            candidate_size_count=2,
            status=_string(report["status"], "pair rescreen status"),
            receipt_path=receipt_path,
        )
