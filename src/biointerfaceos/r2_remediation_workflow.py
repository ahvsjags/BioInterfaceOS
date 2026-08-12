"""Audit the current evidence disposition for every R2 editorial finding.

This is deliberately a status ledger, not a scientific acceptance workflow.
It makes the difference between a verified process correction and an empirical
claim explicit while the real-data and independent-validation gates remain open.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import EvidenceClass, metadata_for


class R2RemediationError(RuntimeError):
    """Raised when an R2 finding is assigned a stale or unsupported disposition."""


@dataclass(frozen=True)
class R2RemediationSummary:
    """Accounting for the reviewer-facing, non-result R2 remediation ledger."""

    status: str
    finding_count: int
    open_finding_count: int
    protocol_fallback_count: int
    bounded_pass_count: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise R2RemediationError(f"{label} must be an object")
    return dict(value)


@dataclass(frozen=True)
class _Source:
    relative: str
    label: str
    payload: dict[str, Any]
    sha256: str


class R2RemediationWorkflow:
    """Freeze current R2 finding states against the receipts that support them."""

    AUDIT_ID = "bioif-r2-remediation-status-v1.6.0"
    AUDITED_AT = "2026-08-13T00:00:00+00:00"
    LEDGER_RELATIVE = "docs/review_round_2/R2_CURRENT_EVIDENCE_STATUS.md"
    OUTPUT_RELATIVE = "reports/review_round_2/remediation_status/v1.6.0"
    RECEIPTS = {
        "semantics": (
            "reports/review_round_2/evidence_semantics/v1.2.0/audit_receipt.json",
            "R2 evidence-semantics receipt",
        ),
        "profile": (
            "reports/review_round_2/real_proteomics_result_profile/v1.0.0/result_profile_receipt.json",
            "T123 result-profile receipt",
        ),
        "admission": (
            "reports/review_round_2/cc0_target_admission/v1.0.0/target_admission_receipt.json",
            "T129 initial admission receipt",
        ),
        "discovery": (
            "reports/review_round_2/cc0_target_discovery/v1.0.0/target_discovery_receipt.json",
            "T129 discovery receipt",
        ),
        "pxd030327_unit_map": (
            "reports/review_round_2/cc0_pxd030327_unit_map/v1.0.0/unit_map_correction_receipt.json",
            "T129 PXD030327 unit-map correction receipt",
        ),
        "t129_current_target_evidence": (
            "reports/review_round_2/t129_current_target_evidence/v1.2.0/current_target_evidence_receipt.json",
            "T129 current consolidated target-evidence receipt",
        ),
        "pxd017052_source_data": (
            "reports/review_round_2/pxd017052_source_data/v1.0.0/pxd017052_source_data_receipt.json",
            "T131 PXD017052 source-data receipt",
        ),
        "independent": (
            "reports/review_round_2/independent_evaluation/v1.0.0/readiness_receipt.json",
            "T124 independent-evaluation readiness receipt",
        ),
        "related_work": (
            "reports/review_round_2/related_work/v1.1.0/related_work_receipt.json",
            "R2 related-work receipt",
        ),
        "public_release": (
            "reports/review_round_2/public_release_audit/v1.2.5/audit_receipt.json",
            "R2 public-release receipt",
        ),
        "figures": (
            "reports/review_round_2/submission_figures/v1.1.0/generation_receipt.json",
            "R2 protocol-figure receipt",
        ),
        "portfolio": (
            "reports/review_round_2/manuscript_portfolio/v1.4.0/portfolio_receipt.json",
            "R2 manuscript-portfolio receipt",
        ),
        "acceptance": (
            "reports/review_round_2/r2_acceptance/v1.4.0/acceptance_readiness_receipt.json",
            "R2 acceptance-readiness receipt",
        ),
    }
    DISPOSITIONS = {
        "R2-01": "OPEN_EMPIRICAL_TARGET_UNAVAILABLE",
        "R2-02": "FALLBACK_PROTOCOL_ONLY_VERIFIED",
        "R2-03": "OPEN_STATISTICAL_VALIDATION_UNAVAILABLE",
        "R2-04": "FALLBACK_SOFTWARE_REPLAY_BOUNDARY_VERIFIED",
        "R2-05": "PASS_LITERATURE_AND_DOMAIN_PACKET",
        "R2-06": "PASS_PUBLIC_RELEASE_AUDIT",
        "R2-07": "FALLBACK_PROTOCOL_FIGURE_QA_VERIFIED",
        "R2-08": "FALLBACK_MERGED_PROTOCOL_PORTFOLIO_VERIFIED",
        "R2-09": "OPEN_EXTERNAL_ACCEPTANCE_REQUIRED",
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    def _path(self, relative: str, label: str) -> Path:
        path = (self.root / relative).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R2RemediationError(f"{label} is missing or outside the repository")
        return path

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R2RemediationError(f"cannot parse {label}") from exc

    @staticmethod
    def _require(condition: bool, label: str) -> None:
        if not condition:
            raise R2RemediationError(f"current R2 evidence no longer supports {label}")

    def _sources(self) -> dict[str, _Source]:
        return {
            key: _Source(
                relative,
                label,
                self._json(self._path(relative, label), label),
                _sha256(self._path(relative, label)),
            )
            for key, (relative, label) in self.RECEIPTS.items()
        }

    def _check_ledger(self) -> str:
        ledger_path = self._path(self.LEDGER_RELATIVE, "R2 current evidence status ledger")
        try:
            ledger = ledger_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise R2RemediationError("cannot read R2 current evidence status ledger") from exc
        for finding_id, disposition in self.DISPOSITIONS.items():
            self._require(
                f"| {finding_id} |" in ledger and disposition in ledger,
                f"the reviewer-readable disposition for {finding_id}",
            )
        return _sha256(ledger_path)

    def _findings(self, sources: dict[str, _Source]) -> list[dict[str, Any]]:
        profile = sources["profile"].payload
        admission = sources["admission"].payload
        discovery = sources["discovery"].payload
        pxd030327_unit_map = sources["pxd030327_unit_map"].payload
        t129_current_target_evidence = sources["t129_current_target_evidence"].payload
        pxd017052_source_data = sources["pxd017052_source_data"].payload
        independent = sources["independent"].payload
        semantics = sources["semantics"].payload
        related_work = sources["related_work"].payload
        public_release = sources["public_release"].payload
        figures = sources["figures"].payload
        portfolio = sources["portfolio"].payload
        acceptance = sources["acceptance"].payload

        self._require(
            profile.get("status") == "REAL_RESULT_PROFILE_COMPLETE_NOT_A_MODEL_TARGET"
            and profile.get("compatible_cross_study_target_count") == 0
            and profile.get("target_status") == "NOT_FROZEN"
            and profile.get("model_fitted") is False
            and profile.get("model_use") == "PROHIBITED",
            "R2-01",
        )
        self._require(
            t129_current_target_evidence.get("status")
            == "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET"
            and t129_current_target_evidence.get("candidate_source_count") == 6
            and t129_current_target_evidence.get("candidate_laboratory_count") == 5
            and t129_current_target_evidence.get("verified_source_asset_count") == 24
            and t129_current_target_evidence.get("admissible_target_count") == 0
            and t129_current_target_evidence.get("target_status") == "NOT_FROZEN"
            and t129_current_target_evidence.get("model_use") == "PROHIBITED"
            and t129_current_target_evidence.get("model_fitted") is False,
            "R2-01",
        )
        self._require(
            pxd017052_source_data.get("status")
            == "VERIFIED_PUBLIC_ASSETS_INCOMPLETE_SOURCE_UNIT_TO_PARTICLE_MAP"
            and pxd017052_source_data.get("official_asset_count") == 4
            and pxd017052_source_data.get("result_to_raw_match_count") == 9
            and pxd017052_source_data.get("explicit_raw_to_particle_map_count") == 0
            and pxd017052_source_data.get("admission") == "NOT_ADMITTED"
            and pxd017052_source_data.get("model_use") == "PROHIBITED"
            and pxd017052_source_data.get("model_fitted") is False,
            "R2-01",
        )
        self._require(
            pxd030327_unit_map.get("status") == "VERIFIED_SINGLE_LAB_UNIT_MAP_NOT_ADMITTED"
            and pxd030327_unit_map.get("unexcluded_unit_count") == 636
            and pxd030327_unit_map.get("unique_matrix_run_count") == 819
            and pxd030327_unit_map.get("unmapped_matrix_column_count") == 183
            and pxd030327_unit_map.get("admission") == "NOT_ADMITTED"
            and pxd030327_unit_map.get("model_use") == "PROHIBITED"
            and pxd030327_unit_map.get("model_fitted") is False,
            "R2-01",
        )
        self._require(
            admission.get("status") == "BLOCKED_NO_CC0_COMMON_TARGET"
            and admission.get("admissible_target_count") == 0
            and admission.get("target_status") == "NOT_FROZEN"
            and discovery.get("status")
            == "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES"
            and discovery.get("admissible_target_count") == 0
            and discovery.get("target_status") == "NOT_FROZEN",
            "R2-01",
        )
        self._require(
            independent.get("status") == "BLOCKED_T123_COMPATIBLE_TARGET_REQUIRED"
            and independent.get("external_evaluator_receipt_verified") is False
            and independent.get("protected_observations_accessed") is False,
            "R2-02",
        )
        self._require(
            profile.get("paired_ablations_run") is False
            and profile.get("external_ood_evaluated") is False
            and profile.get("negative_controls_run") is False
            and independent.get("compatible_target_count") == 0,
            "R2-03",
        )
        self._require(
            semantics.get("status") == "PASS_EVIDENCE_SEMANTICS_WITH_QUARANTINED_LEGACY_FIXTURES"
            and semantics.get("blocking_findings") == 0
            and semantics.get("quarantined_historical_finding_count") == 1
            and semantics.get("historical_sources_mutated") is False,
            "R2-04",
        )
        self._require(
            related_work.get("status") == "PASS_RELATED_WORK_EVIDENCE_PACKET"
            and related_work.get("citation_count") == 12
            and related_work.get("comparator_count") == 8
            and related_work.get("glossary_term_count") == 7
            and related_work.get("scientific_submission_ready") is False,
            "R2-05",
        )
        self._require(
            public_release.get("status") == "PASS_PUBLIC_RELEASE_AUDIT"
            and public_release.get("historical_fixture_bundle_publicly_released") is False
            and public_release.get("scientific_submission_ready") is False,
            "R2-06",
        )
        self._require(
            figures.get("status") == "PASS_R2_PROTOCOL_FIGURE_SUITE"
            and figures.get("figure_count") == 3
            and figures.get("field_mapped") is True
            and figures.get("geometry_qa") == "PASS"
            and figures.get("semantic_qa") == "PASS"
            and figures.get("empirical_values_rendered") is False
            and figures.get("scientific_submission_ready") is False,
            "R2-07",
        )
        self._require(
            portfolio.get("status") == "BLOCKED_R2_MANUSCRIPTS_PENDING_T123_T124"
            and portfolio.get("manuscript_count") == 2
            and portfolio.get("legacy_withdrawal_count") == 15
            and portfolio.get("historical_fixture_manuscripts_reused") is False
            and portfolio.get("scientific_submission_ready") is False,
            "R2-08",
        )
        self._require(
            acceptance.get("status") == "BLOCKED_R2_EXTERNAL_EVIDENCE_REQUIRED"
            and acceptance.get("prerequisite_blocker_count") == 9
            and acceptance.get("external_reproduction_verified") is False
            and acceptance.get("editorial_rereview_verified") is False
            and acceptance.get("scientific_submission_ready") is False,
            "R2-09",
        )
        return [
            {
                "finding_id": "R2-01",
                "disposition": self.DISPOSITIONS["R2-01"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "PXD030327 now has a verified 636-unit run map, while PXD017052 now has "
                    "four verified CC-BY assets and nine result-to-raw links; neither source "
                    "freezes a cross-study numeric-material target."
                ),
                "evidence_source_keys": [
                    "profile",
                    "admission",
                    "discovery",
                    "pxd030327_unit_map",
                    "t129_current_target_evidence",
                    "pxd017052_source_data",
                ],
            },
            {
                "finding_id": "R2-02",
                "disposition": self.DISPOSITIONS["R2-02"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "Paper C is retained only as a protocol until an independent evaluator "
                    "verifies protected observations."
                ),
                "evidence_source_keys": ["independent", "portfolio"],
            },
            {
                "finding_id": "R2-03",
                "disposition": self.DISPOSITIONS["R2-03"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "No estimand, model, ablation, OOD evaluation or effective-sample analysis "
                    "is admitted without a frozen target."
                ),
                "evidence_source_keys": ["profile", "independent"],
            },
            {
                "finding_id": "R2-04",
                "disposition": self.DISPOSITIONS["R2-04"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "The historical fixture wording is source-hash quarantined and excluded from "
                    "current R2 manuscripts and public release; it is not a replication result."
                ),
                "evidence_source_keys": ["semantics"],
            },
            {
                "finding_id": "R2-05",
                "disposition": self.DISPOSITIONS["R2-05"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "The literature/comparator/glossary packet passed its bounded audit, "
                    "but it supplies no empirical validation."
                ),
                "evidence_source_keys": ["related_work"],
            },
            {
                "finding_id": "R2-06",
                "disposition": self.DISPOSITIONS["R2-06"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "Public-release integrity passed while historical fixture bundles remain "
                    "excluded and submission readiness remains false."
                ),
                "evidence_source_keys": ["public_release"],
            },
            {
                "finding_id": "R2-07",
                "disposition": self.DISPOSITIONS["R2-07"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "Three field-mapped protocol figures passed geometry and semantic QA; "
                    "no empirical values are rendered."
                ),
                "evidence_source_keys": ["figures"],
            },
            {
                "finding_id": "R2-08",
                "disposition": self.DISPOSITIONS["R2-08"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "The portfolio uses a merged A+B route and keeps C protocol-only, "
                    "pending T123/T124 rather than presenting results manuscripts."
                ),
                "evidence_source_keys": ["portfolio"],
            },
            {
                "finding_id": "R2-09",
                "disposition": self.DISPOSITIONS["R2-09"],
                "scientific_claim_ready": False,
                "reviewer_readable_disposition": (
                    "External reproduction and editorial re-review remain absent; the acceptance "
                    "audit lists nine blockers and submission readiness is false."
                ),
                "evidence_source_keys": ["acceptance"],
            },
        ]

    def run(self, *, strict: bool = False) -> R2RemediationSummary:
        """Write an immutable, current-state R2 remediation receipt."""
        if not strict:
            raise R2RemediationError("R2 remediation status audit requires --strict")
        if self.output_root.exists():
            raise R2RemediationError("R2 remediation status audit already executed")
        ledger_sha256 = self._check_ledger()
        sources = self._sources()
        findings = self._findings(sources)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": "PARTIALLY_REMEDIATED_R2_EVIDENCE_GAPS_REMAIN",
            **metadata_for(EvidenceClass.DEVELOPMENT_OBSERVATION),
            "reviewer_ledger_path": self.LEDGER_RELATIVE,
            "reviewer_ledger_sha256": ledger_sha256,
            "source_receipts": {
                key: {"path": source.relative, "sha256": source.sha256}
                for key, source in sources.items()
            },
            "finding_count": len(findings),
            "open_finding_count": 3,
            "protocol_fallback_count": 4,
            "bounded_pass_count": 2,
            "findings": findings,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "remediation_status_report.json"
        receipt_path = self.output_root / "remediation_status_receipt.json"
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "remediation_status_report_sha256": _sha256(report_path),
            "finding_count": report["finding_count"],
            "open_finding_count": report["open_finding_count"],
            "protocol_fallback_count": report["protocol_fallback_count"],
            "bounded_pass_count": report["bounded_pass_count"],
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return R2RemediationSummary(
            status=report["status"],
            finding_count=len(findings),
            open_finding_count=3,
            protocol_fallback_count=4,
            bounded_pass_count=2,
            receipt_path=receipt_path,
        )

    def verify(self) -> R2RemediationSummary:
        """Verify the receipt and source hashes without substituting fresh evidence."""
        report_path = self.output_root / "remediation_status_report.json"
        receipt_path = self.output_root / "remediation_status_receipt.json"
        report = self._json(report_path, "R2 remediation status report")
        receipt = self._json(receipt_path, "R2 remediation status receipt")
        required_counts = {
            "finding_count": 9,
            "open_finding_count": 3,
            "protocol_fallback_count": 4,
            "bounded_pass_count": 2,
        }
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != "PARTIALLY_REMEDIATED_R2_EVIDENCE_GAPS_REMAIN"
            or receipt.get("status") != report.get("status")
            or receipt.get("remediation_status_report_sha256") != _sha256(report_path)
            or report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
            or any(
                report.get(key) != value or receipt.get(key) != value
                for key, value in required_counts.items()
            )
        ):
            raise R2RemediationError("R2 remediation status receipt is invalid")
        sources = _mapping(report.get("source_receipts"), "R2 remediation source receipts")
        if set(sources) != set(self.RECEIPTS):
            raise R2RemediationError("R2 remediation source receipt inventory is invalid")
        for key, source in sources.items():
            source_mapping = _mapping(source, f"R2 remediation source receipt {key}")
            relative, _ = self.RECEIPTS[key]
            path = self._path(relative, f"R2 remediation source receipt {key}")
            if source_mapping != {"path": relative, "sha256": _sha256(path)}:
                raise R2RemediationError("R2 remediation source receipt hash is stale")
        if report.get("reviewer_ledger_sha256") != self._check_ledger():
            raise R2RemediationError("R2 remediation reviewer ledger hash is stale")
        findings = report.get("findings")
        if not isinstance(findings, list) or [
            item.get("finding_id") for item in findings if isinstance(item, Mapping)
        ] != list(self.DISPOSITIONS):
            raise R2RemediationError("R2 remediation finding inventory is invalid")
        if any(
            not isinstance(item, Mapping)
            or item.get("disposition") != self.DISPOSITIONS[item.get("finding_id")]
            or item.get("scientific_claim_ready") is not False
            for item in findings
        ):
            raise R2RemediationError("R2 remediation finding state is invalid")
        return R2RemediationSummary(
            status=report["status"],
            finding_count=9,
            open_finding_count=3,
            protocol_fallback_count=4,
            bounded_pass_count=2,
            receipt_path=receipt_path,
        )
