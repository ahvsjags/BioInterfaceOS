"""Verify the analysis-only PNNL/PMC3252235 full-text source screen.

The supplementary XLS is intentionally not promoted to a public data asset:
the file is byte-verifiable but its redistributable licence is unresolved and
its overlap with the frozen R3 target universe is below the preregistered
coverage threshold.  This workflow records that negative decision instead of
silently changing the target or missingness rules.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4PMC3252235SourceScreenError(RuntimeError):
    """Raised when the byte-verified negative source screen is invalid."""


@dataclass(frozen=True)
class R4PMC3252235SourceScreenSummary:
    """Machine-readable summary of the rejected full-text source."""

    source_bytes: int
    direct_overlap_accessions: int
    measurement_columns: int
    rank_qualified_columns: int
    receipt_path: Path


class R4PMC3252235SourceScreenWorkflow:
    """Create and verify the PNNL source-screen receipt."""

    SCREEN_RELATIVE = "docs/data/R4_T184_PMC3252235_SOURCE_SCREEN.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pmc3252235_source_screen/v1.0.0"
    AUDIT_ID = "bioif-r4-pmc3252235-source-screen-v1.0.0"
    STATUS = "REJECTED_FROM_FROZEN_R3_OOD_AND_PUBLIC_RELEASE_ANALYSIS_ONLY_CANDIDATE"

    def __init__(self, root: Path, assets_root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.assets_root = assets_root.resolve(strict=False)
        self.screen_path = self.root / self.SCREEN_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4PMC3252235SourceScreenError(f"cannot parse {label}") from exc

    def _screen(self) -> dict[str, Any]:
        screen = self._json(self.screen_path, "T184 source screen")
        if screen.get("screen_id") != self.AUDIT_ID:
            raise R4PMC3252235SourceScreenError("T184 screen ID is invalid")
        if screen.get("evidence_class") != "SOURCE_SCREENING_ONLY":
            raise R4PMC3252235SourceScreenError("T184 evidence class is invalid")
        if screen.get("allowed_claim_level") != "NONE":
            raise R4PMC3252235SourceScreenError("T184 claim level is invalid")
        if _mapping(screen.get("decision"), "T184 decision").get("status") != self.STATUS:
            raise R4PMC3252235SourceScreenError("T184 decision status is invalid")
        asset = _mapping(screen.get("source_asset"), "T184 source asset")
        relative_path = _string(asset.get("relative_path"), "T184 source asset path")
        if relative_path.startswith("/") or "\\" in relative_path or ".." in Path(relative_path).parts:
            raise R4PMC3252235SourceScreenError("T184 source asset path is unsafe")
        source_path = (self.root / relative_path).resolve(strict=False)
        if not source_path.is_relative_to(self.root) or not source_path.is_file():
            raise R4PMC3252235SourceScreenError("T184 source asset is missing")
        if source_path.stat().st_size != int(asset.get("bytes", -1)):
            raise R4PMC3252235SourceScreenError("T184 source asset byte count differs")
        if _sha256(source_path) != _checksum(asset.get("sha256"), "T184 source asset checksum"):
            raise R4PMC3252235SourceScreenError("T184 source asset checksum differs")
        compatibility = _mapping(screen.get("compatibility_probe"), "T184 compatibility probe")
        if compatibility.get("direct_exact_uniprot_overlap") != 2:
            raise R4PMC3252235SourceScreenError("T184 overlap count changed")
        if compatibility.get("rank_qualified_columns_at_frozen_minimum_10") != 0:
            raise R4PMC3252235SourceScreenError("T184 qualification count changed")
        table = _mapping(screen.get("table_contract"), "T184 table contract")
        if table.get("measurement_columns") != 24 or table.get("quantified_protein_count_reported_by_article") != 88:
            raise R4PMC3252235SourceScreenError("T184 table contract changed")
        return screen

    def run(self, *, strict: bool = False) -> R4PMC3252235SourceScreenSummary:
        if not strict:
            raise R4PMC3252235SourceScreenError("T184 source screen requires --strict")
        if self.output_root.exists():
            raise R4PMC3252235SourceScreenError("T184 source screen already executed")
        screen = self._screen()
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "r4_pmc3252235_source_screen_report.json"
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "screen_relative_path": self.SCREEN_RELATIVE,
            "screen_sha256": _sha256(self.screen_path),
            "source_asset": screen["source_asset"],
            "compatibility_probe": screen["compatibility_probe"],
            "decision": screen["decision"],
            "scientific_submission_ready": False,
        }
        report_path.write_bytes(_canonical(report))
        receipt_path = self.output_root / "r4_pmc3252235_source_screen_receipt.json"
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "source_bytes": screen["source_asset"]["bytes"],
            "direct_overlap_accessions": screen["compatibility_probe"]["direct_exact_uniprot_overlap"],
            "measurement_columns": screen["table_contract"]["measurement_columns"],
            "rank_qualified_columns": screen["compatibility_probe"]["rank_qualified_columns_at_frozen_minimum_10"],
            "model_fitted": False,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path.write_bytes(_canonical(receipt))
        return R4PMC3252235SourceScreenSummary(
            int(receipt["source_bytes"]),
            int(receipt["direct_overlap_accessions"]),
            int(receipt["measurement_columns"]),
            int(receipt["rank_qualified_columns"]),
            receipt_path,
        )

    def verify(self) -> R4PMC3252235SourceScreenSummary:
        self._screen()
        report_path = self.output_root / "r4_pmc3252235_source_screen_report.json"
        receipt_path = self.output_root / "r4_pmc3252235_source_screen_receipt.json"
        report = self._json(report_path, "T184 source screen report")
        receipt = self._json(receipt_path, "T184 source screen receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("screen_sha256") != _sha256(self.screen_path)
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("model_fitted") is not False
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4PMC3252235SourceScreenError("T184 source screen receipt is invalid")
        return R4PMC3252235SourceScreenSummary(
            int(receipt["source_bytes"]),
            int(receipt["direct_overlap_accessions"]),
            int(receipt["measurement_columns"]),
            int(receipt["rank_qualified_columns"]),
            receipt_path,
        )
