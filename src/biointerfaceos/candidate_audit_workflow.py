"""Fixture-backed candidate audit packets and retrospective validation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


class CandidateAuditError(RuntimeError):
    """Raised when the T098 candidate-audit contract is invalid."""


@dataclass(frozen=True)
class CandidateAuditSummary:
    """Summary of one deterministic candidate audit run."""

    candidates: int
    unique_candidates: int
    duplicate_candidates: int
    supported_candidates: int
    rejected_candidates: int
    temporal_matches: int
    unresolved_matches: int
    abstentions: int
    selected_wording: str
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateAuditError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateAuditError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CandidateAuditError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CandidateAuditError(f"{label} must be finite")
    return result


class CandidateAuditWorkflow:
    """Create provenance-complete cards and a non-tuned retrospective audit."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/design/candidate_audit_fixture.json")
        self.output_root = output_root or self.root / "reports/design/candidates"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "candidate-audit fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CandidateAuditError(f"cannot load candidate-audit fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "design_candidate_audit":
            raise CandidateAuditError("candidate-audit fixture schema or mode is invalid")
        for key in ("inputs", "preregistration", "candidates", "retrospective_matches"):
            if key not in data:
                raise CandidateAuditError(f"candidate-audit fixture is missing {key}")
        if not all(isinstance(data[key], list) for key in ("inputs", "candidates", "retrospective_matches")):
            raise CandidateAuditError("candidate-audit fixture list fields are invalid")
        preregistration = _mapping(data["preregistration"], "candidate-audit preregistration")
        if preregistration.get("schema_version") != 1:
            raise CandidateAuditError("candidate-audit preregistration schema is invalid")
        if preregistration.get("temporal_match_policy") != "descriptive_only":
            raise CandidateAuditError("temporal matching must be descriptive only")
        if preregistration.get("target_values_exposed") is not False:
            raise CandidateAuditError("candidate audit cannot expose target values")
        if preregistration.get("allowed_wording") != [
            "exploratory_supported",
            "retrospective_descriptive",
        ]:
            raise CandidateAuditError("allowed wording policy is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected: dict[str, tuple[Path, str]] = {
            "T096 constrained design receipt": (
                self.root / "reports/design/baseline/design_baseline_receipt.json",
                "e6fc606f63b278246e4bb5c150c139fd5b389d6a15016d7f61d5365a9a551bee",
            ),
            "T097 target-corona generative receipt": (
                self.root / "reports/design/generative/target_corona_generative_receipt.json",
                "e920aa0b442d0d91ab2b94053af65065b274fd0e2a8f04b3eaf208b9f6072530",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "candidate-audit input")
            label = _string(row.get("label"), "candidate-audit input label")
            if label not in expected:
                raise CandidateAuditError(f"unexpected candidate-audit input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "candidate-audit input path")).resolve(strict=True)
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise CandidateAuditError(f"candidate-audit input path/checksum differs: {label}")
            raw = path.read_bytes()
            payload = _mapping(json.loads(raw), f"{label} payload")
            if _sha256(raw) != checksum or payload.get("status") != "VALID":
                raise CandidateAuditError(f"{label} is not a valid frozen input")
            if label.startswith("T097") and payload.get("selected_method") != ("conditional_generator"):
                raise CandidateAuditError("T097 selected method is not the frozen generator")
            seen.add(label)
        if seen != set(expected):
            raise CandidateAuditError("candidate-audit inputs do not match T096/T097 contract")

    @staticmethod
    def _preregistration(fixture: Mapping[str, Any]) -> dict[str, Any]:
        preregistration = _mapping(fixture["preregistration"], "candidate-audit preregistration")
        for key in (
            "ad_threshold",
            "uncertainty_threshold",
            "neighbor_distance_threshold",
            "stability_threshold",
            "perturbation_budget",
        ):
            _number(preregistration.get(key), f"candidate-audit {key}")
        if preregistration["perturbation_budget"] != 4:
            raise CandidateAuditError("perturbation budget is not frozen")
        try:
            date.fromisoformat(_string(preregistration.get("design_freeze_date"), "freeze date"))
        except ValueError as exc:
            raise CandidateAuditError("design freeze date is invalid") from exc
        return preregistration

    @classmethod
    def _candidates(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        required = {
            "candidate_id",
            "source_method",
            "fingerprint",
            "component_set",
            "geometry",
            "conditioning",
            "ad_distance",
            "uncertainty",
            "nearest_evidence_distance",
            "perturbation_scores",
            "unsafe",
            "evidence_links",
            "evidence_date",
            "temporal_match",
        }
        records: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        fingerprints: dict[str, str] = {}
        budget = int(preregistration["perturbation_budget"])
        for value in fixture["candidates"]:
            source = _mapping(value, "audit candidate")
            if set(source) != required:
                raise CandidateAuditError("audit candidate fields do not match schema")
            candidate_id = _string(source.get("candidate_id"), "audit candidate ID")
            fingerprint = _string(source.get("fingerprint"), "audit fingerprint")
            if fingerprint in fingerprints:
                duplicates.append(
                    {
                        "candidate_id": candidate_id,
                        "duplicate_of": fingerprints[fingerprint],
                        "fingerprint": fingerprint,
                        "reason": "duplicate_fingerprint",
                    }
                )
                continue
            fingerprints[fingerprint] = candidate_id
            scores = source.get("perturbation_scores")
            if not isinstance(scores, list) or len(scores) != budget:
                raise CandidateAuditError(f"perturbation budget mismatch: {candidate_id}")
            if not all(isinstance(item, int | float) and not isinstance(item, bool) for item in scores):
                raise CandidateAuditError(f"perturbation scores are invalid: {candidate_id}")
            links = source.get("evidence_links")
            if not isinstance(links, list) or not links:
                raise CandidateAuditError(f"evidence links are missing: {candidate_id}")
            if not all(isinstance(item, str) and item.strip() for item in links):
                raise CandidateAuditError(f"evidence links are invalid: {candidate_id}")
            for key in ("unsafe", "temporal_match"):
                if not isinstance(source.get(key), bool):
                    raise CandidateAuditError(f"candidate {key} flag is invalid")
            records.append(
                {
                    "candidate_id": candidate_id,
                    "source_method": _string(source.get("source_method"), "source method"),
                    "fingerprint": fingerprint,
                    "component_set": _string(source.get("component_set"), "component set"),
                    "geometry": _string(source.get("geometry"), "candidate geometry"),
                    "conditioning": _string(source.get("conditioning"), "conditioning"),
                    "ad_distance": _number(source.get("ad_distance"), "AD distance"),
                    "uncertainty": _number(source.get("uncertainty"), "candidate uncertainty"),
                    "nearest_evidence_distance": _number(
                        source.get("nearest_evidence_distance"), "nearest evidence distance"
                    ),
                    "perturbation_scores": [round(_number(item, "perturbation score"), 8) for item in scores],
                    "unsafe": source["unsafe"],
                    "evidence_links": [str(item) for item in links],
                    "evidence_date": _string(source.get("evidence_date"), "evidence date"),
                    "temporal_match": source["temporal_match"],
                }
            )
        return records, duplicates

    @classmethod
    def _retrospective(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any], candidate_ids: set[str]
    ) -> dict[str, Any]:
        required = {
            "candidate_id",
            "evidence_id",
            "evidence_date",
            "match_type",
            "match_strength",
            "temporal_match",
            "used_for_selection",
        }
        matches: list[dict[str, Any]] = []
        freeze = date.fromisoformat(str(preregistration["design_freeze_date"]))
        for value in fixture["retrospective_matches"]:
            source = _mapping(value, "retrospective match")
            if set(source) != required:
                raise CandidateAuditError("retrospective fields do not match schema")
            candidate_id = _string(source.get("candidate_id"), "retrospective candidate ID")
            if candidate_id not in candidate_ids:
                raise CandidateAuditError(f"retrospective candidate is unknown: {candidate_id}")
            temporal = source.get("temporal_match")
            used_for_selection = source.get("used_for_selection")
            if not isinstance(temporal, bool) or used_for_selection is not False:
                raise CandidateAuditError("retrospective selection/temporal policy is invalid")
            evidence_date = _string(source.get("evidence_date"), "retrospective evidence date")
            parsed_date = date.fromisoformat(evidence_date)
            if temporal and parsed_date <= freeze:
                raise CandidateAuditError("temporal evidence must follow the design freeze")
            matches.append(
                {
                    "candidate_id": candidate_id,
                    "evidence_id": _string(source.get("evidence_id"), "evidence ID"),
                    "evidence_date": evidence_date,
                    "match_type": _string(source.get("match_type"), "match type"),
                    "match_strength": round(_number(source.get("match_strength"), "match strength"), 8),
                    "temporal_match": temporal,
                    "used_for_selection": False,
                }
            )
        temporal_matches = sum(row["temporal_match"] for row in matches)
        return {
            "schema_version": 1,
            "matches": matches,
            "temporal_matches": temporal_matches,
            "unresolved_matches": len(matches) - temporal_matches,
            "used_for_selection": False,
            "policy": "descriptive_only",
        }

    @classmethod
    def _audit_records(
        cls, records: list[dict[str, Any]], preregistration: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        supported: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for record in records:
            reasons: list[str] = []
            stability = sum(record["perturbation_scores"]) / len(record["perturbation_scores"])
            if record["ad_distance"] > float(preregistration["ad_threshold"]):
                reasons.append("high_applicability_domain_distance")
            if record["uncertainty"] > float(preregistration["uncertainty_threshold"]):
                reasons.append("high_uncertainty")
            if record["nearest_evidence_distance"] > float(preregistration["neighbor_distance_threshold"]):
                reasons.append("nearest_evidence_too_far")
            if stability < float(preregistration["stability_threshold"]):
                reasons.append("perturbation_instability")
            if record["unsafe"]:
                reasons.append("unsafe_candidate")
            audited = {
                **record,
                "perturbation_stability": round(stability, 8),
                "status": "SUPPORTED" if not reasons else "ABSTAIN",
                "reasons": reasons,
                "allowed_wording": ("exploratory_supported" if not reasons else "abstain_excluded"),
            }
            if reasons:
                rejected.append(audited)
            else:
                supported.append(audited)
        return supported, rejected

    def run(self, *, fixture: bool = True) -> CandidateAuditSummary:
        """Build candidate cards and evaluate later evidence descriptively."""
        if not fixture:
            raise CandidateAuditError("--fixture is required for candidate audit")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = self._preregistration(fixture_data)
        records, duplicates = self._candidates(fixture_data, preregistration)
        supported, rejected = self._audit_records(records, preregistration)
        audited_records = [*supported, *rejected]
        retrospective = self._retrospective(fixture_data, preregistration, {row["candidate_id"] for row in records})
        fixture_text = self.fixture_path.read_text(encoding="utf-8").lower()
        prohibited = ["api_key", "credential", "private_key", "locked_payload", "secret"]
        found = [token for token in prohibited if token in fixture_text]
        lockbox = {
            "schema_version": 1,
            "status": "CLEAN" if not found else "BLOCKED",
            "prohibited_tokens": found,
            "target_values_exposed": False,
            "raw_download": False,
            "network_accessed": False,
        }
        raw_payloads: dict[str, Any] = {
            "cards": {
                "schema_version": 1,
                "cards": supported,
                "target_values_exposed": False,
            },
            "deduplication": {
                "schema_version": 1,
                "raw_candidates": len(fixture_data["candidates"]),
                "unique_candidates": len(records),
                "duplicates": duplicates,
                "deduplication_passed": True,
            },
            "neighbors": {
                "schema_version": 1,
                "threshold": preregistration["neighbor_distance_threshold"],
                "cards": [
                    {
                        "candidate_id": row["candidate_id"],
                        "nearest_evidence_distance": row["nearest_evidence_distance"],
                        "evidence_links": row["evidence_links"],
                    }
                    for row in supported
                ],
            },
            "robustness": {
                "schema_version": 1,
                "stability_threshold": preregistration["stability_threshold"],
                "perturbation_budget": preregistration["perturbation_budget"],
                "records": [
                    {
                        "candidate_id": row["candidate_id"],
                        "stability": row["perturbation_stability"],
                        "status": row["status"],
                    }
                    for row in audited_records
                ],
            },
            "retrospective": retrospective,
            "abstentions": {
                "schema_version": 1,
                "entries": rejected,
                "count": len(rejected),
                "duplicates": duplicates,
                "allowed_wording": "abstain_excluded",
            },
            "failures": {
                "schema_version": 1,
                "status": "VALID" if not found else "INVALID",
                "failures": [],
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "cards": self.output_root / "candidate_cards.json",
            "deduplication": self.output_root / "deduplication_audit.json",
            "neighbors": self.output_root / "evidence_neighbor_audit.json",
            "robustness": self.output_root / "robustness_ledger.json",
            "retrospective": self.output_root / "retrospective_validation.json",
            "abstentions": self.output_root / "abstention_ledger.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        artifacts: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            payload = _canonical(raw_payloads[name])
            path.write_bytes(payload)
            artifacts[name] = {
                "path": (str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path)),
                "sha256": _sha256(payload),
                "bytes": len(payload),
            }
        lockbox_path = self.output_root / "lockbox_scan.json"
        lockbox_bytes = _canonical(lockbox)
        lockbox_path.write_bytes(lockbox_bytes)
        artifacts["lockbox"] = {
            "path": (
                str(lockbox_path.relative_to(self.root))
                if lockbox_path.is_relative_to(self.root)
                else str(lockbox_path)
            ),
            "sha256": _sha256(lockbox_bytes),
            "bytes": len(lockbox_bytes),
        }
        receipt_path = self.output_root / "candidate_audit_receipt.json"
        resumed = int(receipt_path.exists())
        rejected_count = len(fixture_data["candidates"]) - len(supported)
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "candidates": len(fixture_data["candidates"]),
            "unique_candidates": len(records),
            "duplicate_candidates": len(duplicates),
            "supported_candidates": len(supported),
            "rejected_candidates": rejected_count,
            "temporal_matches": retrospective["temporal_matches"],
            "unresolved_matches": retrospective["unresolved_matches"],
            "abstentions": len(rejected),
            "selected_wording": "exploratory_supported",
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifacts,
        }
        receipt_bytes = _canonical(receipt)
        receipt_path.write_bytes(receipt_bytes)
        manifest = {
            "schema_version": 1,
            "workflow": "DESIGN_CANDIDATE_AUDIT_RETROSPECTIVE_VALIDATION",
            "status": receipt["status"],
            "resume_key": resume_key,
            "resume_supported": True,
            "target_values_exposed": False,
            "artifacts": {
                **artifacts,
                "receipt": {
                    "path": (
                        str(receipt_path.relative_to(self.root))
                        if receipt_path.is_relative_to(self.root)
                        else str(receipt_path)
                    ),
                    "sha256": _sha256(receipt_bytes),
                    "bytes": len(receipt_bytes),
                },
            },
        }
        (self.output_root / "candidate_audit_manifest.json").write_bytes(_canonical(manifest))
        return CandidateAuditSummary(
            candidates=len(fixture_data["candidates"]),
            unique_candidates=len(records),
            duplicate_candidates=len(duplicates),
            supported_candidates=len(supported),
            rejected_candidates=rejected_count,
            temporal_matches=int(retrospective["temporal_matches"]),
            unresolved_matches=int(retrospective["unresolved_matches"]),
            abstentions=len(rejected),
            selected_wording="exploratory_supported",
            resumed=resumed,
            receipt_path=receipt_path,
        )
