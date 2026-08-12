"""Strict preflight for a real, public T123 protein-corona source cohort.

The preflight establishes only an acquisition and preprocessing boundary.  It
does not harmonize author quantification outputs, freeze a biological target,
or permit model fitting.
"""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RealProteomicsSourcePreflightError(RuntimeError):
    """Raised when the T123 proteomics preflight contract is unsafe."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealProteomicsSourcePreflightError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise RealProteomicsSourcePreflightError(
            f"{label} must be a list with at least {minimum} items"
        )
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealProteomicsSourcePreflightError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RealProteomicsSourcePreflightError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class RealProteomicsSourcePreflightSummary:
    """Compact accounting for the source-acquisition boundary."""

    source_count: int
    source_defined_unit_count: int
    receipt_path: Path


class RealProteomicsSourcePreflightWorkflow:
    """Fail closed before heterogeneous public proteomics become a model target."""

    AUDIT_ID = "bioif-r2-real-proteomics-source-preflight-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T123_PROTEOMICS_SOURCE_PREFLIGHT.json"
    OUTPUT_RELATIVE = "reports/review_round_2/real_proteomics_source_preflight/v1.0.0"
    ALLOWED_LICENSES = frozenset({"CC0-1.0"})
    EXPECTED_SOURCE_UNITS = {
        "PRIDE-PXD017776": 12,
        "PRIDE-PXD052701": 10,
        "PRIDE-PXD032162": 8,
    }
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "development_cutoff",
        "evidence_class",
        "allowed_claim_level",
        "source_policy",
        "sources",
        "preprocessing_contract",
    }
    REQUIRED_POLICY_FIELDS = {
        "minimum_sources",
        "minimum_studies",
        "minimum_laboratories",
        "require_anonymous_public_access",
        "require_reusable_license",
        "require_human_biofluid_corona_context",
        "require_source_defined_sample_units",
        "require_preprocessing_before_target_freeze",
        "prohibit_author_quantification_concatenation",
        "allowed_licenses",
    }
    REQUIRED_SOURCE_FIELDS = {
        "source_id",
        "accession",
        "project_api_url",
        "landing_url",
        "publication_date",
        "license_id",
        "access",
        "laboratory",
        "laboratory_evidence",
        "biological_context",
        "source_defined_unit_type",
        "source_defined_unit_count",
        "sample_mapping_evidence",
        "released_assets",
        "staged_state",
        "target_admission",
    }
    REQUIRED_ASSET_FIELDS = {"role", "format", "selection", "resource_scale"}
    REQUIRED_CONTRACT_FIELDS = {
        "target_status",
        "model_use",
        "required_before_target_freeze",
        "prohibited_shortcuts",
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
            raise RealProteomicsSourcePreflightError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T123 proteomics preflight registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise RealProteomicsSourcePreflightError(
                "proteomics preflight registry fields or schema are invalid"
            )
        if registry.get("audit_id") != self.AUDIT_ID:
            raise RealProteomicsSourcePreflightError("proteomics preflight identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise RealProteomicsSourcePreflightError(
                "proteomics preflight evidence class is unsafe"
            )
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise RealProteomicsSourcePreflightError("proteomics preflight claim level is unsafe")
        _string(registry.get("evaluated_at"), "proteomics preflight evaluated_at")
        cutoff = _string(registry.get("development_cutoff"), "proteomics preflight cutoff")
        if cutoff != "2024-12-31T23:59:59+00:00":
            raise RealProteomicsSourcePreflightError("proteomics preflight cutoff changed")

        policy = _mapping(registry.get("source_policy"), "proteomics preflight policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS:
            raise RealProteomicsSourcePreflightError(
                "proteomics preflight policy fields are invalid"
            )
        for field in ("minimum_sources", "minimum_studies", "minimum_laboratories"):
            if _integer(policy.get(field), f"proteomics preflight policy {field}", minimum=3) != 3:
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight minimum cohort policy changed"
                )
        for field in self.REQUIRED_POLICY_FIELDS - {
            "minimum_sources",
            "minimum_studies",
            "minimum_laboratories",
            "allowed_licenses",
        }:
            if policy.get(field) is not True:
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight safety policy is weakened"
                )
        if (
            set(_list(policy.get("allowed_licenses"), "proteomics preflight licences"))
            != self.ALLOWED_LICENSES
        ):
            raise RealProteomicsSourcePreflightError("proteomics preflight licences are invalid")

        contract = _mapping(registry.get("preprocessing_contract"), "proteomics preflight contract")
        if set(contract) != self.REQUIRED_CONTRACT_FIELDS:
            raise RealProteomicsSourcePreflightError(
                "proteomics preflight contract fields are invalid"
            )
        if (
            contract.get("target_status") != "NOT_FROZEN"
            or contract.get("model_use") != "PROHIBITED"
        ):
            raise RealProteomicsSourcePreflightError("preflight silently promotes a model target")
        for field in ("required_before_target_freeze", "prohibited_shortcuts"):
            values = _list(contract.get(field), f"proteomics preflight {field}", minimum=3)
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise RealProteomicsSourcePreflightError(
                    f"proteomics preflight {field} contains an invalid item"
                )

        sources: list[dict[str, Any]] = []
        identifiers: set[str] = set()
        laboratories: set[str] = set()
        for value in _list(registry.get("sources"), "proteomics preflight sources", minimum=3):
            source = _mapping(value, "proteomics preflight source")
            if set(source) != self.REQUIRED_SOURCE_FIELDS:
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source fields are invalid"
                )
            for field in self.REQUIRED_SOURCE_FIELDS - {
                "source_defined_unit_count",
                "released_assets",
            }:
                _string(source.get(field), f"proteomics preflight source {field}")
            source_id = source["source_id"]
            if source_id in identifiers or source_id not in self.EXPECTED_SOURCE_UNITS:
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source identity is invalid"
                )
            identifiers.add(source_id)
            if source["accession"] != source_id.removeprefix("PRIDE-"):
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight accession is invalid"
                )
            if not source["project_api_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight API locator is invalid"
                )
            if not source["landing_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight landing locator is invalid"
                )
            if source["publication_date"] > "2024-12-31":
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source is post-freeze"
                )
            if source["license_id"] not in self.ALLOWED_LICENSES:
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source licence is unsafe"
                )
            if source["access"] != "ANONYMOUS_PUBLIC":
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source access is restricted"
                )
            if "human" not in source["biological_context"].lower():
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source is not human-biofluid"
                )
            units = _integer(
                source.get("source_defined_unit_count"),
                "proteomics preflight source-defined unit count",
                minimum=1,
            )
            if units != self.EXPECTED_SOURCE_UNITS[source_id]:
                raise RealProteomicsSourcePreflightError(
                    "proteomics preflight source unit count changed"
                )
            assets = _list(source.get("released_assets"), "proteomics preflight assets", minimum=2)
            for asset_value in assets:
                asset = _mapping(asset_value, "proteomics preflight asset")
                if set(asset) != self.REQUIRED_ASSET_FIELDS:
                    raise RealProteomicsSourcePreflightError(
                        "proteomics preflight asset fields are invalid"
                    )
                for field in self.REQUIRED_ASSET_FIELDS:
                    _string(asset.get(field), f"proteomics preflight asset {field}")
            if source["target_admission"] != "NOT_ADMITTED_PENDING_COMMON_PREPROCESSING":
                raise RealProteomicsSourcePreflightError("proteomics source was silently admitted")
            laboratories.add(source["laboratory"])
            sources.append(source)
        if identifiers != set(self.EXPECTED_SOURCE_UNITS) or len(laboratories) != 3:
            raise RealProteomicsSourcePreflightError(
                "proteomics source/laboratory cohort is invalid"
            )
        return registry, sorted(sources, key=lambda row: str(row["source_id"]))

    def run(self, *, strict: bool = False) -> RealProteomicsSourcePreflightSummary:
        """Write an immutable, non-model source-acquisition preflight receipt."""

        if not strict:
            raise RealProteomicsSourcePreflightError(
                "proteomics source preflight requires --strict"
            )
        if self.output_root.exists():
            raise RealProteomicsSourcePreflightError(
                "real proteomics source preflight already executed"
            )
        registry, sources = self._registry()
        unit_count = sum(
            _integer(source["source_defined_unit_count"], "source-defined unit count", minimum=1)
            for source in sources
        )
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "candidate_source_count": len(sources),
            "candidate_study_count": len(sources),
            "candidate_laboratory_count": len({source["laboratory"] for source in sources}),
            "source_defined_unit_count": unit_count,
            "sources": sources,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "status": "READY_FOR_STAGED_RAW_ACQUISITION_NOT_A_MODEL_TARGET",
            "not_a_model_target_reasons": [
                "The releases use author-specific semi-quantitative, label-free and TMT "
                "workflows; their values are not concatenated into one scale.",
                "PXD052701 requires a reusable source-matched material/size covariate map "
                "before a target can be frozen.",
                "Source run, fraction, channel and biological-replication roles have not "
                "yet been resolved into an analysis-unit manifest.",
            ],
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "source_preflight_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": decision["status"],
            "source_preflight_decision_sha256": _sha256(decision_path),
            "candidate_source_count": decision["candidate_source_count"],
            "candidate_study_count": decision["candidate_study_count"],
            "candidate_laboratory_count": decision["candidate_laboratory_count"],
            "source_defined_unit_count": decision["source_defined_unit_count"],
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "source_preflight_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return RealProteomicsSourcePreflightSummary(
            source_count=_integer(receipt["candidate_source_count"], "source count", minimum=3),
            source_defined_unit_count=_integer(
                receipt["source_defined_unit_count"], "source-defined unit count", minimum=1
            ),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable receipt and its no-model boundary."""

        decision_path = self.output_root / "source_preflight_decision.json"
        receipt_path = self.output_root / "source_preflight_receipt.json"
        decision = self._json(decision_path, "proteomics source preflight decision")
        receipt = self._json(receipt_path, "proteomics source preflight receipt")
        required_false = (
            "model_fitted",
            "paired_ablations_run",
            "external_ood_evaluated",
            "negative_controls_run",
            "independent_validation",
            "scientific_submission_ready",
        )
        if (
            receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != "READY_FOR_STAGED_RAW_ACQUISITION_NOT_A_MODEL_TARGET"
            or decision.get("status") != receipt["status"]
            or receipt.get("source_preflight_decision_sha256") != _sha256(decision_path)
            or receipt.get("candidate_source_count") != 3
            or receipt.get("candidate_study_count") != 3
            or receipt.get("candidate_laboratory_count") != 3
            or receipt.get("source_defined_unit_count") != 30
            or receipt.get("target_status") != "NOT_FROZEN"
            or receipt.get("model_use") != "PROHIBITED"
            or decision.get("target_status") != "NOT_FROZEN"
            or decision.get("model_use") != "PROHIBITED"
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise RealProteomicsSourcePreflightError(
                "proteomics source preflight receipt is invalid"
            )
        return receipt
