"""Audit first-party supplementary-file access without admitting the pair.

The T140 article screen found a promising two-laboratory pair, but article
pages are not byte-level data releases.  T142 records the exact supplementary
assets named by the primary pages, the access/licence observation, and the
remaining handoff requirements.  It never downloads, redistributes, or
promotes a source to the T129 cohort.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TwoLabCoronaAssetAuditError(RuntimeError):
    """Raised when the first-party asset boundary is weakened."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TwoLabCoronaAssetAuditError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwoLabCoronaAssetAuditError(f"{label} must be a non-empty string")
    return value.strip()


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise TwoLabCoronaAssetAuditError(f"{label} must contain at least {minimum} items")
    return value


@dataclass(frozen=True)
class TwoLabCoronaAssetAuditSummary:
    """Non-admission accounting for the first-party asset audit."""

    asset_count: int
    source_count: int
    byte_verified_count: int
    redistributable_count: int
    status: str
    receipt_path: Path


class TwoLabCoronaAssetAuditWorkflow:
    """Freeze a page-level supplementary inventory and its access boundary."""

    AUDIT_ID = "bioif-r2-two-lab-corona-asset-audit-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T140_SUPPLEMENT_ASSET_AUDIT_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/two_lab_corona_asset_audit/v1.0.0"
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "access_scope",
        "assets",
        "decision",
    }
    REQUIRED_ASSET_FIELDS = {
        "source_id",
        "asset_name",
        "asset_type",
        "declared_size",
        "article_locator",
        "asset_locator",
        "page_observation",
        "byte_verified",
        "reuse_terms",
        "redistributable",
        "unit_map_verified",
    }
    EXPECTED_ASSETS = {
        ("PNAS-2008-LUNDQVIST", "supp_105_38_14265__index.html"),
        ("PNAS-2008-LUNDQVIST", "0805135105_0805135105SI.pdf"),
        ("PNAS-2008-LUNDQVIST", "0805135105_ST1.xls"),
        ("PROTEOMICS-2011-ZHANG", "NIHMS344183-supplement-Supp_Figure.doc"),
        ("PROTEOMICS-2011-ZHANG", "NIHMS344183-supplement-Supp_Tables.xls"),
    }
    STATUS = "BLOCKED_FIRST_PARTY_BYTES_LICENCE_UNIT_MAP_AND_SHARED_ENDPOINT_REQUIRED"

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
            raise TwoLabCoronaAssetAuditError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T142 asset registry")
        if set(registry) != self.REQUIRED_TOP_LEVEL or registry.get("schema_version") != 1:
            raise TwoLabCoronaAssetAuditError("T142 registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise TwoLabCoronaAssetAuditError("T142 registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise TwoLabCoronaAssetAuditError("T142 evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise TwoLabCoronaAssetAuditError("T142 claim level is unsafe")
        _string(registry.get("evaluated_at"), "T142 evaluated_at")
        scope = _mapping(registry.get("access_scope"), "T142 access scope")
        required_scope = {
            "source_pair_audit_id",
            "normal_access_only",
            "bulk_downloaded",
            "page_metadata_verified",
            "asset_bytes_written",
            "access_observations",
        }
        if set(scope) != required_scope:
            raise TwoLabCoronaAssetAuditError("T142 access scope fields are invalid")
        if (
            scope.get("source_pair_audit_id") != "bioif-r2-two-lab-corona-pair-rescreen-v1.0.0"
            or scope.get("normal_access_only") is not True
            or scope.get("bulk_downloaded") is not False
            or scope.get("page_metadata_verified") is not True
            or scope.get("asset_bytes_written") is not False
        ):
            raise TwoLabCoronaAssetAuditError("T142 access boundary is unsafe")
        observations = _list(
            scope.get("access_observations"), "T142 access observations", minimum=2
        )
        if any(not isinstance(item, str) or not item.strip() for item in observations):
            raise TwoLabCoronaAssetAuditError("T142 access observation is invalid")

        assets: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for value in _list(registry.get("assets"), "T142 assets", minimum=5):
            asset = _mapping(value, "T142 asset")
            if set(asset) != self.REQUIRED_ASSET_FIELDS:
                raise TwoLabCoronaAssetAuditError("T142 asset fields are invalid")
            for field in self.REQUIRED_ASSET_FIELDS - {
                "declared_size",
                "byte_verified",
                "redistributable",
                "unit_map_verified",
            }:
                _string(asset.get(field), f"T142 asset {field}")
            key = (asset["source_id"], asset["asset_name"])
            if key in seen:
                raise TwoLabCoronaAssetAuditError("T142 asset is duplicated")
            seen.add(key)
            if asset.get("declared_size") not in {"101.5KB", "811.7KB", "730B", "2.9MB", "6.4MB"}:
                raise TwoLabCoronaAssetAuditError("T142 declared size is invalid")
            if not asset["article_locator"].startswith("https://") or not asset[
                "asset_locator"
            ].startswith("https://"):
                raise TwoLabCoronaAssetAuditError("T142 asset locator is invalid")
            if (
                asset["byte_verified"] is not False
                or asset["redistributable"] is not False
                or asset["unit_map_verified"] is not False
            ):
                raise TwoLabCoronaAssetAuditError("T142 asset was silently promoted")
            assets.append(asset)
        if seen != self.EXPECTED_ASSETS:
            raise TwoLabCoronaAssetAuditError("T142 asset inventory is incomplete or unexpected")
        decision = _mapping(registry.get("decision"), "T142 decision")
        required_decision = {
            "status",
            "byte_verified_asset_count",
            "redistributable_asset_count",
            "target_status",
            "model_use",
            "required_next_evidence",
        }
        if set(decision) != required_decision:
            raise TwoLabCoronaAssetAuditError("T142 decision fields are invalid")
        if (
            decision.get("status") != self.STATUS
            or decision.get("byte_verified_asset_count") != 0
            or decision.get("redistributable_asset_count") != 0
            or decision.get("target_status") != "NOT_FROZEN"
            or decision.get("model_use") != "PROHIBITED"
            or len(
                _list(decision.get("required_next_evidence"), "T142 next evidence", minimum=4)
            )
            != 4
        ):
            raise TwoLabCoronaAssetAuditError("T142 decision silently promotes the pair")
        return registry, assets

    def run(self, *, strict: bool = False) -> TwoLabCoronaAssetAuditSummary:
        if not strict:
            raise TwoLabCoronaAssetAuditError("T142 asset audit requires --strict")
        if self.output_root.exists():
            raise TwoLabCoronaAssetAuditError("T142 asset audit already executed")
        registry, assets = self._registry()
        decision = registry["decision"]
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "asset_count": len(assets),
            "source_count": len({asset["source_id"] for asset in assets}),
            "byte_verified_asset_count": 0,
            "redistributable_asset_count": 0,
            "unit_map_verified_asset_count": 0,
            "status": decision["status"],
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "assets": assets,
            "required_next_evidence": decision["required_next_evidence"],
            "model_fitted": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report["status"],
            "report_sha256": hashlib.sha256(_canonical(report)).hexdigest(),
            "asset_count": report["asset_count"],
            "source_count": report["source_count"],
            "byte_verified_asset_count": 0,
            "redistributable_asset_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        self._write(self.output_root / "asset_audit_report.json", report)
        self._write(self.output_root / "asset_audit_receipt.json", receipt)
        return TwoLabCoronaAssetAuditSummary(
            asset_count=5,
            source_count=2,
            byte_verified_count=0,
            redistributable_count=0,
            status=report["status"],
            receipt_path=self.output_root / "asset_audit_receipt.json",
        )

    def verify(self) -> TwoLabCoronaAssetAuditSummary:
        report_path = self.output_root / "asset_audit_report.json"
        receipt_path = self.output_root / "asset_audit_receipt.json"
        report = self._json(report_path, "T142 asset audit report")
        receipt = self._json(receipt_path, "T142 asset audit receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("status") != report.get("status")
            or receipt.get("report_sha256") != _sha256(report_path)
            or report.get("asset_count") != 5
            or report.get("source_count") != 2
            or report.get("byte_verified_asset_count") != 0
            or report.get("redistributable_asset_count") != 0
            or report.get("unit_map_verified_asset_count") != 0
            or report.get("target_status") != "NOT_FROZEN"
            or report.get("model_use") != "PROHIBITED"
            or report.get("scientific_submission_ready") is not False
        ):
            raise TwoLabCoronaAssetAuditError("T142 asset audit receipt is invalid")
        return TwoLabCoronaAssetAuditSummary(
            asset_count=5,
            source_count=2,
            byte_verified_count=0,
            redistributable_count=0,
            status=report["status"],
            receipt_path=receipt_path,
        )
