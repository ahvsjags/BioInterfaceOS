"""Fail-closed T129 rescreening of newly identified CC0 PRIDE leads.

The workflow freezes only the limited metadata and small-result-asset evidence
that was actually inspected.  It never converts source labels such as GO, FLG,
or GNP into a material feature, and it cannot admit a predictive target.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CC0TargetRescreenError(RuntimeError):
    """Raised when the bounded T129 rescreen would weaken a target gate."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CC0TargetRescreenError(f"{label} must be an object")
    return dict(value)


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise CC0TargetRescreenError(f"{label} must contain at least {minimum} items")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CC0TargetRescreenError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CC0TargetRescreenError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class CC0TargetRescreenSummary:
    """Accounting for the non-admitted, bounded rescreen tranche."""

    candidate_source_count: int
    disclosed_laboratory_count: int
    screened_asset_count: int
    receipt_path: Path


class CC0TargetRescreenWorkflow:
    """Audit new CC0 leads without changing the prior immutable tranches."""

    AUDIT_ID = "bioif-r2-cc0-target-rescreen-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T129_CC0_RESCREEN_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/cc0_target_rescreen/v1.0.0"
    ALLOWED_LICENSES = frozenset({"CC0-1.0"})
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "development_cutoff",
        "evidence_class",
        "allowed_claim_level",
        "source_policy",
        "search_scope",
        "candidates",
    }
    REQUIRED_POLICY_FIELDS = {
        "allowed_licenses",
        "require_human_biofluid_corona_context",
        "require_numeric_source_matched_covariates",
        "require_common_preprocessing_endpoint",
        "require_two_independent_laboratories",
        "prohibit_author_quantification_concatenation",
        "prohibit_predictive_identity_features",
        "prohibit_model_use_before_t121_amendment",
    }
    REQUIRED_SCOPE_FIELDS = {
        "official_search_endpoint",
        "query_terms",
        "unique_project_count",
        "cc0_human_pre_cutoff_accessions",
        "directory_screened_accessions",
        "small_asset_inspected_accessions",
    }
    REQUIRED_CANDIDATE_FIELDS = {
        "source_id",
        "accession",
        "project_api_url",
        "landing_url",
        "publication_date",
        "license_id",
        "access",
        "biological_context",
        "laboratory_disclosure_status",
        "screened_assets",
        "source_label_status",
        "numeric_covariate_map_status",
        "common_endpoint_status",
        "analysis_unit_status",
        "admission",
        "model_use",
        "non_admission_reasons",
    }
    REQUIRED_ASSET_FIELDS = {
        "file_name",
        "download_url",
        "observed_local_bytes",
        "local_sha256",
        "publisher_sha1",
        "content_type",
        "screened_evidence",
    }
    EXPECTED_CANDIDATES = {
        "PXD019524": {
            "asset_count": 6,
            "source_label_status": "CATEGORICAL_GO_FLG_SOURCE_LABELS",
            "numeric_covariate_map_status": (
                "NO_NUMERIC_MATERIAL_OR_SIZE_COVARIATE_IN_SCREENED_CSVS"
            ),
            "common_endpoint_status": "AUTHOR_SPECIFIC_TMT_OUTPUT_NOT_SHARED_CROSS_STUDY_ENDPOINT",
        },
        "PXD046988": {
            "asset_count": 1,
            "source_label_status": "CATEGORICAL_GO_GNP_AND_MEDIA_SOURCE_LABELS",
            "numeric_covariate_map_status": (
                "NO_NUMERIC_MATERIAL_OR_SIZE_COVARIATE_IN_SCREENED_QUANT_TABLE"
            ),
            "common_endpoint_status": "AUTHOR_SPECIFIC_DIA_OUTPUT_NOT_SHARED_CROSS_STUDY_ENDPOINT",
        },
    }
    REQUIRED_FALSE = (
        "model_fitted",
        "paired_ablations_run",
        "external_ood_evaluated",
        "negative_controls_run",
        "independent_validation",
        "scientific_submission_ready",
    )

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
            raise CC0TargetRescreenError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T129 CC0 rescreen registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise CC0TargetRescreenError("CC0 rescreen registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise CC0TargetRescreenError("CC0 rescreen registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise CC0TargetRescreenError("CC0 rescreen evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise CC0TargetRescreenError("CC0 rescreen claim level is unsafe")
        _string(registry.get("evaluated_at"), "CC0 rescreen evaluated_at")
        if _string(registry.get("development_cutoff"), "CC0 rescreen cutoff") != (
            "2024-12-31T23:59:59+00:00"
        ):
            raise CC0TargetRescreenError("CC0 rescreen cutoff changed")

        policy = _mapping(registry.get("source_policy"), "CC0 rescreen policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS:
            raise CC0TargetRescreenError("CC0 rescreen policy fields are invalid")
        if set(_list(policy.get("allowed_licenses"), "CC0 rescreen licences")) != (
            self.ALLOWED_LICENSES
        ):
            raise CC0TargetRescreenError("CC0 rescreen licences are invalid")
        if any(
            policy.get(field) is not True
            for field in self.REQUIRED_POLICY_FIELDS - {"allowed_licenses"}
        ):
            raise CC0TargetRescreenError("CC0 rescreen policy is weakened")

        scope = _mapping(registry.get("search_scope"), "CC0 rescreen search scope")
        if set(scope) != self.REQUIRED_SCOPE_FIELDS:
            raise CC0TargetRescreenError("CC0 rescreen search scope is invalid")
        if not _string(scope.get("official_search_endpoint"), "CC0 rescreen endpoint").startswith(
            "https://www.ebi.ac.uk/pride/ws/archive/v3/search/projects"
        ):
            raise CC0TargetRescreenError("CC0 rescreen search endpoint is invalid")
        terms = _list(scope.get("query_terms"), "CC0 rescreen query terms", minimum=8)
        if len(terms) != len(set(terms)) or any(
            not isinstance(term, str) or not term for term in terms
        ):
            raise CC0TargetRescreenError("CC0 rescreen query terms are invalid")
        if _integer(scope.get("unique_project_count"), "CC0 rescreen unique projects") != 83:
            raise CC0TargetRescreenError("CC0 rescreen project accounting is invalid")
        eligible = _list(
            scope.get("cc0_human_pre_cutoff_accessions"),
            "CC0 rescreen eligible projects",
            minimum=25,
        )
        if len(eligible) != 25 or len(eligible) != len(set(eligible)):
            raise CC0TargetRescreenError("CC0 rescreen eligible-project accounting is invalid")
        if set(
            _list(scope.get("directory_screened_accessions"), "CC0 directory screens", minimum=7)
        ) != {
            "PXD010910",
            "PXD019524",
            "PXD023001",
            "PXD026615",
            "PXD028310",
            "PXD046988",
            "PXD052226",
        }:
            raise CC0TargetRescreenError("CC0 rescreen directory scope is invalid")
        if set(
            _list(
                scope.get("small_asset_inspected_accessions"), "CC0 small-asset screens", minimum=2
            )
        ) != set(self.EXPECTED_CANDIDATES):
            raise CC0TargetRescreenError("CC0 rescreen small-asset scope is invalid")

        candidates: list[dict[str, Any]] = []
        source_ids: set[str] = set()
        asset_count = 0
        for value in _list(registry.get("candidates"), "CC0 rescreen candidates", minimum=2):
            candidate = _mapping(value, "CC0 rescreen candidate")
            if set(candidate) != self.REQUIRED_CANDIDATE_FIELDS:
                raise CC0TargetRescreenError("CC0 rescreen candidate fields are invalid")
            for field in self.REQUIRED_CANDIDATE_FIELDS - {
                "screened_assets",
                "non_admission_reasons",
            }:
                _string(candidate.get(field), f"CC0 rescreen candidate {field}")
            accession = candidate["accession"]
            expected = self.EXPECTED_CANDIDATES.get(accession)
            if expected is None or candidate["source_id"] != f"PRIDE-{accession}":
                raise CC0TargetRescreenError("CC0 rescreen candidate identity is invalid")
            if candidate["source_id"] in source_ids:
                raise CC0TargetRescreenError("CC0 rescreen candidate is duplicated")
            source_ids.add(candidate["source_id"])
            if not candidate["project_api_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise CC0TargetRescreenError("CC0 rescreen project locator is invalid")
            if not candidate["landing_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise CC0TargetRescreenError("CC0 rescreen landing locator is invalid")
            if candidate["publication_date"] > "2024-12-31":
                raise CC0TargetRescreenError("CC0 rescreen candidate is post-freeze")
            if (
                candidate["license_id"] not in self.ALLOWED_LICENSES
                or candidate["access"] != "ANONYMOUS_PUBLIC"
            ):
                raise CC0TargetRescreenError("CC0 rescreen candidate access is unsafe")
            if "human" not in candidate["biological_context"].lower():
                raise CC0TargetRescreenError("CC0 rescreen candidate lacks human context")
            if (
                candidate["laboratory_disclosure_status"]
                != "NOT_DISCLOSED_IN_OFFICIAL_PROJECT_RECORD"
            ):
                raise CC0TargetRescreenError("CC0 rescreen laboratory status is invalid")
            for field in (
                "source_label_status",
                "numeric_covariate_map_status",
                "common_endpoint_status",
            ):
                if candidate[field] != expected[field]:
                    raise CC0TargetRescreenError("CC0 rescreen silently promotes a target")
            if candidate["analysis_unit_status"] != "BIOLOGICAL_UNIT_NOT_FROZEN":
                raise CC0TargetRescreenError("CC0 rescreen analysis-unit status is invalid")
            if candidate["admission"] != "NOT_ADMITTED" or candidate["model_use"] != "PROHIBITED":
                raise CC0TargetRescreenError("CC0 rescreen silently promotes a target")
            assets = _list(candidate.get("screened_assets"), "CC0 rescreen assets", minimum=1)
            if len(assets) != expected["asset_count"]:
                raise CC0TargetRescreenError("CC0 rescreen asset accounting is invalid")
            names: set[str] = set()
            for asset_value in assets:
                asset = _mapping(asset_value, "CC0 rescreen asset")
                if set(asset) != self.REQUIRED_ASSET_FIELDS:
                    raise CC0TargetRescreenError("CC0 rescreen asset fields are invalid")
                for field in self.REQUIRED_ASSET_FIELDS - {"observed_local_bytes"}:
                    _string(asset.get(field), f"CC0 rescreen asset {field}")
                if asset["file_name"] in names:
                    raise CC0TargetRescreenError("CC0 rescreen asset is duplicated")
                names.add(asset["file_name"])
                _integer(asset.get("observed_local_bytes"), "CC0 rescreen asset bytes", minimum=1)
                for digest_field, length in (("local_sha256", 64), ("publisher_sha1", 40)):
                    digest = asset[digest_field].lower()
                    if len(digest) != length or any(
                        char not in "0123456789abcdef" for char in digest
                    ):
                        raise CC0TargetRescreenError("CC0 rescreen asset checksum is invalid")
                if not asset["download_url"].startswith("https://ftp.pride.ebi.ac.uk/"):
                    raise CC0TargetRescreenError("CC0 rescreen asset locator is invalid")
            reasons = _list(
                candidate.get("non_admission_reasons"), "CC0 rescreen reasons", minimum=2
            )
            if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
                raise CC0TargetRescreenError("CC0 rescreen reason is invalid")
            asset_count += len(assets)
            candidates.append(candidate)
        if len(source_ids) != 2 or asset_count != 7:
            raise CC0TargetRescreenError("CC0 rescreen candidate cohort is invalid")
        return registry, sorted(candidates, key=lambda row: str(row["source_id"]))

    def run(self, *, strict: bool = False) -> CC0TargetRescreenSummary:
        """Write a one-shot no-target decision from the bounded rescreen evidence."""
        if not strict:
            raise CC0TargetRescreenError("CC0 target rescreen requires --strict")
        if self.output_root.exists():
            raise CC0TargetRescreenError("CC0 target rescreen already executed")
        registry, candidates = self._registry()
        asset_count = sum(len(candidate["screened_assets"]) for candidate in candidates)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "candidate_source_count": len(candidates),
            "disclosed_laboratory_count": 0,
            "screened_asset_count": asset_count,
            "candidates": candidates,
            "status": "BLOCKED_CC0_RESCREEN_NO_NEW_ADMISSIBLE_TARGET",
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "admissible_target_count": 0,
            "blocked_reasons": [
                "PXD019524 records GO/FLG source labels and author-specific TMT output, not a "
                "source-matched numeric material or size covariate or explicit human-biofluid "
                "unit map.",
                "PXD046988 records GO/GNP, medium/plasma, time and replicate source labels in "
                "one DIA table, not numeric material or size covariates for admitted biological "
                "units.",
                "Neither project record discloses an independently verifiable laboratory unit, and "
                "neither output defines a common endpoint across two laboratories.",
            ],
            "next_required_evidence": [
                "At least two independent sources must explicitly map every biological unit to "
                "numeric material or size covariates and one shared preprocessing endpoint.",
                "Freeze T121 Amendment v1.0.1 before any T123 model workflow once those source "
                "assets and laboratory provenance are available.",
            ],
            **{field: False for field in self.REQUIRED_FALSE},
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "target_rescreen_report.json"
        receipt_path = self.output_root / "target_rescreen_receipt.json"
        self._write(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "target_rescreen_report_sha256": _sha256(report_path),
            "candidate_source_count": report["candidate_source_count"],
            "disclosed_laboratory_count": 0,
            "screened_asset_count": report["screened_asset_count"],
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            **{field: False for field in self.REQUIRED_FALSE},
        }
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return CC0TargetRescreenSummary(2, 0, asset_count, receipt_path)

    def verify(self) -> CC0TargetRescreenSummary:
        """Verify the immutable receipt without reconstructing any source semantics."""
        report_path = self.output_root / "target_rescreen_report.json"
        receipt_path = self.output_root / "target_rescreen_receipt.json"
        report = self._json(report_path, "CC0 rescreen report")
        receipt = self._json(receipt_path, "CC0 rescreen receipt")
        expected = {
            "candidate_source_count": 2,
            "disclosed_laboratory_count": 0,
            "screened_asset_count": 7,
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
        }
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != "BLOCKED_CC0_RESCREEN_NO_NEW_ADMISSIBLE_TARGET"
            or receipt.get("status") != report.get("status")
            or receipt.get("target_rescreen_report_sha256") != _sha256(report_path)
            or any(
                report.get(key) != value or receipt.get(key) != value
                for key, value in expected.items()
            )
            or any(
                report.get(field) is not False or receipt.get(field) is not False
                for field in self.REQUIRED_FALSE
            )
        ):
            raise CC0TargetRescreenError("CC0 rescreen receipt is invalid")
        self._registry()
        return CC0TargetRescreenSummary(2, 0, 7, receipt_path)
