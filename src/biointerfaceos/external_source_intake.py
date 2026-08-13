"""Fail closed when an external R2 source package lacks auditable structure.

This module deliberately verifies only the structure and byte integrity of an
externally supplied package.  It does not decide that a source is scientifically
admissible, freeze a target, or run a model.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    require_metadata,
)


class ExternalSourceIntakeError(RuntimeError):
    """Raised when an external source package cannot enter the audit queue."""


@dataclass(frozen=True)
class ExternalSourceIntakeSummary:
    """Non-promoting result of a structurally complete source preflight."""

    status: str
    intake_id: str
    source_count: int
    laboratory_count: int
    source_asset_count: int
    analysis_unit_count: int


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalSourceIntakeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExternalSourceIntakeError(f"{label} must be a non-empty string")
    return value.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _checksum(value: Any, label: str) -> str:
    checksum = _string(value, label)
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise ExternalSourceIntakeError(f"{label} must be a lowercase SHA-256")
    return checksum


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ExternalSourceIntakeError(f"{label} must be a finite numeric value")
    number = float(value)
    if not math.isfinite(number):
        raise ExternalSourceIntakeError(f"{label} must be a finite numeric value")
    return number


class ExternalSourceIntakeWorkflow:
    """Preflight a contributor-held external source package without promotion."""

    STATUS = "STRUCTURALLY_COMPLETE_REQUIRES_SOURCE_AUDIT"
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "submission_state",
        "intake_id",
        "submitted_at",
        "evidence_class",
        "allowed_claim_level",
        "target_admission_requested",
        "source_records",
    }
    REQUIRED_SOURCE = {
        "source_id",
        "source_accession_or_doi",
        "official_repository_or_publisher_locator",
        "source_license",
        "laboratory_affiliation",
        "human_biofluid",
        "assay_and_acquisition_context",
        "author_scale_segregated",
        "source_assets",
        "analysis_units",
    }
    REQUIRED_ASSET = {"asset_id", "relative_path", "sha256"}
    REQUIRED_UNIT = {
        "analysis_unit_id",
        "source_file_or_result_id",
        "material_identity",
        "numeric_material_or_size_covariate",
        "biological_role",
        "replicate_role",
        "shared_endpoint_value",
        "endpoint_unit_or_scale",
        "shared_preprocessing_version",
        "source_asset_checksum",
    }
    REQUIRED_COVARIATE = {"name", "value", "unit"}

    def __init__(self, manifest_path: Path, assets_root: Path) -> None:
        self.manifest_path = manifest_path.resolve(strict=False)
        self.assets_root = assets_root.resolve(strict=False)

    @staticmethod
    def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
        result = _mapping(value, label)
        if set(result) != expected:
            raise ExternalSourceIntakeError(f"{label} fields are incomplete or unexpected")
        return result

    def _asset_path(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise ExternalSourceIntakeError(f"{label} must use a relative POSIX path")
        pure_path = PurePosixPath(relative_path)
        if pure_path.is_absolute() or not pure_path.parts or ".." in pure_path.parts:
            raise ExternalSourceIntakeError(f"{label} escapes the declared assets root")
        path = (self.assets_root / Path(*pure_path.parts)).resolve(strict=False)
        if not path.is_relative_to(self.assets_root) or not path.is_file():
            raise ExternalSourceIntakeError(
                f"{label} is missing or outside the declared assets root"
            )
        return path

    @staticmethod
    def _https_locator(value: Any, label: str) -> str:
        locator = _string(value, label)
        parsed = urlparse(locator)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ExternalSourceIntakeError(f"{label} must be an official HTTPS locator")
        return locator

    @staticmethod
    def _submitted_at(value: Any) -> str:
        submitted_at = _string(value, "submitted_at")
        try:
            parsed = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ExternalSourceIntakeError("submitted_at must be an RFC3339 timestamp") from exc
        if parsed.tzinfo is None:
            raise ExternalSourceIntakeError("submitted_at must include a timezone")
        return submitted_at

    def _package(self) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            raise ExternalSourceIntakeError("external source manifest is missing")
        if not self.assets_root.is_dir():
            raise ExternalSourceIntakeError("external source assets root is missing")
        try:
            package = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExternalSourceIntakeError("external source manifest cannot be parsed") from exc
        package = self._exact_keys(package, self.REQUIRED_TOP_LEVEL, "external source manifest")
        if package["schema_version"] != 1:
            raise ExternalSourceIntakeError("external source manifest schema version is invalid")
        if package["submission_state"] != "SUBMITTED_FOR_PREFLIGHT":
            raise ExternalSourceIntakeError(
                "external source manifest is not a submitted preflight package"
            )
        if package["target_admission_requested"] is not False:
            raise ExternalSourceIntakeError("external source manifest attempts target admission")
        _string(package["intake_id"], "intake_id")
        self._submitted_at(package["submitted_at"])
        try:
            evidence_class, claim_level = require_metadata(package, "external source manifest")
        except EvidenceSemanticsError as exc:
            raise ExternalSourceIntakeError("external source manifest metadata is invalid") from exc
        if (
            evidence_class is not EvidenceClass.DEVELOPMENT_OBSERVATION
            or claim_level is not AllowedClaimLevel.EXPLORATORY
        ):
            raise ExternalSourceIntakeError("external source manifest claim level is invalid")
        source_records = package["source_records"]
        if not isinstance(source_records, list) or len(source_records) < 2:
            raise ExternalSourceIntakeError("source_records has too few entries")
        return package

    def _source_assets(self, source: dict[str, Any], source_id: str) -> dict[str, str]:
        assets = source["source_assets"]
        if not isinstance(assets, list) or not assets:
            raise ExternalSourceIntakeError(f"{source_id} must declare at least one source asset")
        resolved_assets: dict[str, str] = {}
        for asset_value in assets:
            asset = self._exact_keys(asset_value, self.REQUIRED_ASSET, f"{source_id} source asset")
            asset_id = _string(asset["asset_id"], f"{source_id} source asset id")
            if asset_id in resolved_assets:
                raise ExternalSourceIntakeError(f"{source_id} repeats source asset id {asset_id}")
            relative_path = _string(asset["relative_path"], f"{source_id} asset path")
            expected_checksum = _checksum(asset["sha256"], f"{source_id} asset checksum")
            actual_checksum = _sha256(self._asset_path(relative_path, f"{source_id} asset path"))
            if actual_checksum != expected_checksum:
                raise ExternalSourceIntakeError(f"{source_id} asset checksum does not match bytes")
            resolved_assets[asset_id] = expected_checksum
        return resolved_assets

    @staticmethod
    def _unit(
        value: Any,
        source_id: str,
        assets: dict[str, str],
        unit_ids: set[str],
    ) -> tuple[str, str, str]:
        unit = ExternalSourceIntakeWorkflow._exact_keys(
            value, ExternalSourceIntakeWorkflow.REQUIRED_UNIT, f"{source_id} analysis unit"
        )
        unit_id = _string(unit["analysis_unit_id"], f"{source_id} analysis unit id")
        if unit_id in unit_ids:
            raise ExternalSourceIntakeError(f"analysis unit id is not globally unique: {unit_id}")
        unit_ids.add(unit_id)
        source_asset_id = _string(
            unit["source_file_or_result_id"], f"{source_id} source file or result id"
        )
        if source_asset_id not in assets:
            raise ExternalSourceIntakeError(
                f"{source_id} analysis unit does not reference a source asset"
            )
        if _checksum(unit["source_asset_checksum"], f"{source_id} unit asset checksum") != assets[
            source_asset_id
        ]:
            raise ExternalSourceIntakeError(
                f"{source_id} analysis unit asset checksum is not source-matched"
            )
        _string(unit["material_identity"], f"{source_id} material identity")
        covariate = ExternalSourceIntakeWorkflow._exact_keys(
            unit["numeric_material_or_size_covariate"],
            ExternalSourceIntakeWorkflow.REQUIRED_COVARIATE,
            f"{source_id} numeric material or size covariate",
        )
        _string(covariate["name"], f"{source_id} covariate name")
        _finite_number(covariate["value"], f"{source_id} covariate value")
        _string(covariate["unit"], f"{source_id} covariate unit")
        _string(unit["biological_role"], f"{source_id} biological role")
        _string(unit["replicate_role"], f"{source_id} replicate role")
        _finite_number(unit["shared_endpoint_value"], f"{source_id} shared endpoint value")
        endpoint_unit = _string(unit["endpoint_unit_or_scale"], f"{source_id} endpoint unit")
        preprocessing = _string(
            unit["shared_preprocessing_version"], f"{source_id} preprocessing version"
        )
        return unit_id, endpoint_unit, preprocessing

    def run(self, *, strict: bool = False) -> ExternalSourceIntakeSummary:
        """Verify an externally received package without admitting it as a target."""
        if not strict:
            raise ExternalSourceIntakeError("external source preflight requires --strict")
        package = self._package()
        source_ids: set[str] = set()
        laboratories: set[str] = set()
        unit_ids: set[str] = set()
        endpoint_units: set[str] = set()
        preprocessing_versions: set[str] = set()
        asset_owners: dict[str, str] = {}
        source_asset_count = 0

        for source_value in package["source_records"]:
            source = self._exact_keys(source_value, self.REQUIRED_SOURCE, "external source record")
            source_id = _string(source["source_id"], "source id")
            if source_id in source_ids:
                raise ExternalSourceIntakeError(f"source id is not unique: {source_id}")
            source_ids.add(source_id)
            _string(source["source_accession_or_doi"], f"{source_id} accession or DOI")
            self._https_locator(
                source["official_repository_or_publisher_locator"], f"{source_id} official locator"
            )
            if _string(source["source_license"], f"{source_id} source licence") != "CC0-1.0":
                raise ExternalSourceIntakeError(
                    f"{source_id} is not eligible for the CC0-only route"
                )
            laboratory = _string(source["laboratory_affiliation"], f"{source_id} laboratory")
            laboratories.add(laboratory.casefold())
            biofluid = _string(source["human_biofluid"], f"{source_id} human biofluid")
            if "human" not in biofluid.casefold():
                raise ExternalSourceIntakeError(f"{source_id} does not declare a human biofluid")
            _string(source["assay_and_acquisition_context"], f"{source_id} assay context")
            if source["author_scale_segregated"] is not True:
                raise ExternalSourceIntakeError(
                    f"{source_id} does not segregate author quantification"
                )
            assets = self._source_assets(source, source_id)
            for checksum in assets.values():
                prior_owner = asset_owners.setdefault(checksum, source_id)
                if prior_owner != source_id:
                    raise ExternalSourceIntakeError(
                        "external source package reuses one source asset across laboratories"
                    )
            source_asset_count += len(assets)
            units = source["analysis_units"]
            if not isinstance(units, list) or not units:
                raise ExternalSourceIntakeError(f"{source_id} must declare analysis units")
            for unit in units:
                _, endpoint_unit, preprocessing = self._unit(unit, source_id, assets, unit_ids)
                endpoint_units.add(endpoint_unit)
                preprocessing_versions.add(preprocessing)

        if len(laboratories) < 2:
            raise ExternalSourceIntakeError(
                "external source package has fewer than two laboratories"
            )
        if len(endpoint_units) != 1 or len(preprocessing_versions) != 1:
            raise ExternalSourceIntakeError(
                "external source package does not declare one shared endpoint and preprocessing"
            )
        return ExternalSourceIntakeSummary(
            status=self.STATUS,
            intake_id=_string(package["intake_id"], "intake_id"),
            source_count=len(source_ids),
            laboratory_count=len(laboratories),
            source_asset_count=source_asset_count,
            analysis_unit_count=len(unit_ids),
        )
