"""Fail-closed expansion screening for additional T129 CC0 source candidates.

This workflow records first-party project and result-asset evidence for a
separate discovery tranche.  It deliberately does not turn accession labels,
TopPIC file names, or author intensity columns into a predictive endpoint.
"""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CC0TargetDiscoveryError(RuntimeError):
    """Raised when the T129 discovery record would weaken a no-model boundary."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CC0TargetDiscoveryError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise CC0TargetDiscoveryError(f"{label} must contain at least {minimum} items")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CC0TargetDiscoveryError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CC0TargetDiscoveryError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class CC0TargetDiscoverySummary:
    """Compact accounting for an expanded, rejected discovery tranche."""

    candidate_source_count: int
    candidate_laboratory_count: int
    screened_asset_count: int
    receipt_path: Path


class CC0TargetDiscoveryWorkflow:
    """Screen additional CC0 sources without modifying the initial admission receipt."""

    AUDIT_ID = "bioif-r2-cc0-target-discovery-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T129_CC0_TARGET_DISCOVERY_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/cc0_target_discovery/v1.0.0"
    ALLOWED_LICENSES = frozenset({"CC0-1.0"})
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "development_cutoff",
        "evidence_class",
        "allowed_claim_level",
        "source_policy",
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
    REQUIRED_CANDIDATE_FIELDS = {
        "source_id",
        "accession",
        "project_api_url",
        "landing_url",
        "publication_date",
        "license_id",
        "access",
        "laboratory",
        "biological_context",
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
        "content_type",
        "source_label_evidence",
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
            raise CC0TargetDiscoveryError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T129 CC0 target-discovery registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise CC0TargetDiscoveryError("CC0 target-discovery registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise CC0TargetDiscoveryError("CC0 target-discovery registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise CC0TargetDiscoveryError("CC0 target-discovery evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise CC0TargetDiscoveryError("CC0 target-discovery claim level is unsafe")
        _string(registry.get("evaluated_at"), "CC0 target-discovery evaluated_at")
        if _string(registry.get("development_cutoff"), "CC0 target-discovery cutoff") != (
            "2024-12-31T23:59:59+00:00"
        ):
            raise CC0TargetDiscoveryError("CC0 target-discovery cutoff changed")

        policy = _mapping(registry.get("source_policy"), "CC0 target-discovery policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS:
            raise CC0TargetDiscoveryError("CC0 target-discovery policy fields are invalid")
        if set(_list(policy.get("allowed_licenses"), "CC0 target-discovery licences")) != (
            self.ALLOWED_LICENSES
        ):
            raise CC0TargetDiscoveryError("CC0 target-discovery licences are invalid")
        for field in self.REQUIRED_POLICY_FIELDS - {"allowed_licenses"}:
            if policy.get(field) is not True:
                raise CC0TargetDiscoveryError("CC0 target-discovery safety policy is weakened")

        candidates: list[dict[str, Any]] = []
        source_ids: set[str] = set()
        laboratories: set[str] = set()
        asset_count = 0
        for value in _list(
            registry.get("candidates"), "CC0 target-discovery candidates", minimum=2
        ):
            candidate = _mapping(value, "CC0 target-discovery candidate")
            if set(candidate) != self.REQUIRED_CANDIDATE_FIELDS:
                raise CC0TargetDiscoveryError("CC0 target-discovery candidate fields are invalid")
            for field in self.REQUIRED_CANDIDATE_FIELDS - {
                "screened_assets",
                "non_admission_reasons",
            }:
                _string(candidate.get(field), f"CC0 target-discovery candidate {field}")
            source_id = candidate["source_id"]
            if source_id in source_ids or source_id != f"PRIDE-{candidate['accession']}":
                raise CC0TargetDiscoveryError("CC0 target-discovery source identity is invalid")
            source_ids.add(source_id)
            if not candidate["project_api_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise CC0TargetDiscoveryError("CC0 target-discovery API locator is invalid")
            if not candidate["landing_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise CC0TargetDiscoveryError("CC0 target-discovery landing locator is invalid")
            if candidate["publication_date"] > "2024-12-31":
                raise CC0TargetDiscoveryError("CC0 target-discovery source is post-freeze")
            if candidate["license_id"] not in self.ALLOWED_LICENSES:
                raise CC0TargetDiscoveryError("CC0 target-discovery licence is unsafe")
            if candidate["access"] != "ANONYMOUS_PUBLIC":
                raise CC0TargetDiscoveryError("CC0 target-discovery access is restricted")
            if "human" not in candidate["biological_context"].lower():
                raise CC0TargetDiscoveryError("CC0 target-discovery source is not human-biofluid")
            laboratories.add(candidate["laboratory"])

            names: set[str] = set()
            assets = _list(
                candidate.get("screened_assets"), "CC0 target-discovery screened assets", minimum=1
            )
            for asset_value in assets:
                asset = _mapping(asset_value, "CC0 target-discovery asset")
                if set(asset) != self.REQUIRED_ASSET_FIELDS:
                    raise CC0TargetDiscoveryError("CC0 target-discovery asset fields are invalid")
                for field in self.REQUIRED_ASSET_FIELDS - {"observed_local_bytes"}:
                    _string(asset.get(field), f"CC0 target-discovery asset {field}")
                if asset["file_name"] in names:
                    raise CC0TargetDiscoveryError("CC0 target-discovery asset identity is invalid")
                names.add(asset["file_name"])
                _integer(
                    asset.get("observed_local_bytes"),
                    "CC0 target-discovery observed local bytes",
                    minimum=1,
                )
                digest = asset["local_sha256"].lower()
                if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                    raise CC0TargetDiscoveryError("CC0 target-discovery asset SHA-256 is invalid")
                if not asset["download_url"].startswith("https://ftp.pride.ebi.ac.uk/"):
                    raise CC0TargetDiscoveryError(
                        "CC0 target-discovery asset needs an official HTTPS URL"
                    )
            asset_count += len(assets)

            expected_statuses = {
                "source_label_status": "SOURCE_LABELS_NOT_A_COVARIATE_MAP",
                "numeric_covariate_map_status": "MISSING_SOURCE_MATCHED_UNIT_LEVEL_MAP",
                "common_endpoint_status": "NOT_A_COMMON_CROSS_STUDY_ENDPOINT",
                "analysis_unit_status": "BIOLOGICAL_UNIT_NOT_FROZEN",
            }
            if any(candidate[field] != status for field, status in expected_statuses.items()):
                raise CC0TargetDiscoveryError("CC0 target-discovery silently promotes a target")
            if candidate["admission"] != "NOT_ADMITTED" or candidate["model_use"] != "PROHIBITED":
                raise CC0TargetDiscoveryError("CC0 target-discovery silently promotes a target")
            reasons = _list(
                candidate.get("non_admission_reasons"),
                "CC0 target-discovery non-admission reasons",
                minimum=2,
            )
            if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
                raise CC0TargetDiscoveryError("CC0 target-discovery reason is invalid")
            candidates.append(candidate)
        if len(source_ids) != 2 or len(laboratories) != 1 or asset_count != 7:
            raise CC0TargetDiscoveryError("CC0 target-discovery candidate cohort is invalid")
        return registry, sorted(candidates, key=lambda row: str(row["source_id"]))

    def run(self, *, strict: bool = False) -> CC0TargetDiscoverySummary:
        """Write an immutable no-target decision for the expansion tranche."""

        if not strict:
            raise CC0TargetDiscoveryError("CC0 target-discovery audit requires --strict")
        if self.output_root.exists():
            raise CC0TargetDiscoveryError("CC0 target-discovery audit already executed")
        registry, candidates = self._registry()
        laboratory_count = len({candidate["laboratory"] for candidate in candidates})
        asset_count = sum(len(candidate["screened_assets"]) for candidate in candidates)
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "candidate_source_count": len(candidates),
            "candidate_laboratory_count": laboratory_count,
            "screened_asset_count": asset_count,
            "candidates": candidates,
            "status": "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES",
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "admissible_target_count": 0,
            "blocked_reasons": [
                "PXD053359 result files expose S2/S4 acquisition labels, but no official "
                "source asset maps those labels to numeric material or size covariates for "
                "each analysis unit.",
                "PXD050779 records three parallel protein-corona samples from one commercial "
                "healthy-human-plasma source, but no screened result asset maps them to a "
                "reusable numeric material or size covariate.",
                "Both sources originate from one laboratory and use heterogeneous top-down "
                "author outputs; they do not establish a two-laboratory common predictive "
                "endpoint.",
            ],
            "next_required_evidence": [
                "Obtain source assets that map every biological analysis unit to numeric "
                "material or size covariates without inferring semantics from file or sample "
                "labels.",
                "Freeze one common endpoint and study-held-out design across at least two "
                "independent laboratories before creating T121 Amendment v1.0.1.",
            ],
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "target_discovery_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": decision["status"],
            "target_discovery_decision_sha256": _sha256(decision_path),
            "candidate_source_count": decision["candidate_source_count"],
            "candidate_laboratory_count": decision["candidate_laboratory_count"],
            "screened_asset_count": decision["screened_asset_count"],
            "admissible_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "target_discovery_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return CC0TargetDiscoverySummary(
            candidate_source_count=_integer(
                receipt["candidate_source_count"], "candidate source count", minimum=2
            ),
            candidate_laboratory_count=_integer(
                receipt["candidate_laboratory_count"], "candidate laboratory count", minimum=1
            ),
            screened_asset_count=_integer(
                receipt["screened_asset_count"], "screened asset count", minimum=1
            ),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable expansion receipt and its no-model boundary."""

        decision_path = self.output_root / "target_discovery_decision.json"
        receipt_path = self.output_root / "target_discovery_receipt.json"
        decision = self._json(decision_path, "CC0 target-discovery decision")
        receipt = self._json(receipt_path, "CC0 target-discovery receipt")
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
            or receipt.get("status") != "BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES"
            or decision.get("status") != receipt["status"]
            or receipt.get("target_discovery_decision_sha256") != _sha256(decision_path)
            or receipt.get("candidate_source_count") != 2
            or receipt.get("candidate_laboratory_count") != 1
            or receipt.get("screened_asset_count") != 7
            or receipt.get("admissible_target_count") != 0
            or receipt.get("target_status") != "NOT_FROZEN"
            or receipt.get("model_use") != "PROHIBITED"
            or decision.get("admissible_target_count") != 0
            or decision.get("target_status") != "NOT_FROZEN"
            or decision.get("model_use") != "PROHIBITED"
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise CC0TargetDiscoveryError("CC0 target-discovery receipt is invalid")
        return receipt
