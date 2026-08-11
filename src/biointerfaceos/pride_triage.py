"""Fixture-backed PRIDE project triage and sample-plan freeze."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

TRIAGE_FIXTURE = Path("tests/fixtures/omics/pride_triage.json")
TRIAGE_ROOT = Path("reports/omics/pride")


class PrideTriageError(RuntimeError):
    """Raised when a PRIDE triage fixture violates its auditable contract."""


@dataclass(frozen=True)
class PrideTriageSummary:
    """Summary and output paths from one PRIDE triage run."""

    projects: int
    eligible_projects: int
    review_projects: int
    metadata_only_projects: int
    sample_rows: int
    outputs: dict[str, Path]


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PrideTriageError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PrideTriageError(f"JSON object required: {path}")
    return value


def _date(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise PrideTriageError(f"{field} must be an ISO date")
    return value


def _family_ids(root: Path) -> set[str]:
    path = root / "registry/paper_families.parquet"
    try:
        rows = pq.read_table(path).to_pylist()
    except (OSError, ValueError) as exc:
        raise PrideTriageError(f"cannot read paper-family registry: {exc}") from exc
    values = {str(row.get("family_id")) for row in rows if row.get("family_id")}
    if not values:
        raise PrideTriageError("paper-family registry is empty")
    return values


def _jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise PrideTriageError(f"cannot read candidate registry: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PrideTriageError(f"invalid candidate registry JSON at line {number}") from exc
        if not isinstance(value, Mapping):
            raise PrideTriageError(f"candidate registry object required at line {number}")
        rows.append(dict(value))
    return rows


def _file_status(file_record: Mapping[str, Any]) -> str:
    access = file_record["access"]
    if access == "PUBLIC":
        return "PUBLIC"
    if access == "RESTRICTED":
        return "RESTRICTED"
    if access == "METADATA_ONLY":
        return "METADATA_ONLY"
    return "UNAVAILABLE"


class PrideTriage:
    """Validate PRIDE cards, sample maps, and split decisions without downloads."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / TRIAGE_FIXTURE
        self.output_root = output_root or self.root / TRIAGE_ROOT

    def _load(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        value = _read_json(self.fixture_path)
        if set(value) != {"schema_version", "scope", "projects"}:
            raise PrideTriageError("PRIDE triage fixture envelope is invalid")
        if value.get("schema_version") != 1 or value.get("scope") != "development":
            raise PrideTriageError("PRIDE triage fixture schema or scope is invalid")
        projects = value.get("projects")
        if not isinstance(projects, list) or not projects:
            raise PrideTriageError("PRIDE triage projects are missing")
        return value, [dict(project) for project in projects if isinstance(project, Mapping)]

    @staticmethod
    def _validate_file(file_record: Mapping[str, Any], project: str) -> None:
        fields = {
            "file_name",
            "kind",
            "size_bytes",
            "checksum_sha256",
            "checksum_status",
            "access",
        }
        if set(file_record) != fields:
            raise PrideTriageError(f"file fields are invalid for {project}")
        if (
            not isinstance(file_record["file_name"], str)
            or not file_record["file_name"]
            or file_record["kind"] not in {"RAW", "SEARCH", "RESULT", "METADATA"}
            or not isinstance(file_record["size_bytes"], int)
            or file_record["size_bytes"] < 0
            or file_record["access"] not in {"PUBLIC", "RESTRICTED", "METADATA_ONLY", "UNAVAILABLE"}
            or file_record["checksum_status"]
            not in {"CAPTURED_NOT_DOWNLOADED", "NOT_APPLICABLE", "UNAVAILABLE"}
        ):
            raise PrideTriageError(f"file values are invalid for {project}")
        checksum = file_record["checksum_sha256"]
        if file_record["checksum_status"] == "CAPTURED_NOT_DOWNLOADED":
            if not isinstance(checksum, str) or len(checksum) != 64:
                raise PrideTriageError(f"captured checksum is invalid for {project}")
        elif checksum is not None:
            raise PrideTriageError(f"non-captured file checksum must be null for {project}")

    @staticmethod
    def _validate_sample(sample: Mapping[str, Any], project: str) -> None:
        fields = {"sample_id", "label", "arm", "replicate", "biofluid", "evidence_locator"}
        if set(sample) != fields:
            raise PrideTriageError(f"sample-map fields are invalid for {project}")
        if (
            not isinstance(sample["sample_id"], str)
            or not isinstance(sample["label"], str)
            or sample["arm"] is not None
            and not isinstance(sample["arm"], str)
            or sample["replicate"] is not None
            and not isinstance(sample["replicate"], int)
            or not isinstance(sample["biofluid"], str)
            or not isinstance(sample["evidence_locator"], str)
            or not sample["evidence_locator"].startswith("PRIDE:")
        ):
            raise PrideTriageError(f"sample-map values are invalid for {project}")

    @staticmethod
    def _eligible(
        project: Mapping[str, Any], samples: list[dict[str, Any]]
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        availability = project["raw_search_availability"]
        if project["locked_project"]:
            reasons.append("LOCKED_METADATA_ONLY")
        if availability["raw"] != "PUBLIC":
            reasons.append("RAW_NOT_PUBLIC")
        if availability["search"] != "PUBLIC":
            reasons.append("SEARCH_NOT_PUBLIC")
        counts = project["replicate_counts"]
        if any(not isinstance(count, int) or count <= 0 for count in counts.values()):
            reasons.append("REPLICATE_COUNT_UNRESOLVED")
        if not samples:
            reasons.append("SAMPLE_MAP_EMPTY")
        if len({str(sample["sample_id"]) for sample in samples}) != len(samples):
            reasons.append("SAMPLE_ID_DUPLICATE")
        arms = set(str(arm) for arm in project["material_arms"])
        if any(sample["arm"] not in arms for sample in samples):
            reasons.append("SAMPLE_ARM_UNRESOLVED")
        observed_counts = Counter(str(sample["arm"]) for sample in samples)
        for arm, count in counts.items():
            if isinstance(count, int) and observed_counts.get(str(arm), 0) != count:
                reasons.append(f"REPLICATE_MAP_MISMATCH:{arm}")
        public_files = [file for file in project["file_inventory"] if file["access"] == "PUBLIC"]
        if any(file["checksum_status"] != "CAPTURED_NOT_DOWNLOADED" for file in public_files):
            reasons.append("PUBLIC_FILE_CHECKSUM_MISSING")
        return not reasons, reasons

    def run(self, *, scope: str = "development") -> PrideTriageSummary:
        """Build deterministic project cards and freeze sample-plan decisions."""
        fixture, projects = self._load()
        if scope != fixture["scope"]:
            raise PrideTriageError(f"unsupported triage scope: {scope}")
        family_ids = _family_ids(self.root)
        candidates = _jsonl(self.root / "registry/search_candidates.jsonl")
        candidate_by_id = {
            str(row["candidate_id"]): row
            for row in candidates
            if isinstance(row.get("candidate_id"), str)
        }
        required_project_fields = {
            "project_accession",
            "candidate_ids",
            "family_ids",
            "title",
            "submission_date",
            "publication_date",
            "species",
            "instrument",
            "file_inventory",
            "raw_search_availability",
            "material_arms",
            "biofluid",
            "replicate_counts",
            "outcomes",
            "sample_map",
            "evidence_locators",
            "locked_project",
            "split_decision",
            "decision_reason",
        }
        cards: list[dict[str, Any]] = []
        sample_maps: list[dict[str, Any]] = []
        eligibility: list[dict[str, Any]] = []
        review_queue: list[dict[str, Any]] = []
        seen_projects: set[str] = set()
        seen_candidates: set[str] = set()
        for raw_project in projects:
            if set(raw_project) != required_project_fields:
                raise PrideTriageError("PRIDE project card fields are invalid")
            project = dict(raw_project)
            accession = project["project_accession"]
            if not isinstance(accession, str) or not accession or accession in seen_projects:
                raise PrideTriageError("PRIDE project accessions are not unique")
            seen_projects.add(accession)
            candidate_ids = project["candidate_ids"]
            if not isinstance(candidate_ids, list) or not all(
                isinstance(candidate_id, str) for candidate_id in candidate_ids
            ):
                raise PrideTriageError(f"candidate IDs are invalid for {accession}")
            for candidate_id in candidate_ids:
                candidate = candidate_by_id.get(candidate_id)
                if candidate is None or candidate.get("source") != "pride":
                    raise PrideTriageError(f"candidate is not a PRIDE registry row: {candidate_id}")
                if candidate_id in seen_candidates:
                    raise PrideTriageError(
                        f"candidate is assigned to multiple projects: {candidate_id}"
                    )
                seen_candidates.add(candidate_id)
            if not isinstance(project["family_ids"], list) or not project["family_ids"]:
                raise PrideTriageError(f"family links are missing for {accession}")
            if not set(str(value) for value in project["family_ids"]) <= family_ids:
                raise PrideTriageError(f"family link is absent for {accession}")
            if not isinstance(project["title"], str) or not project["title"]:
                raise PrideTriageError(f"title is missing for {accession}")
            _date(project["submission_date"], "submission_date")
            _date(project["publication_date"], "publication_date")
            if (
                not isinstance(project["species"], list)
                or not project["species"]
                or not all(isinstance(value, str) for value in project["species"])
                or not isinstance(project["instrument"], str)
                or not project["instrument"]
            ):
                raise PrideTriageError(
                    f"official species/instrument metadata is invalid for {accession}"
                )
            files = project["file_inventory"]
            if not isinstance(files, list) or not files:
                raise PrideTriageError(f"file inventory is missing for {accession}")
            for file_record in files:
                if not isinstance(file_record, Mapping):
                    raise PrideTriageError(f"file inventory object is invalid for {accession}")
                self._validate_file(file_record, accession)
            availability = project["raw_search_availability"]
            if (
                not isinstance(availability, Mapping)
                or set(availability) != {"raw", "search"}
                or availability["raw"]
                not in {"PUBLIC", "RESTRICTED", "UNAVAILABLE", "METADATA_ONLY"}
                or availability["search"]
                not in {"PUBLIC", "RESTRICTED", "UNAVAILABLE", "METADATA_ONLY"}
            ):
                raise PrideTriageError(f"raw/search availability is invalid for {accession}")
            arms = project["material_arms"]
            if (
                not isinstance(arms, list)
                or not arms
                or not all(isinstance(arm, str) for arm in arms)
            ):
                raise PrideTriageError(f"material arms are missing for {accession}")
            if not isinstance(project["biofluid"], str) or not project["biofluid"]:
                raise PrideTriageError(f"biofluid status is missing for {accession}")
            counts = project["replicate_counts"]
            if not isinstance(counts, Mapping) or set(counts) != set(arms):
                raise PrideTriageError(
                    f"replicate counts do not cover material arms for {accession}"
                )
            outcomes = project["outcomes"]
            if not isinstance(outcomes, list) or not all(
                isinstance(value, str) for value in outcomes
            ):
                raise PrideTriageError(f"outcomes are invalid for {accession}")
            samples = project["sample_map"]
            if not isinstance(samples, list):
                raise PrideTriageError(f"sample map is invalid for {accession}")
            normalized_samples: list[dict[str, Any]] = []
            for sample in samples:
                if not isinstance(sample, Mapping):
                    raise PrideTriageError(f"sample map row is invalid for {accession}")
                self._validate_sample(sample, accession)
                normalized_samples.append(dict(sample))
            locators = project["evidence_locators"]
            if (
                not isinstance(locators, list)
                or not locators
                or not all(isinstance(locator, str) for locator in locators)
            ):
                raise PrideTriageError(f"evidence locators are missing for {accession}")
            if not isinstance(project["locked_project"], bool):
                raise PrideTriageError(f"locked flag is invalid for {accession}")
            if project["split_decision"] not in {"ELIGIBLE", "PARK_REVIEW", "METADATA_ONLY"}:
                raise PrideTriageError(f"split decision is invalid for {accession}")
            if not isinstance(project["decision_reason"], str) or not project["decision_reason"]:
                raise PrideTriageError(f"decision reason is missing for {accession}")
            eligible, reasons = self._eligible(project, normalized_samples)
            if project["split_decision"] == "ELIGIBLE" and not eligible:
                raise PrideTriageError(f"eligible project failed sample-plan checks: {accession}")
            if project["split_decision"] != "ELIGIBLE" and eligible:
                raise PrideTriageError(
                    f"non-eligible project passed sample-plan checks: {accession}"
                )
            card = dict(project)
            card["candidate_registry_status"] = "LINKED" if candidate_ids else "METADATA_ONLY_SEED"
            card["file_status_counts"] = dict(
                sorted(Counter(_file_status(file) for file in files).items())
            )
            card["sample_count"] = len(normalized_samples)
            card["sample_plan_valid"] = eligible
            card["no_raw_download"] = True
            card["locked_payload_accessed"] = False
            cards.append(card)
            sample_maps.append(
                {
                    "project_accession": accession,
                    "sample_count": len(normalized_samples),
                    "samples": normalized_samples,
                    "no_pseudo_replicates": True,
                }
            )
            eligibility_row = {
                "project_accession": accession,
                "family_ids": project["family_ids"],
                "split_decision": project["split_decision"],
                "eligible_for_split": eligible,
                "reasons": reasons,
                "split_group_key": (str(project["family_ids"][0]) if eligible else None),
                "no_pseudo_replicates": True,
            }
            eligibility.append(eligibility_row)
            if not eligible:
                review_queue.append(
                    {
                        "project_accession": accession,
                        "status": "OPEN",
                        "split_decision": project["split_decision"],
                        "reasons": reasons,
                        "decision_reason": project["decision_reason"],
                    }
                )

        manifest = {
            "schema_version": 1,
            "scope": scope,
            "projects": len(cards),
            "eligible_projects": sum(row["eligible_for_split"] for row in eligibility),
            "review_projects": sum(row["split_decision"] == "PARK_REVIEW" for row in eligibility),
            "metadata_only_projects": sum(
                row["split_decision"] == "METADATA_ONLY" for row in eligibility
            ),
            "sample_rows": sum(len(value["samples"]) for value in sample_maps),
            "no_raw_download": True,
            "locked_payload_accessed": False,
            "no_pseudo_replicates": True,
        }
        input_hashes = {
            "fixture": _sha256(self.fixture_path.read_bytes()),
            "paper_families": _sha256((self.root / "registry/paper_families.parquet").read_bytes()),
            "search_candidates": _sha256(
                (self.root / "registry/search_candidates.jsonl").read_bytes()
            ),
            "pride_project_fixture": _sha256(
                (self.root / "tests/fixtures/sources/pride/project_PXD000001.json").read_bytes()
            ),
            "pride_files_fixture": _sha256(
                (self.root / "tests/fixtures/sources/pride/files_PXD000001.json").read_bytes()
            ),
        }
        outputs = {
            "project_cards.json": {"schema_version": 1, "cards": cards},
            "sample_maps.json": {"schema_version": 1, "maps": sample_maps},
            "split_eligibility.json": {
                "schema_version": 1,
                "manifest": manifest,
                "projects": eligibility,
            },
            "review_queue.json": {"schema_version": 1, "queue": review_queue},
        }
        self.output_root.mkdir(parents=True, exist_ok=True)
        serialized = {name: _canonical(value) for name, value in outputs.items()}
        receipt = {
            "schema_version": 1,
            "scope": scope,
            "input_sha256": input_hashes,
            "output_sha256": {name: _sha256(content) for name, content in serialized.items()},
            **manifest,
        }
        serialized["triage_receipt.json"] = _canonical(receipt)
        for name, content in serialized.items():
            (self.output_root / name).write_bytes(content)
        return PrideTriageSummary(
            projects=len(cards),
            eligible_projects=int(manifest["eligible_projects"]),
            review_projects=int(manifest["review_projects"]),
            metadata_only_projects=int(manifest["metadata_only_projects"]),
            sample_rows=int(manifest["sample_rows"]),
            outputs={name: self.output_root / name for name in serialized},
        )
