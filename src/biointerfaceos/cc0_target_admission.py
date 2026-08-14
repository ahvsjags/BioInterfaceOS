"""Fail-closed T129 screening for a CC0 human protein-corona model target.

The screening records source-asset evidence but does not treat two compatible
licences, author result tables, or source labels as a common model endpoint.
"""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CC0TargetAdmissionError(RuntimeError):
    """Raised when a T129 target-admission decision is unsafe."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CC0TargetAdmissionError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list) or len(value) < minimum:
        raise CC0TargetAdmissionError(f"{label} must contain at least {minimum} items")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CC0TargetAdmissionError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CC0TargetAdmissionError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class CC0TargetAdmissionSummary:
    """Compact accounting for a strict, non-admission screening result."""

    candidate_source_count: int
    candidate_laboratory_count: int
    source_condition_count: int
    receipt_path: Path


class CC0TargetAdmissionWorkflow:
    """Audit CC0 candidate evidence without silently freezing a model target."""

    AUDIT_ID = "bioif-r2-cc0-target-admission-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R2_T129_CC0_TARGET_ADMISSION_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_2/cc0_target_admission/v1.0.0"
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
        "require_study_held_out_split",
        "prohibit_author_quantification_concatenation",
        "prohibit_predictive_identity_features",
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
        "screened_asset",
        "source_conditions",
        "numeric_covariate_map_status",
        "author_quantification_status",
        "analysis_unit_status",
        "admission",
        "model_use",
        "non_admission_reasons",
    }
    REQUIRED_ASSET_FIELDS = {
        "file_name",
        "download_url",
        "publisher_api_bytes",
        "local_bytes",
        "local_sha256",
        "content_type",
        "cell_evidence",
    }
    REQUIRED_CELL_EVIDENCE_FIELDS = {"worksheet", "cell", "observed_value"}
    REQUIRED_CONDITION_FIELDS = {
        "source_condition_id",
        "source_label",
        "source_label_cell",
        "author_quantification_columns",
        "replicate_role_status",
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
            raise CC0TargetAdmissionError(f"cannot parse {label}") from exc

    def _registry(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T129 CC0 target-admission registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise CC0TargetAdmissionError("CC0 target-admission registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise CC0TargetAdmissionError("CC0 target-admission registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise CC0TargetAdmissionError("CC0 target-admission evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise CC0TargetAdmissionError("CC0 target-admission claim level is unsafe")
        _string(registry.get("evaluated_at"), "CC0 target-admission evaluated_at")
        if _string(registry.get("development_cutoff"), "CC0 target-admission cutoff") != ("2024-12-31T23:59:59+00:00"):
            raise CC0TargetAdmissionError("CC0 target-admission cutoff changed")

        policy = _mapping(registry.get("source_policy"), "CC0 target-admission policy")
        if set(policy) != self.REQUIRED_POLICY_FIELDS:
            raise CC0TargetAdmissionError("CC0 target-admission policy fields are invalid")
        if set(_list(policy.get("allowed_licenses"), "CC0 target-admission licences")) != (self.ALLOWED_LICENSES):
            raise CC0TargetAdmissionError("CC0 target-admission licences are invalid")
        for field in self.REQUIRED_POLICY_FIELDS - {"allowed_licenses"}:
            if policy.get(field) is not True:
                raise CC0TargetAdmissionError("CC0 target-admission safety policy is weakened")

        candidates: list[dict[str, Any]] = []
        source_ids: set[str] = set()
        laboratories: set[str] = set()
        for value in _list(registry.get("candidates"), "CC0 target-admission candidates", minimum=2):
            candidate = _mapping(value, "CC0 target-admission candidate")
            if set(candidate) != self.REQUIRED_CANDIDATE_FIELDS:
                raise CC0TargetAdmissionError("CC0 target-admission candidate fields are invalid")
            for field in self.REQUIRED_CANDIDATE_FIELDS - {
                "screened_asset",
                "source_conditions",
                "non_admission_reasons",
            }:
                _string(candidate.get(field), f"CC0 target-admission candidate {field}")
            source_id = candidate["source_id"]
            if source_id in source_ids or source_id != f"PRIDE-{candidate['accession']}":
                raise CC0TargetAdmissionError("CC0 target-admission source identity is invalid")
            source_ids.add(source_id)
            if not candidate["project_api_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise CC0TargetAdmissionError("CC0 target-admission API locator is invalid")
            if not candidate["landing_url"].startswith("https://www.ebi.ac.uk/pride/"):
                raise CC0TargetAdmissionError("CC0 target-admission landing locator is invalid")
            if candidate["publication_date"] > "2024-12-31":
                raise CC0TargetAdmissionError("CC0 target-admission source is post-freeze")
            if candidate["license_id"] not in self.ALLOWED_LICENSES:
                raise CC0TargetAdmissionError("CC0 target-admission licence is unsafe")
            if candidate["access"] != "ANONYMOUS_PUBLIC":
                raise CC0TargetAdmissionError("CC0 target-admission access is restricted")
            if "human" not in candidate["biological_context"].lower():
                raise CC0TargetAdmissionError("CC0 target-admission source is not human-biofluid")
            laboratories.add(candidate["laboratory"])

            asset = _mapping(candidate["screened_asset"], "CC0 target-admission asset")
            if set(asset) != self.REQUIRED_ASSET_FIELDS:
                raise CC0TargetAdmissionError("CC0 target-admission asset fields are invalid")
            for field in self.REQUIRED_ASSET_FIELDS - {
                "publisher_api_bytes",
                "local_bytes",
                "cell_evidence",
            }:
                _string(asset.get(field), f"CC0 target-admission asset {field}")
            for field in ("publisher_api_bytes", "local_bytes"):
                _integer(asset.get(field), f"CC0 target-admission asset {field}", minimum=1)
            digest = asset["local_sha256"].lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise CC0TargetAdmissionError("CC0 target-admission asset SHA-256 is invalid")
            if not asset["download_url"].startswith("https://ftp.pride.ebi.ac.uk/"):
                raise CC0TargetAdmissionError("CC0 target-admission asset needs an official HTTPS URL")
            for cell_value in _list(asset.get("cell_evidence"), "CC0 target-admission cell evidence", minimum=3):
                cell = _mapping(cell_value, "CC0 target-admission cell evidence")
                if set(cell) != self.REQUIRED_CELL_EVIDENCE_FIELDS:
                    raise CC0TargetAdmissionError("CC0 target-admission cell evidence is invalid")
                for field in self.REQUIRED_CELL_EVIDENCE_FIELDS:
                    _string(cell.get(field), f"CC0 target-admission cell {field}")

            conditions = _list(
                candidate.get("source_conditions"),
                "CC0 target-admission source conditions",
                minimum=1,
            )
            condition_ids: set[str] = set()
            for condition_value in conditions:
                condition = _mapping(condition_value, "CC0 target-admission source condition")
                if set(condition) != self.REQUIRED_CONDITION_FIELDS:
                    raise CC0TargetAdmissionError("CC0 target-admission condition fields are invalid")
                for field in self.REQUIRED_CONDITION_FIELDS - {"author_quantification_columns"}:
                    _string(condition.get(field), f"CC0 target-admission condition {field}")
                condition_id = condition["source_condition_id"]
                if condition_id in condition_ids or not condition_id.startswith(f"{source_id}-"):
                    raise CC0TargetAdmissionError("CC0 target-admission condition identity is invalid")
                condition_ids.add(condition_id)
                columns = _list(
                    condition.get("author_quantification_columns"),
                    "CC0 target-admission author quantification columns",
                    minimum=1,
                )
                if any(not isinstance(column, str) or not column.strip() for column in columns):
                    raise CC0TargetAdmissionError("CC0 target-admission quantification column is invalid")

            if candidate["numeric_covariate_map_status"] != ("MISSING_IN_SELECTED_CC0_SOURCE_ASSETS"):
                raise CC0TargetAdmissionError("CC0 target-admission silently promotes covariates")
            if candidate["admission"] != "NOT_ADMITTED" or candidate["model_use"] != "PROHIBITED":
                raise CC0TargetAdmissionError("CC0 target-admission silently promotes a target")
            reasons = _list(
                candidate.get("non_admission_reasons"),
                "CC0 target-admission non-admission reasons",
                minimum=2,
            )
            if any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
                raise CC0TargetAdmissionError("CC0 target-admission reason is invalid")
            candidates.append(candidate)
        if len(source_ids) != 2 or len(laboratories) != 2:
            raise CC0TargetAdmissionError("CC0 target-admission candidate cohort is invalid")
        return registry, sorted(candidates, key=lambda row: str(row["source_id"]))

    def run(self, *, strict: bool = False) -> CC0TargetAdmissionSummary:
        """Write the immutable no-target decision for the screened CC0 candidates."""

        if not strict:
            raise CC0TargetAdmissionError("CC0 target-admission audit requires --strict")
        if self.output_root.exists():
            raise CC0TargetAdmissionError("CC0 target-admission audit already executed")
        registry, candidates = self._registry()
        laboratory_count = len({candidate["laboratory"] for candidate in candidates})
        condition_count = sum(len(candidate["source_conditions"]) for candidate in candidates)
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": registry["evaluated_at"],
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "candidate_source_count": len(candidates),
            "candidate_laboratory_count": laboratory_count,
            "source_condition_count": condition_count,
            "candidates": candidates,
            "status": "BLOCKED_NO_CC0_COMMON_TARGET",
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "admissible_target_count": 0,
            "blocked_reasons": [
                "Neither selected CC0 source asset provides a source-matched numeric material or "
                "size covariate map; formulation names are retained as source labels only.",
                "The candidate tables are author-specific quantitative outputs and are not "
                "concatenated into a cross-study abundance scale.",
                "No common preprocessing endpoint, biological analysis-unit manifest, or "
                "study-held-out split has been frozen, so T121 Amendment v1.0.1 is not created.",
            ],
            "next_required_evidence": [
                "Obtain reusable CC0 source assets that map each biological analysis unit to "
                "numeric material or size covariates without inferring semantics from labels.",
                "Freeze one shared preprocessing endpoint across independent laboratories and "
                "separate biological, technical, fraction and channel roles.",
                "Create and hash a versioned T121 amendment before enabling a new T123 model gate.",
            ],
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "target_admission_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": decision["status"],
            "target_admission_decision_sha256": _sha256(decision_path),
            "candidate_source_count": decision["candidate_source_count"],
            "candidate_laboratory_count": decision["candidate_laboratory_count"],
            "source_condition_count": decision["source_condition_count"],
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
        receipt_path = self.output_root / "target_admission_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return CC0TargetAdmissionSummary(
            candidate_source_count=_integer(receipt["candidate_source_count"], "candidate source count", minimum=2),
            candidate_laboratory_count=_integer(
                receipt["candidate_laboratory_count"], "candidate laboratory count", minimum=2
            ),
            source_condition_count=_integer(receipt["source_condition_count"], "source condition count", minimum=1),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable target-admission receipt and no-model boundary."""

        decision_path = self.output_root / "target_admission_decision.json"
        receipt_path = self.output_root / "target_admission_receipt.json"
        decision = self._json(decision_path, "CC0 target-admission decision")
        receipt = self._json(receipt_path, "CC0 target-admission receipt")
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
            or receipt.get("status") != "BLOCKED_NO_CC0_COMMON_TARGET"
            or decision.get("status") != receipt["status"]
            or receipt.get("target_admission_decision_sha256") != _sha256(decision_path)
            or receipt.get("candidate_source_count") != 2
            or receipt.get("candidate_laboratory_count") != 2
            or receipt.get("source_condition_count") != 9
            or receipt.get("admissible_target_count") != 0
            or receipt.get("target_status") != "NOT_FROZEN"
            or receipt.get("model_use") != "PROHIBITED"
            or decision.get("admissible_target_count") != 0
            or decision.get("target_status") != "NOT_FROZEN"
            or decision.get("model_use") != "PROHIBITED"
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise CC0TargetAdmissionError("CC0 target-admission receipt is invalid")
        return receipt
