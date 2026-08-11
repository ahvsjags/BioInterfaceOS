"""Species-aware protein identifier and orthology resolution."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class ProteinResolutionError(ValueError):
    """Raised when a protein/orthology fixture violates its contract."""


@dataclass(frozen=True)
class ProteinResolutionSummary:
    """Counts and output paths from one fixture run."""

    mentions: int
    resolved: int
    ambiguous: int
    obsolete_review: int
    orthology_groups: int
    orthology_edges: int
    review_items: int
    entities_path: Path
    orthology_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ProteinResolutionError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ProteinResolutionError(f"{name} must be finite")
    return result


class ProteinResolver:
    """Resolve protein mentions by species and preserve orthology multiplicity."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        entities_path: Path | None = None,
        orthology_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/proteins/protein_resolution.json"
        )
        self.entities_path = entities_path or self.root / "registry/protein_entities.json"
        self.orthology_path = orthology_path or (self.root / "registry/orthology_groups.json")
        self.review_path = review_path or (self.root / "registry/protein_review_queue.jsonl")
        self.report_path = report_path or self.root / "reports/protein_resolution.md"

    @staticmethod
    def _load_fixture(
        path: Path,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProteinResolutionError(f"cannot load protein fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {
            "schema_version",
            "proteins",
            "orthology_groups",
        }:
            raise ProteinResolutionError("protein fixture envelope is invalid")
        if value["schema_version"] != 1:
            raise ProteinResolutionError("protein fixture schema is invalid")
        if not isinstance(value["proteins"], list) or not isinstance(
            value["orthology_groups"], list
        ):
            raise ProteinResolutionError("protein or orthology fixture lists are invalid")
        proteins = [dict(item) for item in value["proteins"] if isinstance(item, Mapping)]
        groups = [dict(item) for item in value["orthology_groups"] if isinstance(item, Mapping)]
        if len(proteins) != len(value["proteins"]) or len(groups) != len(value["orthology_groups"]):
            raise ProteinResolutionError("protein fixture contains a non-object")
        return proteins, groups

    def _resolve_proteins(
        self,
        proteins: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        required = {"mention_id", "raw_name", "species", "source_locator", "candidates"}
        candidate_required = {
            "accession",
            "gene_id",
            "protein_name",
            "isoform_status",
            "resolution_method",
            "confidence",
            "obsolete",
            "replaced_by",
        }
        entities: list[dict[str, Any]] = []
        by_mention: dict[str, dict[str, Any]] = {}
        for raw in proteins:
            if set(raw) != required:
                raise ProteinResolutionError("protein mention fields are invalid")
            mention_id = _text(raw["mention_id"])
            raw_name = _text(raw["raw_name"])
            species = _text(raw["species"])
            locator = _text(raw["source_locator"])
            candidates_raw = raw["candidates"]
            if not mention_id or not raw_name or not species or not locator.startswith("asset:"):
                raise ProteinResolutionError("protein mention identifiers/species/locator invalid")
            if not isinstance(candidates_raw, list) or not candidates_raw:
                raise ProteinResolutionError(f"{mention_id} has no candidates")
            candidates: list[dict[str, Any]] = []
            for candidate in candidates_raw:
                if not isinstance(candidate, Mapping) or set(candidate) != candidate_required:
                    raise ProteinResolutionError(f"{mention_id} candidate fields are invalid")
                confidence = _float(candidate["confidence"], f"{mention_id}.confidence")
                if not 0.0 <= confidence <= 1.0:
                    raise ProteinResolutionError(f"{mention_id} confidence is out of range")
                if bool(candidate["obsolete"]) and candidate["replaced_by"] is None:
                    raise ProteinResolutionError(f"{mention_id} obsolete mapping lacks replacement")
                candidates.append(dict(candidate))
            candidates.sort(key=lambda item: float(item["confidence"]), reverse=True)
            top = candidates[0]
            obsolete = bool(top["obsolete"])
            if obsolete:
                status = "OBSOLETE_REVIEW"
                reason = "OBSOLETE_ACCESSION_REQUIRES_REVIEW"
            elif len(candidates) > 1:
                status = "AMBIGUOUS"
                reason = (
                    "ISOFORM_AMBIGUITY"
                    if any(
                        "isoform" in _text(item["isoform_status"]).lower() for item in candidates
                    )
                    else "MULTIPLE_PROTEIN_CANDIDATES"
                )
            elif float(top["confidence"]) >= 0.8:
                status = "RESOLVED"
                reason = None
            else:
                status = "AMBIGUOUS"
                reason = "LOW_CONFIDENCE_PROTEIN_MAPPING"
            if reason is not None:
                reviews.append(
                    {
                        "review_id": f"protein-review:{mention_id}",
                        "reason": reason,
                        "mention_id": mention_id,
                        "species": species,
                        "raw_name": raw_name,
                        "source_locator": locator,
                        "candidate_accessions": [item["accession"] for item in candidates],
                        "resolution": "MANUAL_REVIEW",
                    }
                )
            entity = {
                "mention_id": mention_id,
                "raw_name": raw_name,
                "species": species,
                "source_locator": locator,
                "status": status,
                "resolved_protein": top if status == "RESOLVED" else None,
                "candidate_mappings": candidates,
            }
            entities.append(entity)
            by_mention[mention_id] = entity
        return entities, by_mention

    def _orthology(
        self,
        groups: list[dict[str, Any]],
        by_mention: Mapping[str, dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        required = {"group_id", "source_locator", "members"}
        member_required = {"mention_id", "relationship", "source_locator"}
        output: list[dict[str, Any]] = []
        edge_count = 0
        for raw in groups:
            if set(raw) != required:
                raise ProteinResolutionError("orthology group fields are invalid")
            group_id = _text(raw["group_id"])
            locator = _text(raw["source_locator"])
            raw_members = raw["members"]
            if not group_id or not locator.startswith("asset:"):
                raise ProteinResolutionError("orthology group identifiers/locator invalid")
            if not isinstance(raw_members, list) or len(raw_members) < 2:
                raise ProteinResolutionError(f"{group_id} needs at least two members")
            members: list[dict[str, Any]] = []
            for raw_member in raw_members:
                if not isinstance(raw_member, Mapping) or set(raw_member) != member_required:
                    raise ProteinResolutionError(f"{group_id} member fields are invalid")
                mention_id = _text(raw_member["mention_id"])
                member_locator = _text(raw_member["source_locator"])
                if mention_id not in by_mention or not member_locator.startswith("asset:"):
                    raise ProteinResolutionError(f"{group_id} member identity/locator invalid")
                entity = by_mention[mention_id]
                resolved = entity["resolved_protein"]
                members.append(
                    {
                        "mention_id": mention_id,
                        "species": entity["species"],
                        "accession": resolved["accession"] if resolved else None,
                        "gene_id": resolved["gene_id"] if resolved else None,
                        "relationship": _text(raw_member["relationship"]),
                        "source_locator": member_locator,
                        "status": entity["status"],
                    }
                )
            anchor = members[0]
            edges: list[dict[str, Any]] = []
            for member in members[1:]:
                edges.append(
                    {
                        "edge_id": f"{group_id}:{anchor['mention_id']}->{member['mention_id']}",
                        "group_id": group_id,
                        "from_mention_id": anchor["mention_id"],
                        "to_mention_id": member["mention_id"],
                        "relation": "ONE_TO_MANY_ORTHOLOGY",
                        "status": "RESOLVED"
                        if anchor["status"] == "RESOLVED" and member["status"] == "RESOLVED"
                        else "REVIEW_REQUIRED",
                    }
                )
            edge_count += len(edges)
            output.append(
                {
                    "group_id": group_id,
                    "source_locator": locator,
                    "members": members,
                    "edges": edges,
                }
            )
        return output, edge_count

    def run(self) -> ProteinResolutionSummary:
        """Resolve protein mentions and write orthology evidence."""
        proteins, groups = self._load_fixture(self.fixture_path)
        reviews: list[dict[str, Any]] = []
        entities, by_mention = self._resolve_proteins(proteins, reviews)
        orthology, edge_count = self._orthology(groups, by_mention)
        self.entities_path.parent.mkdir(parents=True, exist_ok=True)
        self.entities_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "entities": entities},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.orthology_path.parent.mkdir(parents=True, exist_ok=True)
        self.orthology_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "orthology_groups": orthology},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        review_ledger = AppendOnlyJSONL(self.review_path)
        review_ledger.initialize()
        existing = {
            json.loads(line).get("review_id")
            for line in review_ledger.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for review in reviews:
            if review["review_id"] not in existing:
                review_ledger.append(review)

        resolved_count = sum(entity["status"] == "RESOLVED" for entity in entities)
        ambiguous_count = sum(entity["status"] == "AMBIGUOUS" for entity in entities)
        obsolete_count = sum(entity["status"] == "OBSOLETE_REVIEW" for entity in entities)
        report = (
            "\n".join(
                [
                    "# Protein Identifier and Orthology Resolution Report",
                    "",
                    "Species-aware accession/gene mapping preserves isoform and "
                    "obsolete ambiguity.",
                    "",
                    f"- mentions: {len(proteins)}",
                    f"- resolved: {resolved_count}",
                    f"- ambiguous: {ambiguous_count}",
                    f"- obsolete review: {obsolete_count}",
                    f"- orthology groups: {len(orthology)}",
                    f"- orthology edges: {edge_count}",
                    f"- review items: {len(reviews)}",
                    "",
                    "One-to-many orthology members remain separate nodes.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return ProteinResolutionSummary(
            mentions=len(proteins),
            resolved=resolved_count,
            ambiguous=ambiguous_count,
            obsolete_review=obsolete_count,
            orthology_groups=len(orthology),
            orthology_edges=edge_count,
            review_items=len(reviews),
            entities_path=self.entities_path,
            orthology_path=self.orthology_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
