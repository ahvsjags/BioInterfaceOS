"""Fail-closed audit for licence-bound protein-corona source mappings.

The audit makes a deliberately narrow distinction: public raw result files do
not automatically make a paper-derived material map public.  It records which
route can be reconsidered, while preventing an analysis-only map or implicit
file-name semantics from silently entering the CC0 target cohort.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LicenseBoundSourceMapError(RuntimeError):
    """Raised when a licence/source-map decision weakens the target boundary."""


@dataclass(frozen=True)
class LicenseBoundSourceMapSummary:
    """Compact accounting for the strict non-admission decision."""

    route_count: int
    independent_laboratory_count: int
    analysis_only_complete_map_count: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LicenseBoundSourceMapError(f"{label} must be an object")
    return dict(value)


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise LicenseBoundSourceMapError(f"{label} must contain at least {minimum} items")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LicenseBoundSourceMapError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise LicenseBoundSourceMapError(f"{label} must be an integer >= {minimum}")
    return value


class LicenseBoundSourceMapWorkflow:
    """Audit reuse, unit coverage and target eligibility without model fitting."""

    AUDIT_ID = "bioif-r2-license-bound-source-maps-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T130_LICENSE_BOUND_SOURCE_MAP_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/license_bound_source_maps/v1.0.0"
    REQUIRED_FALSE = (
        "target_frozen",
        "model_fitted",
        "paired_ablations_run",
        "external_ood_evaluated",
        "negative_controls_run",
        "independent_validation",
        "scientific_submission_ready",
    )
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "development_cutoff",
        "evidence_class",
        "allowed_claim_level",
        "source_policy",
        "routes",
    }
    REQUIRED_POLICY_FIELDS = {
        "cc0_cohort_license",
        "public_redistributable_mapping_licenses",
        "analysis_only_mapping_licenses",
        "require_complete_source_unit_coverage",
        "require_numeric_material_or_size_covariate",
        "require_shared_cross_study_endpoint",
        "require_two_independent_laboratories",
        "prohibit_implicit_file_label_features",
        "prohibit_model_use_before_t121_amendment",
    }
    REQUIRED_ROUTE_FIELDS = {
        "route_id",
        "source_id",
        "stable_identifier",
        "laboratory",
        "primary_data_release",
        "mapping_evidence",
        "unit_coverage",
        "numeric_material_or_size_covariate_status",
        "endpoint_status",
        "admission",
        "model_use",
        "non_admission_reasons",
    }
    REQUIRED_RELEASE_FIELDS = {"locator", "license_id", "access", "source_unit_count"}
    REQUIRED_MAPPING_FIELDS = {
        "locator",
        "source_type",
        "license_id",
        "reuse_class",
        "verification_status",
        "mapping_claim",
        "public_registry_value_policy",
    }
    REQUIRED_COVERAGE_FIELDS = {
        "source_unit_identifiers",
        "source_unit_count",
        "mapped_unit_count",
    }
    PUBLIC_LICENSES = frozenset({"CC0-1.0", "CC-BY-3.0", "CC-BY-4.0"})
    ANALYSIS_ONLY_LICENSES = frozenset({"CC-BY-NC-3.0", "CC-BY-NC-4.0"})
    EXPECTED_ROUTE_IDS = {
        "PXD052701_RSC_D4NA00345D",
        "PXD017776_PRIDE_ONLY",
        "C9NR08186K_RSC_SUPPLEMENTS",
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
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LicenseBoundSourceMapError(f"cannot parse {label}") from exc

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _require(condition: bool, label: str) -> None:
        if not condition:
            raise LicenseBoundSourceMapError(label)

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T130 licence-bound source-map registry")
        self._require(
            set(registry) == self.REQUIRED_REGISTRY_FIELDS and registry.get("schema_version") == 1,
            "T130 registry fields are invalid",
        )
        self._require(registry.get("audit_id") == self.AUDIT_ID, "T130 registry identity is invalid")
        self._require(
            registry.get("evidence_class") == "DEVELOPMENT_OBSERVATION"
            and registry.get("allowed_claim_level") == "EXPLORATORY",
            "T130 evidence semantics are unsafe",
        )
        self._require(
            _string(registry.get("development_cutoff"), "T130 cutoff") == "2024-12-31T23:59:59+00:00",
            "T130 cutoff changed",
        )
        _string(registry.get("evaluated_at"), "T130 evaluated_at")

        policy = _mapping(registry.get("source_policy"), "T130 source policy")
        self._require(set(policy) == self.REQUIRED_POLICY_FIELDS, "T130 policy fields are invalid")
        self._require(policy.get("cc0_cohort_license") == "CC0-1.0", "T130 CC0 cohort changed")
        self._require(
            set(_list(policy.get("public_redistributable_mapping_licenses"), "public licences"))
            == self.PUBLIC_LICENSES,
            "T130 public licence policy is invalid",
        )
        self._require(
            set(_list(policy.get("analysis_only_mapping_licenses"), "analysis-only licences"))
            == self.ANALYSIS_ONLY_LICENSES,
            "T130 analysis-only licence policy is invalid",
        )
        for field in self.REQUIRED_POLICY_FIELDS - {
            "cc0_cohort_license",
            "public_redistributable_mapping_licenses",
            "analysis_only_mapping_licenses",
        }:
            self._require(policy.get(field) is True, "T130 policy boundary is weakened")

        routes: list[dict[str, Any]] = []
        route_ids: set[str] = set()
        laboratories: set[str] = set()
        for value in _list(registry.get("routes"), "T130 routes", minimum=3):
            route = _mapping(value, "T130 route")
            self._require(set(route) == self.REQUIRED_ROUTE_FIELDS, "T130 route fields are invalid")
            for field in self.REQUIRED_ROUTE_FIELDS - {
                "primary_data_release",
                "mapping_evidence",
                "unit_coverage",
                "non_admission_reasons",
            }:
                _string(route.get(field), f"T130 route {field}")
            route_id = route["route_id"]
            self._require(route_id not in route_ids, "T130 route identity is duplicated")
            route_ids.add(route_id)
            laboratories.add(route["laboratory"])

            release = _mapping(route.get("primary_data_release"), "T130 primary release")
            self._require(
                set(release) == self.REQUIRED_RELEASE_FIELDS,
                "T130 primary release fields are invalid",
            )
            for field in self.REQUIRED_RELEASE_FIELDS - {"source_unit_count"}:
                _string(release.get(field), f"T130 primary release {field}")
            _integer(release.get("source_unit_count"), "T130 primary source units")
            self._require(
                release["locator"].startswith("https://") and release["license_id"] in self.PUBLIC_LICENSES,
                "T130 primary release is not a public reusable source",
            )

            mapping = _mapping(route.get("mapping_evidence"), "T130 mapping evidence")
            self._require(
                set(mapping) == self.REQUIRED_MAPPING_FIELDS,
                "T130 mapping evidence fields are invalid",
            )
            for field in self.REQUIRED_MAPPING_FIELDS:
                _string(mapping.get(field), f"T130 mapping evidence {field}")
            self._require(mapping["locator"].startswith("https://"), "T130 mapping locator is invalid")
            reuse_class = mapping["reuse_class"]
            mapping_license = mapping["license_id"]
            self._require(
                (reuse_class == "ANALYSIS_ONLY_NONPUBLIC_MAPPING" and mapping_license in self.ANALYSIS_ONLY_LICENSES)
                or (
                    reuse_class in {"PUBLIC_MAPPING_INCOMPLETE", "PUBLIC_MAPPING_UNVERIFIED"}
                    and mapping_license in self.PUBLIC_LICENSES
                ),
                "T130 mapping licence classification is invalid",
            )

            coverage = _mapping(route.get("unit_coverage"), "T130 unit coverage")
            self._require(
                set(coverage) == self.REQUIRED_COVERAGE_FIELDS,
                "T130 unit coverage fields are invalid",
            )
            identifiers = _list(coverage.get("source_unit_identifiers"), "T130 source units")
            self._require(
                all(isinstance(item, str) and item.strip() for item in identifiers)
                and len(set(identifiers)) == len(identifiers),
                "T130 source unit identities are invalid",
            )
            source_unit_count = _integer(coverage.get("source_unit_count"), "T130 covered source units")
            mapped_unit_count = _integer(coverage.get("mapped_unit_count"), "T130 mapped source units")
            self._require(
                source_unit_count == len(identifiers)
                and source_unit_count == release["source_unit_count"]
                and mapped_unit_count <= source_unit_count,
                "T130 unit coverage accounting is invalid",
            )

            reasons = _list(route.get("non_admission_reasons"), "T130 non-admission reasons", minimum=2)
            self._require(
                all(isinstance(reason, str) and reason.strip() for reason in reasons),
                "T130 non-admission reason is invalid",
            )
            self._require(
                route["admission"] == "NOT_ADMITTED" and route["model_use"] == "PROHIBITED",
                "T130 route silently promotes a target",
            )
            routes.append(route)

        self._require(route_ids == self.EXPECTED_ROUTE_IDS, "T130 route cohort is invalid")
        self._require(len(laboratories) == 3, "T130 laboratory accounting is invalid")
        by_id = {route["route_id"]: route for route in routes}
        pxd052 = by_id["PXD052701_RSC_D4NA00345D"]
        self._require(
            pxd052["unit_coverage"]["mapped_unit_count"] == 10
            and pxd052["numeric_material_or_size_covariate_status"]
            == "EXPLICIT_NOMINAL_EXTRUSION_FILTER_SIZE_ANALYSIS_ONLY"
            and pxd052["endpoint_status"] == "AUTHOR_SPECIFIC_NSAF_OR_SPECTRAL_COUNT_NOT_SHARED_CROSS_STUDY",
            "T130 PXD052701 boundary is invalid",
        )
        pxd017 = by_id["PXD017776_PRIDE_ONLY"]
        self._require(
            pxd017["unit_coverage"]["mapped_unit_count"] == 0
            and pxd017["numeric_material_or_size_covariate_status"] == "MISSING_NUMERIC_SOURCE_MATCHED_MAP",
            "T130 PXD017776 boundary is invalid",
        )
        c9 = by_id["C9NR08186K_RSC_SUPPLEMENTS"]
        self._require(
            c9["unit_coverage"]["source_unit_count"] == 0
            and c9["numeric_material_or_size_covariate_status"] == "UNVERIFIED_PENDING_WORKBOOK_INSPECTION",
            "T130 C9NR08186K boundary is invalid",
        )
        return registry, sorted(routes, key=lambda route: str(route["route_id"]))

    def run(self, *, strict: bool = False) -> LicenseBoundSourceMapSummary:
        """Write the immutable strict licence/source-map non-admission decision."""

        if not strict:
            raise LicenseBoundSourceMapError("licence-bound source-map audit requires --strict")
        if self.output_root.exists():
            raise LicenseBoundSourceMapError("licence-bound source-map audit already executed")
        registry, routes = self._registry()
        analysis_only_complete_map_count = sum(
            route["mapping_evidence"]["reuse_class"] == "ANALYSIS_ONLY_NONPUBLIC_MAPPING"
            and route["unit_coverage"]["source_unit_count"] == route["unit_coverage"]["mapped_unit_count"]
            and route["unit_coverage"]["mapped_unit_count"] > 0
            for route in routes
        )
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "status": "BLOCKED_NO_PUBLIC_CROSS_STUDY_NUMERIC_MATERIAL_TARGET",
            "cc0_cohort_status": "UNCHANGED_NO_ADDITIONAL_ADMISSIONS",
            "route_count": len(routes),
            "independent_laboratory_count": len({route["laboratory"] for route in routes}),
            "public_redistributable_complete_map_count": 0,
            "analysis_only_complete_map_count": analysis_only_complete_map_count,
            "public_incomplete_or_unverified_route_count": sum(
                route["mapping_evidence"]["reuse_class"] in {"PUBLIC_MAPPING_INCOMPLETE", "PUBLIC_MAPPING_UNVERIFIED"}
                for route in routes
            ),
            "shared_cross_study_endpoint_count": 0,
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "routes": routes,
            "blocked_reasons": [
                "PXD052701 has a complete nominal-size map only through an analysis-only CC BY-NC source; no mapping values are copied into public artefacts or the CC0 cohort.",  # noqa: E501
                "PXD017776 has public CC0 author results but no released numeric file-to-condition map, so file-name tokens remain prohibited identity features.",  # noqa: E501
                "C9NR08186K is a distinct public CC BY route, but its XLSX schema and source-unit coverage are unverified and raw proteomics availability is restricted to reasonable request.",  # noqa: E501
                "No two independent laboratories have a frozen, identically processed protein-corona endpoint with complete public reusable numeric material or size covariates.",  # noqa: E501
            ],
            "next_required_evidence": [
                "Obtain a public-redistributable source map that closes each PXD017776 unit to source-defined numeric covariates, without relabelling file names.",  # noqa: E501
                "After normal publisher verification, checksum and inspect C9NR08186K's listed XLSX supplements before recording any unit or endpoint fields.",  # noqa: E501
                "Before any model run, freeze a T121 amendment with a shared preprocessing endpoint, source-unit manifest, study-held-out split and permitted features across at least two laboratories.",  # noqa: E501
            ],
            **{field: False for field in self.REQUIRED_FALSE},
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "license_bound_source_map_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": decision["status"],
            "license_bound_source_map_decision_sha256": _sha256(decision_path),
            "route_count": decision["route_count"],
            "independent_laboratory_count": decision["independent_laboratory_count"],
            "public_redistributable_complete_map_count": 0,
            "analysis_only_complete_map_count": analysis_only_complete_map_count,
            "shared_cross_study_endpoint_count": 0,
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            **{field: False for field in self.REQUIRED_FALSE},
        }
        receipt_path = self.output_root / "license_bound_source_map_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return LicenseBoundSourceMapSummary(
            route_count=len(routes),
            independent_laboratory_count=len({route["laboratory"] for route in routes}),
            analysis_only_complete_map_count=analysis_only_complete_map_count,
            receipt_path=receipt_path,
        )

    def verify(self) -> LicenseBoundSourceMapSummary:
        """Verify the decision, receipt and registry binding after execution."""

        decision_path = self.output_root / "license_bound_source_map_decision.json"
        receipt_path = self.output_root / "license_bound_source_map_receipt.json"
        decision = self._json(decision_path, "T130 licence-bound source-map decision")
        receipt = self._json(receipt_path, "T130 licence-bound source-map receipt")
        registry, routes = self._registry()
        analysis_only_complete_map_count = sum(
            route["mapping_evidence"]["reuse_class"] == "ANALYSIS_ONLY_NONPUBLIC_MAPPING"
            and route["unit_coverage"]["source_unit_count"] == route["unit_coverage"]["mapped_unit_count"]
            and route["unit_coverage"]["mapped_unit_count"] > 0
            for route in routes
        )
        required_counts = {
            "route_count": 3,
            "independent_laboratory_count": 3,
            "public_redistributable_complete_map_count": 0,
            "analysis_only_complete_map_count": analysis_only_complete_map_count,
            "shared_cross_study_endpoint_count": 0,
            "admissible_target_count": 0,
        }
        self._require(
            decision.get("audit_id") == self.AUDIT_ID
            and receipt.get("audit_id") == self.AUDIT_ID
            and decision.get("status") == "BLOCKED_NO_PUBLIC_CROSS_STUDY_NUMERIC_MATERIAL_TARGET"
            and receipt.get("status") == decision.get("status")
            and decision.get("cc0_cohort_status") == "UNCHANGED_NO_ADDITIONAL_ADMISSIONS"
            and receipt.get("license_bound_source_map_decision_sha256") == _sha256(decision_path)
            and decision.get("registry_sha256") == _sha256(self.registry_path)
            and decision.get("routes") == routes
            and decision.get("target_status") == "NOT_FROZEN"
            and receipt.get("target_status") == "NOT_FROZEN"
            and decision.get("model_use") == "PROHIBITED"
            and receipt.get("model_use") == "PROHIBITED"
            and all(decision.get(key) == value and receipt.get(key) == value for key, value in required_counts.items())
            and all(decision.get(field) is False and receipt.get(field) is False for field in self.REQUIRED_FALSE),
            "T130 licence-bound source-map receipt is invalid",
        )
        return LicenseBoundSourceMapSummary(
            route_count=3,
            independent_laboratory_count=3,
            analysis_only_complete_map_count=analysis_only_complete_map_count,
            receipt_path=receipt_path,
        )
