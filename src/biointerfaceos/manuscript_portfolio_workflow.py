"""Audit the R2 manuscript portfolio without turning protocols into results."""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    metadata_for,
    require_metadata,
)


class ManuscriptPortfolioError(RuntimeError):
    """Raised when an R2 manuscript route loses an evidence boundary."""


@dataclass(frozen=True)
class ManuscriptPortfolioSummary:
    """Non-result accounting for the two R2 manuscript routes."""

    manuscript_count: int
    protocol_figure_count: int
    legacy_withdrawal_count: int
    status: str
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ManuscriptPortfolioError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManuscriptPortfolioError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        raise ManuscriptPortfolioError(f"{label} has too few entries")
    values = [_string(item, label) for item in value]
    if len(values) != len(set(values)):
        raise ManuscriptPortfolioError(f"{label} contains duplicates")
    return values


class ManuscriptPortfolioWorkflow:
    """Create a fail-closed receipt for R2's protocol-only portfolio state."""

    AUDIT_ID = "bioif-r2-manuscript-portfolio-audit-v1.4.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    PORTFOLIO_RELATIVE = "docs/manuscripts/R2_MANUSCRIPT_PORTFOLIO.json"
    COMPARATOR_MAP_RELATIVE = "docs/literature/R2_MANUSCRIPT_COMPARATOR_MAP.json"
    FIGURE_MANIFEST_RELATIVE = (
        "reports/review_round_2/submission_figures/v1.1.0/figure_manifest.json"
    )
    WITHDRAWAL_RELATIVE = "reports/review_round_2/submission_figures/v1.1.0/withdrawal_ledger.json"
    RELATED_WORK_RELATIVE = "reports/review_round_2/related_work/v1.1.0/related_work_receipt.json"
    T123_COMPATIBILITY_RELATIVE = (
        "reports/review_round_2/real_model_compatibility/v1.1.0/compatibility_receipt.json"
    )
    T123_RESULT_PROFILE_RELATIVE = (
        "reports/review_round_2/real_proteomics_result_profile/v1.0.0/result_profile_receipt.json"
    )
    T129_ADMISSION_RELATIVE = (
        "reports/review_round_2/cc0_target_admission/v1.0.0/target_admission_receipt.json"
    )
    T129_DISCOVERY_RELATIVE = (
        "reports/review_round_2/cc0_target_discovery/v1.0.0/target_discovery_receipt.json"
    )
    T129_CURRENT_TARGET_EVIDENCE_RELATIVE = (
        "reports/review_round_2/t129_current_target_evidence/v1.2.0/"
        "current_target_evidence_receipt.json"
    )
    T124_RELATIVE = "reports/review_round_2/independent_evaluation/v1.0.0/readiness_receipt.json"
    OUTPUT_RELATIVE = "reports/review_round_2/manuscript_portfolio/v1.4.0"
    REQUIRED_PORTFOLIO_FIELDS = {
        "schema_version",
        "portfolio_id",
        "declared_at",
        "status",
        "required_legacy_withdrawal_count",
        "historical_artifacts",
        "manuscripts",
    }
    REQUIRED_MANUSCRIPT_FIELDS = {
        "manuscript_id",
        "title",
        "route",
        "current_status",
        "document_path",
        "comparator_scope_id",
        "prerequisite_tasks",
        "required_evidence_paths",
        "forbidden_claims",
        "required_sections",
        "figure_usage",
    }
    REQUIRED_MANUSCRIPT_IDS = frozenset({"R2_PAPER_AB_PROTOCOL", "R2_PAPER_C_PROTOCOL"})
    REQUIRED_ROUTES = {
        "R2_PAPER_AB_PROTOCOL": "MERGED_PROTOCOL_ONLY_PENDING_T123",
        "R2_PAPER_C_PROTOCOL": "REGISTERED_PROTOCOL_ONLY_PENDING_T124",
    }
    REQUIRED_STATUSES = {
        "R2_PAPER_AB_PROTOCOL": "BLOCKED_PENDING_COMPATIBLE_REAL_MODEL_TARGET",
        "R2_PAPER_C_PROTOCOL": "BLOCKED_PENDING_EXTERNAL_EVALUATOR_RECEIPT",
    }
    REQUIRED_SCOPE_IDS = {
        "R2_PAPER_AB_PROTOCOL": "R2_PAPER_AB_REAL_BENCHMARK_METHOD",
        "R2_PAPER_C_PROTOCOL": "R2_PAPER_C_PREREGISTERED_PROTOCOL",
    }
    DOCUMENT_BOUNDARIES = {
        "R2_PAPER_AB_PROTOCOL": {
            "This is the merged R2 A+B protocol outline.",
            "It is **not submission-ready**.",
            "The historical fixture manuscripts are withdrawn from R2 submission scope.",
            "T123 found zero compatible cross-study targets.",
            "No model effect, paired ablation,",
            "generalisation or external OOD result belongs in this version.",
            "The completed three-source author-result profile contains 23 profiles but zero",
            "neither screen admits a target.",
            "The current consolidated T129 receipt binds six candidate sources",
        },
        "R2_PAPER_C_PROTOCOL": {
            "This is a results-blind R2 Paper C protocol outline.",
            "It is **not\nsubmission-ready**",
            "Historical fixture pre-lock outputs are not evidence for this protocol.",
            "The current receipt has zero compatible targets",
            "The author team cannot access values",
            "the protocol; they do not supply a result.",
            "all six candidates remain non-admitted.",
            "model use remains",
            "`PROHIBITED`",
        },
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: Any, label: str) -> Path:
        path = (self.root / _string(relative, label)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ManuscriptPortfolioError(f"{label} is missing or outside the repository")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ManuscriptPortfolioError(f"cannot parse {label}") from exc

    def _portfolio(self) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
        path = self._path(self.PORTFOLIO_RELATIVE, "R2 manuscript portfolio")
        portfolio = self._json(path, "R2 manuscript portfolio")
        if set(portfolio) != self.REQUIRED_PORTFOLIO_FIELDS or portfolio.get("schema_version") != 1:
            raise ManuscriptPortfolioError("R2 manuscript portfolio schema is invalid")
        if (
            portfolio.get("portfolio_id") != "bioif-r2-manuscript-portfolio-v1.4.0"
            or portfolio.get("declared_at") != self.AUDITED_AT
            or portfolio.get("status") != "PROTOCOL_PORTFOLIO_PENDING_REAL_EVIDENCE"
            or portfolio.get("required_legacy_withdrawal_count") != 15
        ):
            raise ManuscriptPortfolioError("R2 manuscript portfolio identity or status is invalid")
        historical = _string_list(
            portfolio.get("historical_artifacts"), "historical artifacts", minimum=3
        )
        if len(historical) != 3 or any(
            not item.startswith("release/manuscripts/") for item in historical
        ):
            raise ManuscriptPortfolioError("historical manuscript exclusion set is invalid")
        for relative in historical:
            self._path(relative, "historical manuscript")
        raw_manuscripts = portfolio.get("manuscripts")
        if not isinstance(raw_manuscripts, list) or len(raw_manuscripts) != 2:
            raise ManuscriptPortfolioError(
                "R2 portfolio must contain exactly two manuscript routes"
            )
        manuscripts: list[dict[str, Any]] = []
        identifiers: set[str] = set()
        for value in raw_manuscripts:
            manuscript = _mapping(value, "R2 manuscript route")
            if set(manuscript) != self.REQUIRED_MANUSCRIPT_FIELDS:
                raise ManuscriptPortfolioError("R2 manuscript route schema is invalid")
            identifier = _string(manuscript.get("manuscript_id"), "R2 manuscript ID")
            if identifier in identifiers:
                raise ManuscriptPortfolioError("R2 manuscript ID is duplicated")
            identifiers.add(identifier)
            for field in (
                "title",
                "route",
                "current_status",
                "document_path",
                "comparator_scope_id",
            ):
                _string(manuscript.get(field), f"R2 manuscript {field}")
            for field in (
                "prerequisite_tasks",
                "required_evidence_paths",
                "forbidden_claims",
                "required_sections",
                "figure_usage",
            ):
                _string_list(manuscript.get(field), f"R2 manuscript {field}")
            manuscripts.append(manuscript)
        if identifiers != self.REQUIRED_MANUSCRIPT_IDS:
            raise ManuscriptPortfolioError("R2 manuscript IDs do not match the required portfolio")
        return portfolio, path, manuscripts

    def _documents(self, manuscripts: list[dict[str, Any]]) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        for manuscript in manuscripts:
            identifier = str(manuscript["manuscript_id"])
            if (
                manuscript["route"] != self.REQUIRED_ROUTES[identifier]
                or manuscript["current_status"] != self.REQUIRED_STATUSES[identifier]
                or manuscript["comparator_scope_id"] != self.REQUIRED_SCOPE_IDS[identifier]
            ):
                raise ManuscriptPortfolioError("R2 manuscript route or status is unsafe")
            document_path = self._path(manuscript["document_path"], "R2 manuscript outline")
            if document_path.as_posix().find("release/manuscripts") >= 0:
                raise ManuscriptPortfolioError("historical manuscript entered the R2 portfolio")
            try:
                content = document_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise ManuscriptPortfolioError("cannot read R2 manuscript outline") from exc
            required_sections = _string_list(
                manuscript["required_sections"], "R2 manuscript sections", minimum=9
            )
            missing_sections = [
                section for section in required_sections if f"## {section}" not in content
            ]
            if missing_sections:
                raise ManuscriptPortfolioError("R2 manuscript outline is missing required sections")
            normalized_content = " ".join(content.split())
            if any(
                " ".join(boundary.split()) not in normalized_content
                for boundary in self.DOCUMENT_BOUNDARIES[identifier]
            ):
                raise ManuscriptPortfolioError("R2 manuscript outline weakens a protocol boundary")
            records.append(
                {
                    "manuscript_id": identifier,
                    "document_path": str(document_path.relative_to(self.root)),
                    "document_sha256": _sha256(document_path),
                }
            )
        return sorted(records, key=lambda row: row["manuscript_id"])

    def _evidence_state(self, manuscripts: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
        comparator_map = self._json(
            self._path(self.COMPARATOR_MAP_RELATIVE, "R2 manuscript comparator map"),
            "R2 manuscript comparator map",
        )
        scopes = comparator_map.get("manuscript_scopes")
        if not isinstance(scopes, list):
            raise ManuscriptPortfolioError("R2 manuscript comparator scopes are invalid")
        scope_ids = {item.get("scope_id") for item in scopes if isinstance(item, dict)}
        if not {item["comparator_scope_id"] for item in manuscripts}.issubset(scope_ids):
            raise ManuscriptPortfolioError("R2 manuscript route lacks a verified comparator scope")
        for manuscript in manuscripts:
            for relative in _string_list(
                manuscript["required_evidence_paths"], "R2 manuscript evidence paths"
            ):
                self._path(relative, "R2 manuscript evidence")

        related = self._json(
            self._path(self.RELATED_WORK_RELATIVE, "R2 related-work receipt"),
            "R2 related-work receipt",
        )
        if (
            related.get("status") != "PASS_RELATED_WORK_EVIDENCE_PACKET"
            or related.get("citation_count") != 12
            or related.get("comparator_count") != 8
            or related.get("historical_fixture_manuscripts_retroactively_cleared") is not False
        ):
            raise ManuscriptPortfolioError("R2 related-work evidence is insufficient")
        figures = self._json(
            self._path(self.FIGURE_MANIFEST_RELATIVE, "R2 figure manifest"), "R2 figure manifest"
        )
        figure_rows = figures.get("figures")
        if (
            figures.get("publication_status") != "PROTOCOL_ONLY"
            or figures.get("scientific_submission_ready") is not False
            or figures.get("withdrawn_historical_figure_count") != 15
            or not isinstance(figure_rows, list)
            or len(figure_rows) != 3
        ):
            raise ManuscriptPortfolioError("R2 figure suite is not protocol-only")
        figure_ids = {item.get("figure_id") for item in figure_rows if isinstance(item, dict)}
        for manuscript in manuscripts:
            if not set(_string_list(manuscript["figure_usage"], "R2 manuscript figures")).issubset(
                figure_ids
            ):
                raise ManuscriptPortfolioError("R2 manuscript names an unavailable protocol figure")
        withdrawal = self._json(
            self._path(self.WITHDRAWAL_RELATIVE, "R2 withdrawal ledger"), "R2 withdrawal ledger"
        )
        withdrawals = withdrawal.get("withdrawals")
        if (
            not isinstance(withdrawals, list)
            or len(withdrawals) != 15
            or any(
                item.get("status") != "WITHDRAWN_FROM_R2_SUBMISSION_SCOPE"
                for item in withdrawals
                if isinstance(item, dict)
            )
        ):
            raise ManuscriptPortfolioError("R2 historical-figure withdrawal is incomplete")
        compatibility = self._json(
            self._path(self.T123_COMPATIBILITY_RELATIVE, "T123 compatibility receipt"),
            "T123 compatibility receipt",
        )
        result_profile = self._json(
            self._path(self.T123_RESULT_PROFILE_RELATIVE, "T123 result-profile receipt"),
            "T123 result-profile receipt",
        )
        t129_admission = self._json(
            self._path(self.T129_ADMISSION_RELATIVE, "T129 admission receipt"),
            "T129 admission receipt",
        )
        t129_discovery = self._json(
            self._path(self.T129_DISCOVERY_RELATIVE, "T129 discovery receipt"),
            "T129 discovery receipt",
        )
        t129_current_target_evidence = self._json(
            self._path(
                self.T129_CURRENT_TARGET_EVIDENCE_RELATIVE,
                "T129 current target-evidence receipt",
            ),
            "T129 current target-evidence receipt",
        )
        t124 = self._json(
            self._path(self.T124_RELATIVE, "T124 readiness receipt"),
            "T124 readiness receipt",
        )
        if (
            compatibility.get("status") != "BLOCKED_NO_COMPATIBLE_CROSS_STUDY_TARGET"
            or compatibility.get("compatible_target_count") != 0
            or compatibility.get("model_fitted") is not False
            or result_profile.get("status") != "REAL_RESULT_PROFILE_COMPLETE_NOT_A_MODEL_TARGET"
            or result_profile.get("compatible_cross_study_target_count") != 0
            or result_profile.get("target_status") != "NOT_FROZEN"
            or result_profile.get("model_use") != "PROHIBITED"
            or result_profile.get("model_fitted") is not False
            or t129_admission.get("status") != "BLOCKED_NO_CC0_COMMON_TARGET"
            or t129_admission.get("admissible_target_count") != 0
            or t129_admission.get("target_status") != "NOT_FROZEN"
            or t129_admission.get("model_use") != "PROHIBITED"
            or t129_admission.get("model_fitted") is not False
            or t129_discovery.get("status")
            != "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES"
            or t129_discovery.get("admissible_target_count") != 0
            or t129_discovery.get("target_status") != "NOT_FROZEN"
            or t129_discovery.get("model_use") != "PROHIBITED"
            or t129_discovery.get("model_fitted") is not False
            or t129_current_target_evidence.get("status")
            != "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET"
            or t129_current_target_evidence.get("candidate_source_count") != 6
            or t129_current_target_evidence.get("candidate_laboratory_count") != 5
            or t129_current_target_evidence.get("verified_source_asset_count") != 24
            or t129_current_target_evidence.get("admissible_target_count") != 0
            or t129_current_target_evidence.get("target_status") != "NOT_FROZEN"
            or t129_current_target_evidence.get("model_use") != "PROHIBITED"
            or t129_current_target_evidence.get("model_fitted") is not False
            or t124.get("status") != "BLOCKED_T123_COMPATIBLE_TARGET_REQUIRED"
            or t124.get("external_evaluator_receipt_verified") is not False
        ):
            raise ManuscriptPortfolioError(
                "T123/T124/T129 evidence state is not represented honestly"
            )
        return (
            {
                "related_work_receipt_sha256": _sha256(
                    self._path(self.RELATED_WORK_RELATIVE, "R2 related-work receipt")
                ),
                "figure_manifest_sha256": _sha256(
                    self._path(self.FIGURE_MANIFEST_RELATIVE, "R2 figure manifest")
                ),
                "withdrawal_ledger_sha256": _sha256(
                    self._path(self.WITHDRAWAL_RELATIVE, "R2 withdrawal ledger")
                ),
                "t123_compatibility_receipt_sha256": _sha256(
                    self._path(self.T123_COMPATIBILITY_RELATIVE, "T123 compatibility receipt")
                ),
                "t123_result_profile_receipt_sha256": _sha256(
                    self._path(self.T123_RESULT_PROFILE_RELATIVE, "T123 result-profile receipt")
                ),
                "t129_admission_receipt_sha256": _sha256(
                    self._path(self.T129_ADMISSION_RELATIVE, "T129 admission receipt")
                ),
                "t129_discovery_receipt_sha256": _sha256(
                    self._path(self.T129_DISCOVERY_RELATIVE, "T129 discovery receipt")
                ),
                "t129_current_target_evidence_receipt_sha256": _sha256(
                    self._path(
                        self.T129_CURRENT_TARGET_EVIDENCE_RELATIVE,
                        "T129 current target-evidence receipt",
                    )
                ),
                "t124_readiness_receipt_sha256": _sha256(
                    self._path(self.T124_RELATIVE, "T124 readiness receipt")
                ),
                "t123_compatible_target_count": 0,
                "t123_profile_compatible_cross_study_target_count": 0,
                "t129_admission_admissible_target_count": 0,
                "t129_discovery_admissible_target_count": 0,
                "t129_current_target_evidence_candidate_source_count": 6,
                "t129_current_target_evidence_candidate_laboratory_count": 5,
                "t129_current_target_evidence_verified_source_asset_count": 24,
                "t124_external_evaluator_receipt_verified": False,
            },
            len(figure_rows),
        )

    def run(self, *, strict: bool = False) -> ManuscriptPortfolioSummary:
        """Write one immutable blocked-state R2 portfolio receipt."""
        if not strict:
            raise ManuscriptPortfolioError("R2 manuscript portfolio audit requires --strict")
        if self.output_root.exists():
            raise ManuscriptPortfolioError("R2 manuscript portfolio audit already executed")
        portfolio, portfolio_path, manuscripts = self._portfolio()
        documents = self._documents(manuscripts)
        evidence, figure_count = self._evidence_state(manuscripts)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "portfolio_id": portfolio["portfolio_id"],
            "portfolio_sha256": _sha256(portfolio_path),
            "status": "BLOCKED_R2_MANUSCRIPTS_PENDING_T123_T124",
            **metadata_for(EvidenceClass.DEVELOPMENT_OBSERVATION),
            "manuscripts": documents,
            "protocol_figure_count": figure_count,
            "legacy_withdrawal_count": portfolio["required_legacy_withdrawal_count"],
            "evidence": evidence,
            "historical_fixture_manuscripts_reused": False,
            "model_fitted": False,
            "independent_evaluator_receipt_verified": False,
            "scientific_submission_ready": False,
            "next_required_evidence": (
                "T123 compatible target and frozen real-model outputs, followed by a T124 "
                "external evaluator receipt from protected real observations."
            ),
        }
        report_path = self.output_root / "portfolio_decision.json"
        receipt_path = self.output_root / "portfolio_receipt.json"
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "portfolio_decision_sha256": _sha256(report_path),
            "manuscript_count": len(documents),
            "protocol_figure_count": figure_count,
            "legacy_withdrawal_count": portfolio["required_legacy_withdrawal_count"],
            "t123_compatible_target_count": 0,
            "t123_profile_compatible_cross_study_target_count": 0,
            "t129_admission_admissible_target_count": 0,
            "t129_discovery_admissible_target_count": 0,
            "t129_current_target_evidence_candidate_source_count": 6,
            "t129_current_target_evidence_candidate_laboratory_count": 5,
            "t129_current_target_evidence_verified_source_asset_count": 24,
            "t124_external_evaluator_receipt_verified": False,
            "historical_fixture_manuscripts_reused": False,
            "model_fitted": False,
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return ManuscriptPortfolioSummary(
            manuscript_count=len(documents),
            protocol_figure_count=figure_count,
            legacy_withdrawal_count=portfolio["required_legacy_withdrawal_count"],
            status=report["status"],
            receipt_path=receipt_path,
        )

    def verify(self) -> ManuscriptPortfolioSummary:
        """Verify the portfolio receipt without rebuilding its reports."""
        decision_path = self.output_root / "portfolio_decision.json"
        receipt_path = self.output_root / "portfolio_receipt.json"
        decision = self._json(decision_path, "R2 manuscript portfolio decision")
        receipt = self._json(receipt_path, "R2 manuscript portfolio receipt")
        try:
            evidence_class, claim_level = require_metadata(decision, "R2 manuscript portfolio")
        except EvidenceSemanticsError as exc:
            raise ManuscriptPortfolioError(str(exc)) from exc
        if (
            decision.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or decision.get("status") != "BLOCKED_R2_MANUSCRIPTS_PENDING_T123_T124"
            or receipt.get("status") != decision.get("status")
            or receipt.get("portfolio_decision_sha256") != _sha256(decision_path)
            or evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise ManuscriptPortfolioError("R2 manuscript portfolio receipt is invalid")
        expected = {
            "manuscript_count": 2,
            "protocol_figure_count": 3,
            "legacy_withdrawal_count": 15,
            "t123_compatible_target_count": 0,
            "t123_profile_compatible_cross_study_target_count": 0,
            "t129_admission_admissible_target_count": 0,
            "t129_discovery_admissible_target_count": 0,
            "t129_current_target_evidence_candidate_source_count": 6,
            "t129_current_target_evidence_candidate_laboratory_count": 5,
            "t129_current_target_evidence_verified_source_asset_count": 24,
        }
        if any(receipt.get(key) != value for key, value in expected.items()) or any(
            receipt.get(field) is not False
            for field in (
                "t124_external_evaluator_receipt_verified",
                "historical_fixture_manuscripts_reused",
                "model_fitted",
                "scientific_submission_ready",
            )
        ):
            raise ManuscriptPortfolioError("R2 manuscript portfolio accounting is invalid")
        return ManuscriptPortfolioSummary(
            manuscript_count=2,
            protocol_figure_count=3,
            legacy_withdrawal_count=15,
            status="BLOCKED_R2_MANUSCRIPTS_PENDING_T123_T124",
            receipt_path=receipt_path,
        )
