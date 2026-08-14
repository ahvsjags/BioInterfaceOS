"""Immutable audit of newly screened public T123 source candidates.

The workflow records why individually promising public data records were not
silently promoted to a shared biological prediction target. It has no network
client and never retrieves reserved lockbox content during execution.
"""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RealModelSourceDiscoveryError(RuntimeError):
    """Raised when the T123 public-source discovery audit is unsafe."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealModelSourceDiscoveryError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise RealModelSourceDiscoveryError(f"{label} must be a list with at least {minimum} items")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealModelSourceDiscoveryError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RealModelSourceDiscoveryError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class RealModelSourceDiscoverySummary:
    """Compact accounting for the public source-discovery decision."""

    candidate_count: int
    rejected_candidate_count: int
    reserved_lockbox_candidate_count: int
    receipt_path: Path


class RealModelSourceDiscoveryWorkflow:
    """Fail closed when screened source records do not define a valid T123 target."""

    AUDIT_ID = "bioif-r2-real-model-source-discovery-audit-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T123_PUBLIC_SOURCE_DISCOVERY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/real_model_source_discovery/v1.0.0"
    ALLOWED_LICENSES = frozenset({"CC-BY-4.0", "CC0-1.0", "PDDL-1.0"})
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "source_policy",
        "candidates",
    }
    REQUIRED_POLICY_FIELDS = {
        "minimum_sources",
        "minimum_studies",
        "minimum_laboratories",
        "require_same_measurement_definition",
        "require_same_endpoint_unit",
        "require_matched_biological_condition",
        "require_raw_source_defined_independent_units",
        "require_anonymous_public_access",
        "allowed_licenses",
    }
    REQUIRED_CANDIDATE_FIELDS = {
        "candidate_id",
        "landing_url",
        "doi",
        "published_at",
        "license_id",
        "access",
        "institution_evidence",
        "measurement_definition",
        "endpoint_unit",
        "asset_evidence",
        "biological_condition_evidence",
        "independent_unit_evidence",
        "decision",
        "rejection_reasons",
    }
    REJECTED = "REJECTED_NOT_ADMISSIBLE"
    RESERVED = "RESERVED_LOCKBOX_NOT_USED"

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
            raise RealModelSourceDiscoveryError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T123 public source-discovery registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise RealModelSourceDiscoveryError("source-discovery registry fields or schema are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise RealModelSourceDiscoveryError("source-discovery registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise RealModelSourceDiscoveryError("source-discovery evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise RealModelSourceDiscoveryError("source-discovery claim level is unsafe")
        _string(registry.get("evaluated_at"), "source-discovery evaluated_at")
        policy = _mapping(registry.get("source_policy"), "source-discovery policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS:
            raise RealModelSourceDiscoveryError("source-discovery policy fields are invalid")
        for field in ("minimum_sources", "minimum_studies", "minimum_laboratories"):
            if _integer(policy.get(field), f"source-discovery policy {field}", minimum=3) != 3:
                raise RealModelSourceDiscoveryError("source-discovery minimum cohort policy changed")
        for field in self.REQUIRED_POLICY_FIELDS - {
            "minimum_sources",
            "minimum_studies",
            "minimum_laboratories",
            "allowed_licenses",
        }:
            if policy.get(field) is not True:
                raise RealModelSourceDiscoveryError("source-discovery safety policy is weakened")
        policy_licenses = _list(policy.get("allowed_licenses"), "source-discovery allowed licences")
        if set(policy_licenses) != self.ALLOWED_LICENSES:
            raise RealModelSourceDiscoveryError("source-discovery allowed licences are invalid")

        candidates: list[dict[str, Any]] = []
        identifiers: set[str] = set()
        for value in _list(registry.get("candidates"), "source-discovery candidates", minimum=3):
            candidate = _mapping(value, "source-discovery candidate")
            if set(candidate) != self.REQUIRED_CANDIDATE_FIELDS:
                raise RealModelSourceDiscoveryError("source-discovery candidate fields are invalid")
            for field in self.REQUIRED_CANDIDATE_FIELDS - {"rejection_reasons"}:
                _string(candidate.get(field), f"source-discovery candidate {field}")
            candidate_id = candidate["candidate_id"]
            if candidate_id in identifiers:
                raise RealModelSourceDiscoveryError("source-discovery candidate ID is duplicated")
            identifiers.add(candidate_id)
            has_valid_source_identity = candidate["landing_url"].startswith("https://") and candidate["doi"].startswith(
                "10."
            )
            if not has_valid_source_identity:
                raise RealModelSourceDiscoveryError("source-discovery candidate source identity is invalid")
            if candidate["license_id"] not in self.ALLOWED_LICENSES:
                raise RealModelSourceDiscoveryError("source-discovery candidate licence is unsafe")
            if candidate["access"] != "ANONYMOUS_PUBLIC":
                raise RealModelSourceDiscoveryError("source-discovery candidate access is restricted")
            reasons = _list(
                candidate.get("rejection_reasons"),
                "source-discovery candidate rejection reasons",
                minimum=1,
            )
            if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
                raise RealModelSourceDiscoveryError("source-discovery rejection reason is invalid")
            if candidate["decision"] not in {self.REJECTED, self.RESERVED}:
                raise RealModelSourceDiscoveryError("source-discovery candidate was silently admitted")
            candidates.append(candidate)
        if len(candidates) != 3:
            raise RealModelSourceDiscoveryError("source-discovery audit requires exactly three screened records")
        if sum(candidate["decision"] == self.RESERVED for candidate in candidates) != 1:
            raise RealModelSourceDiscoveryError("source-discovery must preserve one reserved lockbox record")
        return registry, sorted(candidates, key=lambda row: str(row["candidate_id"]))

    def run(self, *, strict: bool = False) -> RealModelSourceDiscoverySummary:
        """Write the immutable blocked T123 discovery decision in strict mode."""

        if not strict:
            raise RealModelSourceDiscoveryError("T123 source-discovery audit requires --strict")
        if self.output_root.exists():
            raise RealModelSourceDiscoveryError("real-model source-discovery audit already executed")
        registry, candidates = self._registry()
        rejected = sum(candidate["decision"] == self.REJECTED for candidate in candidates)
        reserved = sum(candidate["decision"] == self.RESERVED for candidate in candidates)
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "candidate_count": len(candidates),
            "rejected_candidate_count": rejected,
            "reserved_lockbox_candidate_count": reserved,
            "admitted_candidate_count": 0,
            "candidates": candidates,
            "status": "BLOCKED_NO_ADMISSIBLE_T123_TARGET_FOUND",
            "blocked_reasons": [
                "No screened record supplies a source-defined row-level DLS target with a "
                "matched biological-condition protocol.",
                "A post-freeze record stays out of development evidence and is not treated as "
                "an inferred external validation result.",
                "The source policy still requires three independently generated studies and "
                "laboratories with the same declared measurement definition and unit.",
            ],
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "source_discovery_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": decision["status"],
            "source_discovery_decision_sha256": _sha256(decision_path),
            "candidate_count": decision["candidate_count"],
            "rejected_candidate_count": decision["rejected_candidate_count"],
            "reserved_lockbox_candidate_count": decision["reserved_lockbox_candidate_count"],
            "admitted_candidate_count": 0,
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "source_discovery_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return RealModelSourceDiscoverySummary(
            candidate_count=_integer(receipt["candidate_count"], "candidate count", minimum=3),
            rejected_candidate_count=_integer(
                receipt["rejected_candidate_count"], "rejected candidate count", minimum=1
            ),
            reserved_lockbox_candidate_count=_integer(
                receipt["reserved_lockbox_candidate_count"],
                "reserved lockbox candidate count",
                minimum=1,
            ),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable discovery receipt and its no-results boundary."""

        decision_path = self.output_root / "source_discovery_decision.json"
        receipt_path = self.output_root / "source_discovery_receipt.json"
        decision = self._json(decision_path, "source-discovery decision")
        receipt = self._json(receipt_path, "source-discovery receipt")
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
            or receipt.get("status") != "BLOCKED_NO_ADMISSIBLE_T123_TARGET_FOUND"
            or decision.get("status") != receipt["status"]
            or receipt.get("source_discovery_decision_sha256") != _sha256(decision_path)
            or receipt.get("candidate_count") != 3
            or receipt.get("rejected_candidate_count") != 2
            or receipt.get("reserved_lockbox_candidate_count") != 1
            or receipt.get("admitted_candidate_count") != 0
            or decision.get("admitted_candidate_count") != 0
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise RealModelSourceDiscoveryError("source-discovery receipt is invalid")
        return receipt
