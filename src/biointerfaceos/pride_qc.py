"""Fixture-backed PRIDE QC and author-result concordance audit."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class PrideQCError(RuntimeError):
    """Raised when the bounded PRIDE QC fixture is invalid."""


@dataclass(frozen=True)
class PrideQCSummary:
    """Summary of one PRIDE QC/concordance audit."""

    attempted_projects: int
    processed_qc_passed: int
    failed_projects: int
    claims: int
    concordant: int
    discrepant: int
    unavailable: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PrideQCError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PrideQCError(f"{label} must be a non-empty string")
    return value.strip()


def _float(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, float | int):
        raise PrideQCError(f"{label} must be numeric")
    return float(value)


class PrideQCWorkflow:
    """Audit three or more development PRIDE projects without payload access."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/omics/pride_qc_fixture.json"
        self.output_root = output_root or self.root / "reports/omics/pride_qc"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PrideQCError(f"cannot load PRIDE QC fixture: {exc}") from exc
        fixture = _mapping(data, "PRIDE QC fixture")
        if fixture.get("schema_version") != 1:
            raise PrideQCError("PRIDE QC fixture schema_version must be 1")
        for key in ("inputs", "gates", "projects", "author_claims"):
            if key not in fixture:
                raise PrideQCError(f"PRIDE QC fixture missing {key}")
        if not isinstance(fixture["projects"], list) or not isinstance(
            fixture["author_claims"], list
        ):
            raise PrideQCError("projects and author_claims must be lists")
        if len(fixture["projects"]) < 3:
            raise PrideQCError("at least three development projects must be attempted")
        return fixture

    def _read_hashed_json(self, relative: str, declared_sha: str, label: str) -> dict[str, Any]:
        path = (self.root / relative).resolve(strict=True)
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise PrideQCError(f"{label} must remain inside repository") from exc
        if _sha256_path(path) != declared_sha:
            raise PrideQCError(f"{label} checksum differs from fixture")
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PrideQCError(f"cannot load {label}: {exc}") from exc

    def _verify_inputs(self, data: Mapping[str, Any]) -> dict[str, Any]:
        inputs = _mapping(data["inputs"], "inputs")
        paths = {
            "project_cards": ("project_cards_path", "project_cards_sha256"),
            "split_eligibility": ("split_eligibility_path", "split_eligibility_sha256"),
            "search_receipt": ("search_receipt_path", "search_receipt_sha256"),
            "ratio_recovery": ("ratio_recovery_path", "ratio_recovery_sha256"),
            "harmonization_receipt": (
                "harmonization_receipt_path",
                "harmonization_receipt_sha256",
            ),
        }
        outputs: dict[str, Any] = {}
        for label, (path_key, hash_key) in paths.items():
            relative = _string(inputs.get(path_key), f"inputs.{path_key}")
            declared_sha = _string(inputs.get(hash_key), f"inputs.{hash_key}")
            outputs[label] = self._read_hashed_json(relative, declared_sha, label)
        if outputs["search_receipt"].get("status") != "COMPLETED":
            raise PrideQCError("search receipt is not completed")
        if outputs["harmonization_receipt"].get("status") != "COMPLETED":
            raise PrideQCError("harmonization receipt is not completed")
        return outputs

    @staticmethod
    def _project_card_map(cards: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        values = cards.get("cards")
        if not isinstance(values, list):
            raise PrideQCError("project cards have no cards")
        result: dict[str, dict[str, Any]] = {}
        for value in values:
            card = _mapping(value, "project card")
            accession = _string(card.get("project_accession"), "project card accession")
            result[accession] = card
        return result

    @staticmethod
    def _ratio_map(ratio_report: Mapping[str, Any]) -> dict[str, float]:
        values = ratio_report.get("results")
        if not isinstance(values, list):
            raise PrideQCError("ratio recovery report has no results")
        result: dict[str, float] = {}
        for value in values:
            row = _mapping(value, "ratio result")
            result[_string(row.get("protein_accession"), "ratio protein")] = _float(
                row.get("observed_ratio"), "ratio observed"
            )
        return result

    def _audit_projects(
        self,
        data: Mapping[str, Any],
        inputs: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        gates = _mapping(data["gates"], "gates")
        min_replicates = int(_float(gates.get("min_replicates"), "gates.min_replicates"))
        max_fdr = _float(gates.get("max_fdr"), "gates.max_fdr")
        min_intensity_fraction = _float(
            gates.get("min_observed_intensity_fraction"),
            "gates.min_observed_intensity_fraction",
        )
        cards = self._project_card_map(inputs["project_cards"])
        eligibility = _mapping(inputs["split_eligibility"], "split eligibility").get("projects")
        if not isinstance(eligibility, list):
            raise PrideQCError("split eligibility has no projects")
        eligibility_map = {
            _string(
                _mapping(value, "eligibility row").get("project_accession"),
                "eligibility accession",
            ): _mapping(value, "eligibility row")
            for value in eligibility
        }
        ratios = self._ratio_map(inputs["ratio_recovery"])
        _float(
            _mapping(inputs["search_receipt"].get("fdr"), "search fdr").get("estimated_fdr"),
            "search estimated fdr",
        )
        author_claims = cast(list[Any], data["author_claims"])
        claims_by_project: dict[str, list[dict[str, Any]]] = {}
        for value in author_claims:
            claim = _mapping(value, "author claim")
            claim_project = _string(claim.get("project_accession"), "author claim project")
            _string(claim.get("claim_id"), "author claim id")
            _string(claim.get("locator"), "author claim locator")
            claims_by_project.setdefault(claim_project, []).append(claim)
        qc_rows: list[dict[str, Any]] = []
        concordance_rows: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for project_value in cast(list[Any], data["projects"]):
            qc_project = _mapping(project_value, "QC project")
            accession = _string(qc_project.get("project_accession"), "QC project accession")
            card = cards.get(accession)
            eligibility_row = eligibility_map.get(accession)
            if card is None or eligibility_row is None:
                raise PrideQCError(f"QC project is absent from T052 outputs: {accession}")
            raw_access = _string(
                _mapping(card.get("raw_search_availability"), "raw availability").get("raw"),
                "raw availability",
            )
            replicate_counts = card.get("replicate_counts")
            if not isinstance(replicate_counts, Mapping):
                raise PrideQCError(f"replicate counts are invalid: {accession}")
            replicate_values = [
                value for value in replicate_counts.values() if isinstance(value, int)
            ]
            replicate_pass = bool(replicate_values) and min(replicate_values) >= min_replicates
            project_metrics = _mapping(qc_project.get("processed_metrics"), "processed metrics")
            fdr = project_metrics.get("search_fdr")
            intensity_fraction = project_metrics.get("observed_intensity_fraction")
            fdr_pass = fdr is not None and _float(fdr, "project search_fdr") <= max_fdr
            intensity_pass = (
                intensity_fraction is not None
                and _float(intensity_fraction, "project intensity fraction")
                >= min_intensity_fraction
            )
            access_pass = raw_access == "PUBLIC" and not bool(card.get("locked_project"))
            processed_pass = replicate_pass and fdr_pass and intensity_pass
            if processed_pass:
                status = "PASS_PROCESSED_ONLY"
                grade = "G3_PROCESSED_FIXTURE"
            else:
                status = "FAIL_PROCESSED_QC"
                grade = "G1_METADATA_ONLY"
            reasons: list[str] = []
            if not access_pass:
                reasons.append("RAW_NOT_PUBLIC" if raw_access != "PUBLIC" else "LOCKED_PROJECT")
            if not replicate_pass:
                reasons.append("REPLICATE_QC_FAILED")
            if not fdr_pass:
                reasons.append("FDR_QC_FAILED")
            if not intensity_pass:
                reasons.append("INTENSITY_QC_FAILED")
            if not access_pass and status == "PASS_PROCESSED_ONLY":
                status = "PASS_PROCESSED_ONLY_RAW_UNAVAILABLE"
            qc_rows.append(
                {
                    "project_accession": accession,
                    "split_decision": eligibility_row["split_decision"],
                    "raw_access": raw_access,
                    "locked_project": bool(card.get("locked_project")),
                    "raw_payload_accessed": False,
                    "replicate_counts": dict(replicate_counts),
                    "replicate_gate": replicate_pass,
                    "search_fdr": fdr,
                    "fdr_gate": fdr_pass,
                    "observed_intensity_fraction": intensity_fraction,
                    "intensity_gate": intensity_pass,
                    "processed_qc_pass": processed_pass,
                    "status": status,
                    "evidence_grade": grade,
                    "failure_reasons": reasons,
                    "evidence_locators": card.get("evidence_locators", []),
                }
            )
            if reasons:
                failures.append(
                    {
                        "project_accession": accession,
                        "reasons": reasons,
                        "status": status,
                        "evidence_grade": grade,
                    }
                )
            for claim in claims_by_project.get(accession, []):
                protein = _string(claim.get("protein_accession"), "claim protein")
                author_value = _float(claim.get("author_ratio"), "claim author_ratio")
                tolerance = _float(claim.get("tolerance"), "claim tolerance")
                analysis_value = ratios.get(protein) if processed_pass else None
                if analysis_value is None:
                    concordance = "UNAVAILABLE"
                    reason = "PROJECT_QC_FAILED_OR_NO_COMPARABLE_RESULT"
                elif abs(analysis_value - author_value) <= tolerance:
                    concordance = "CONCORDANT"
                    reason = None
                else:
                    concordance = "DISCREPANT"
                    reason = "RATIO_DIFFERS_BEYOND_TOLERANCE"
                concordance_rows.append(
                    {
                        "project_accession": accession,
                        "claim_id": claim["claim_id"],
                        "locator": claim["locator"],
                        "protein_accession": protein,
                        "author_ratio": author_value,
                        "analysis_ratio": analysis_value,
                        "tolerance": tolerance,
                        "concordance": concordance,
                        "reason": reason,
                    }
                )
        return qc_rows, concordance_rows, failures

    def run(self, *, fixture: bool = False) -> PrideQCSummary:
        """Run PRIDE project QC and author concordance."""
        if not fixture:
            raise PrideQCError("--fixture is required for the bounded PRIDE QC workflow")
        data = self._load_fixture()
        inputs = self._verify_inputs(data)
        qc_rows, concordance_rows, failures = self._audit_projects(data, inputs)
        processed_passed = sum(bool(row["processed_qc_pass"]) for row in qc_rows)
        concordant = sum(row["concordance"] == "CONCORDANT" for row in concordance_rows)
        discrepant = sum(row["concordance"] == "DISCREPANT" for row in concordance_rows)
        unavailable = sum(row["concordance"] == "UNAVAILABLE" for row in concordance_rows)
        if processed_passed < 1:
            raise PrideQCError("no project passed processed QC")
        resume_material = {
            "qc": qc_rows,
            "concordance": concordance_rows,
            "failures": failures,
        }
        resume_key = _sha256(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "qc": self.output_root / "project_qc.json",
            "concordance": self.output_root / "author_concordance.json",
            "failures": self.output_root / "failure_ledger.json",
            "grades": self.output_root / "evidence_grades.json",
            "summary": self.output_root / "qc_summary.json",
            "receipt": self.output_root / "qc_receipt.json",
            "log": self.output_root / "qc_log.json",
            "manifest": self.output_root / "qc_manifest.json",
        }
        grades = {
            "schema_version": 1,
            "projects": [
                {
                    "project_accession": row["project_accession"],
                    "evidence_grade": row["evidence_grade"],
                    "processed_qc_pass": row["processed_qc_pass"],
                    "raw_qc_status": "NOT_RUN_NO_DOWNLOAD",
                    "claim_statuses": sorted(
                        {
                            claim["concordance"]
                            for claim in concordance_rows
                            if claim["project_accession"] == row["project_accession"]
                        }
                    ),
                }
                for row in qc_rows
            ],
        }
        summary = {
            "schema_version": 1,
            "attempted_projects": len(qc_rows),
            "processed_qc_passed": processed_passed,
            "failed_projects": len(failures),
            "claims": len(concordance_rows),
            "concordant": concordant,
            "discrepant": discrepant,
            "unavailable": unavailable,
            "all_projects_attempted": len(qc_rows) >= 3,
        }
        raw_payloads = {
            "qc": {"schema_version": 1, "projects": qc_rows},
            "concordance": {"schema_version": 1, "claims": concordance_rows},
            "failures": {"schema_version": 1, "append_only": True, "entries": failures},
            "grades": grades,
            "summary": summary,
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root))
                if path.is_relative_to(self.root)
                else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "inputs": data["inputs"],
            "gates": data["gates"],
            "summary": summary,
            "raw_payload_accessed": False,
            "locked_payload_accessed": False,
            "real_network_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "three_project_attempt_gate_passed", "projects": len(qc_rows)},
                {"event": "processed_qc_evaluated", "passed": processed_passed},
                {"event": "concordance_evaluated", "claims": len(concordance_rows)},
                {"event": "failure_ledger_written", "entries": len(failures)},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            **summary,
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path),
                    "sha256": _sha256(payload_bytes[name]),
                    "bytes": len(payload_bytes[name]),
                }
                for name, path in paths.items()
                if name in payload_bytes
            },
        }
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise PrideQCError("existing PRIDE QC receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise PrideQCError(f"existing PRIDE QC artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return PrideQCSummary(
            attempted_projects=len(qc_rows),
            processed_qc_passed=processed_passed,
            failed_projects=len(failures),
            claims=len(concordance_rows),
            concordant=concordant,
            discrepant=discrepant,
            unavailable=unavailable,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
