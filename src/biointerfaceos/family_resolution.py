"""Resolve fixture-backed paper families and study identities."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from biointerfaceos.ledgers import AppendOnlyJSONL


class FamilyResolutionError(RuntimeError):
    """Raised when identity-resolution inputs violate their contract."""


@dataclass(frozen=True)
class FamilyResolutionSummary:
    """Counts emitted by one deterministic family-resolution run."""

    family_count: int
    member_rows: int
    manual_review_rows: int
    split_safe: bool
    parquet_path: Path
    report_path: Path
    review_path: Path


class _UnionFind:
    def __init__(self, members: list[str]) -> None:
        self.parent = {member: member for member in members}

    def find(self, member: str) -> str:
        parent = self.parent[member]
        if parent != member:
            self.parent[member] = self.find(parent)
        return self.parent[member]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


class FamilyResolver:
    """Build split-safe paper families from explicit identity evidence."""

    _HIGH_CONFIDENCE_RELATIONSHIPS = frozenset(
        {"preprint_of", "correction_of", "supplement_of", "dataset_for", "duplicate_of"}
    )
    _FAMILY_SCHEMA = pa.schema(
        [
            pa.field("family_id", pa.string(), nullable=False),
            pa.field("record_id", pa.string(), nullable=False),
            pa.field("record_type", pa.string(), nullable=False),
            pa.field("relationship_to_family", pa.string(), nullable=False),
            pa.field("source", pa.string(), nullable=False),
            pa.field("accession", pa.string(), nullable=True),
            pa.field("doi", pa.string(), nullable=True),
            pa.field("normalized_doi", pa.string(), nullable=True),
            pa.field("title", pa.string(), nullable=False),
            pa.field("normalized_title", pa.string(), nullable=False),
            pa.field("year", pa.int64(), nullable=False),
            pa.field("split", pa.string(), nullable=False),
            pa.field("study_key", pa.string(), nullable=False),
            pa.field("lab_key", pa.string(), nullable=False),
            pa.field("record_sha256", pa.string(), nullable=False),
            pa.field("resolution_status", pa.string(), nullable=False),
        ]
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        parquet_path: Path | None = None,
        report_path: Path | None = None,
        review_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/families/paper_family_records.json")
        self.parquet_path = parquet_path or self.root / "registry/paper_families.parquet"
        self.report_path = report_path or self.root / "reports/paper_family_dedup.md"
        self.review_path = review_path or self.root / "registry/family_manual_review.jsonl"

    @staticmethod
    def _normalize_doi(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().lower()
        normalized = re.sub(r"^https?://doi\.org/", "", normalized)
        normalized = re.sub(r"^doi:", "", normalized)
        return normalized.rstrip(".,; ")

    @staticmethod
    def _normalize_title(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise FamilyResolutionError("record title is required")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())

    @staticmethod
    def _author_surname(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower().split()[-1])

    @staticmethod
    def _record_sha(record: Mapping[str, Any]) -> str:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_fixture(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            value = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FamilyResolutionError(f"cannot load family fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {
            "schema_version",
            "records",
            "relationships",
        }:
            raise FamilyResolutionError("family fixture envelope is invalid")
        if value["schema_version"] != 1:
            raise FamilyResolutionError("family fixture schema_version must be 1")
        raw_records = value["records"]
        raw_relationships = value["relationships"]
        if not isinstance(raw_records, list) or not all(isinstance(row, Mapping) for row in raw_records):
            raise FamilyResolutionError("family fixture records are invalid")
        if not isinstance(raw_relationships, list) or not all(isinstance(row, Mapping) for row in raw_relationships):
            raise FamilyResolutionError("family fixture relationships are invalid")
        records = [dict(row) for row in raw_records]
        relationships = [dict(row) for row in raw_relationships]
        required = {
            "record_id",
            "record_type",
            "source",
            "accession",
            "doi",
            "title",
            "authors",
            "year",
            "split",
            "url",
        }
        ids: set[str] = set()
        for record in records:
            if set(record) != required:
                raise FamilyResolutionError("family record fields are invalid")
            record_id = record["record_id"]
            if not isinstance(record_id, str) or not record_id or record_id in ids:
                raise FamilyResolutionError("family record IDs must be unique non-empty strings")
            ids.add(record_id)
            if not isinstance(record["authors"], list) or not record["authors"]:
                raise FamilyResolutionError(f"record {record_id} authors are invalid")
            if not isinstance(record["year"], int) or isinstance(record["year"], bool):
                raise FamilyResolutionError(f"record {record_id} year is invalid")
            if record["split"] not in {"train", "validation"}:
                raise FamilyResolutionError(f"record {record_id} split is invalid")
        for relationship in relationships:
            if set(relationship) != {
                "relationship_id",
                "source_record_id",
                "target_record_id",
                "relationship",
                "confidence",
            }:
                raise FamilyResolutionError("family relationship fields are invalid")
            if relationship["source_record_id"] not in ids or relationship["target_record_id"] not in ids:
                raise FamilyResolutionError("family relationship references an unknown record")
            if relationship["confidence"] not in {"high", "uncertain"}:
                raise FamilyResolutionError("family relationship confidence is invalid")
        return records, relationships

    @staticmethod
    def _review_key(reason: str, left: str, right: str) -> str:
        pair = "|".join(sorted((left, right)))
        return f"{reason}:{pair}"

    def run(self) -> FamilyResolutionSummary:
        """Resolve families, write Parquet/report/review outputs, and return counts."""
        records, relationships = self._load_fixture()
        by_id = {str(record["record_id"]): record for record in records}
        union_find = _UnionFind(sorted(by_id))
        reviews: dict[str, dict[str, Any]] = {}

        def add_review(
            reason: str,
            left: str,
            right: str,
            relationship: str,
            confidence: str,
        ) -> None:
            review_id = self._review_key(reason, left, right)
            reviews[review_id] = {
                "review_id": review_id,
                "reason": reason,
                "record_ids": sorted((left, right)),
                "relationship": relationship,
                "confidence": confidence,
                "split_values": sorted({str(by_id[left]["split"]), str(by_id[right]["split"])}),
                "resolution": "MANUAL_REVIEW",
            }

        def join(left: str, right: str, reason: str, relationship: str, confidence: str) -> None:
            left_split = by_id[left]["split"]
            right_split = by_id[right]["split"]
            if left_split != right_split:
                add_review("SPLIT_BOUNDARY_CONFLICT", left, right, relationship, confidence)
                return
            union_find.union(left, right)

        for field_name in ("doi", "accession"):
            buckets: dict[str, list[str]] = defaultdict(list)
            for record in records:
                value = (
                    self._normalize_doi(record[field_name])
                    if field_name == "doi"
                    else (
                        f"{record['source']}:{str(record[field_name]).lower().strip()}"
                        if isinstance(record[field_name], str) and record[field_name].strip()
                        else None
                    )
                )
                if value is not None:
                    buckets[value].append(str(record["record_id"]))
            for key, members in buckets.items():
                for left, right in zip(members, members[1:], strict=False):
                    join(left, right, f"shared_{field_name}:{key}", "identity_match", "high")

        for relationship in relationships:
            left = str(relationship["source_record_id"])
            right = str(relationship["target_record_id"])
            relation = str(relationship["relationship"])
            confidence = str(relationship["confidence"])
            if confidence == "uncertain":
                add_review("UNCERTAIN_RELATIONSHIP", left, right, relation, confidence)
            elif relation in self._HIGH_CONFIDENCE_RELATIONSHIPS:
                join(left, right, "explicit_relationship", relation, confidence)
            else:
                add_review("UNSUPPORTED_RELATIONSHIP", left, right, relation, confidence)

        title_buckets: dict[tuple[str, int, str], list[str]] = defaultdict(list)
        for record in records:
            title_buckets[
                (
                    self._normalize_title(record["title"]),
                    int(record["year"]),
                    self._author_surname(str(record["authors"][0])),
                )
            ].append(str(record["record_id"]))
        for members in title_buckets.values():
            for left, right in zip(members, members[1:], strict=False):
                join(left, right, "title_author_year_match", "identity_match", "high")

        groups: dict[str, list[str]] = defaultdict(list)
        for record_id in sorted(by_id):
            groups[union_find.find(record_id)].append(record_id)
        ordered_groups = sorted(groups.values(), key=lambda members: members[0])
        family_by_record: dict[str, str] = {}
        for number, members in enumerate(ordered_groups, 1):
            for record_id in members:
                family_by_record[record_id] = f"FAMILY-{number:03d}"

        rows: list[dict[str, Any]] = []
        for members in ordered_groups:
            family_id = family_by_record[members[0]]
            primary = sorted(
                members,
                key=lambda record_id: (
                    str(by_id[record_id]["record_type"]) != "article",
                    record_id,
                ),
            )[0]
            primary_record = by_id[primary]
            primary_title = self._normalize_title(primary_record["title"])
            primary_author = self._author_surname(str(primary_record["authors"][0]))
            study_material = f"{primary_title}|{primary_author}|{primary_record['year']}"
            study_key = f"study:{hashlib.sha256(study_material.encode()).hexdigest()[:16]}"
            lab_material = "|".join(self._author_surname(str(author)) for author in primary_record["authors"][:3])
            lab_key = f"lab:{hashlib.sha256(lab_material.encode()).hexdigest()[:16]}"
            member_set = set(members)
            for record_id in members:
                record = by_id[record_id]
                member_relationships = [
                    str(link["relationship"])
                    for link in relationships
                    if (link["source_record_id"] == record_id and link["target_record_id"] in member_set)
                    or (link["target_record_id"] == record_id and link["source_record_id"] in member_set)
                ]
                rows.append(
                    {
                        "family_id": family_id,
                        "record_id": record_id,
                        "record_type": str(record["record_type"]),
                        "relationship_to_family": (
                            member_relationships[0]
                            if member_relationships
                            else ("primary" if record_id == primary else "associated")
                        ),
                        "source": str(record["source"]),
                        "accession": record["accession"],
                        "doi": record["doi"],
                        "normalized_doi": self._normalize_doi(record["doi"]),
                        "title": str(record["title"]),
                        "normalized_title": self._normalize_title(record["title"]),
                        "year": int(record["year"]),
                        "split": str(record["split"]),
                        "study_key": study_key,
                        "lab_key": lab_key,
                        "record_sha256": self._record_sha(record),
                        "resolution_status": "RESOLVED",
                    }
                )

        rows.sort(key=lambda row: (row["family_id"], row["record_id"]))
        split_safe = all(
            len({row["split"] for row in rows if row["family_id"] == family_id}) == 1
            for family_id in {row["family_id"] for row in rows}
        )
        if not split_safe:
            raise FamilyResolutionError("resolved family crosses train/validation split")

        self.parquet_path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(rows, schema=self._FAMILY_SCHEMA)
        pq.write_table(table, self.parquet_path, compression="zstd")
        review_ledger = AppendOnlyJSONL(self.review_path)
        review_ledger.initialize()
        existing_reviews = {
            json.loads(line).get("review_id")
            for line in review_ledger.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for review_id in sorted(reviews):
            if review_id not in existing_reviews:
                review_ledger.append(reviews[review_id])

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        family_lines = [
            f"- {family_id}: {sum(row['family_id'] == family_id for row in rows)} members"
            for family_id in sorted({row["family_id"] for row in rows})
        ]
        report = (
            "\n".join(
                [
                    "# Paper Family Deduplication Report",
                    "",
                    "Fixture-backed identity resolution; no live endpoints or locked-test payloads were accessed.",
                    "",
                    f"- resolved families: {len(ordered_groups)}",
                    f"- resolved member rows: {len(rows)}",
                    f"- manual-review records: {len(reviews)}",
                    f"- split-safe families: {split_safe}",
                    "",
                    "## Families",
                    "",
                    *family_lines,
                    "",
                    "## Manual review",
                    "",
                    "Uncertain relationships and cross-split identity collisions remain in "
                    "registry/family_manual_review.jsonl.",
                ]
            )
            + "\n"
        )
        self.report_path.write_text(report, encoding="utf-8")
        return FamilyResolutionSummary(
            family_count=len(ordered_groups),
            member_rows=len(rows),
            manual_review_rows=len(reviews),
            split_safe=split_safe,
            parquet_path=self.parquet_path,
            report_path=self.report_path,
            review_path=self.review_path,
        )
