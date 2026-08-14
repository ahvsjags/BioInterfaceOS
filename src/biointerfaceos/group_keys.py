"""Build deterministic leakage-safe group keys from frozen identity metadata."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class GroupKeysError(RuntimeError):
    """Raised when group-key provenance or collision validation fails."""


@dataclass(frozen=True)
class GroupKeysSummary:
    """Summary of one canonical group-key build."""

    rows: int
    unique_study: int
    unique_paper_families: int
    unique_projects: int
    collisions: int
    review_rows: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GroupKeysError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GroupKeysError(f"{label} must be a non-empty string")
    return value.strip()


def _normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


class GroupKeysWorkflow:
    """Generate group keys without using outcomes or freezing splits."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/splits/group_keys_fixture.json"
        self.output_root = output_root or self.root / "reports/splits/group_keys"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GroupKeysError(f"cannot load group-key fixture: {exc}") from exc
        data = _mapping(fixture, "group-key fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "group_keys":
            raise GroupKeysError("group-key fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not data["inputs"]:
            raise GroupKeysError("group-key fixture has no inputs")
        if not isinstance(data.get("records"), list) or not data["records"]:
            raise GroupKeysError("group-key fixture has no records")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> None:
        required = {
            "T030 family evidence",
            "T041 material registry",
            "T043 protocol registry",
            "T047 silver manifest",
            "T057 PRIDE QC",
        }
        labels: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "group-key input")
            label = _string(row.get("label"), "input label")
            relative = _string(row.get("path"), "input path")
            path = (self.root / relative).resolve(strict=True)
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise GroupKeysError("group-key input escaped repository") from exc
            expected = _string(row.get("sha256"), "input checksum")
            if _sha256(path.read_bytes()) != expected:
                raise GroupKeysError(f"group-key input checksum differs: {label}")
            labels.add(label)
        if labels != required:
            raise GroupKeysError("group-key inputs do not match T030/T041/T043/T047/T057 contract")

    @staticmethod
    def _keys(row: Mapping[str, Any]) -> dict[str, str]:
        study_id = _string(row.get("study_id"), "study ID")
        project_id = _string(row.get("project_id"), "project ID")
        family_id = _string(row.get("paper_family_id"), "paper family ID")
        lab_value = row.get("lab_id")
        lab_key = (
            f"LAB:{_normalize(_string(lab_value, 'lab ID'))}"
            if lab_value is not None
            else f"LAB_UNKNOWN:{_normalize(family_id or project_id)}"
        )
        material_entity = row.get("material_entity_id")
        if material_entity is not None:
            material_key = f"MATERIAL:{_normalize(_string(material_entity, 'material entity'))}"
        else:
            raw_material = _string(row.get("material_raw"), "raw material")
            material_key = f"MATERIAL_UNKNOWN:{_normalize(raw_material)}"
        bioenvironment = row.get("bioenvironment_id")
        bio_key = (
            f"BIOENV:{_normalize(_string(bioenvironment, 'bioenvironment ID'))}"
            if bioenvironment is not None
            else "BIOENV_UNKNOWN"
        )
        protocol = _string(row.get("protocol_id"), "protocol ID")
        date = row.get("date")
        date_key = f"DATE:{_string(date, 'date')}" if date is not None else "DATE_UNKNOWN"
        return {
            "study_group_key": f"STUDY:{_normalize(study_id)}",
            "project_group_key": f"PROJECT:{_normalize(project_id)}",
            "paper_family_group_key": f"PAPER_FAMILY:{_normalize(family_id)}",
            "lab_group_key": lab_key,
            "material_group_key": material_key,
            "bioenvironment_group_key": bio_key,
            "protocol_group_key": f"PROTOCOL:{_normalize(protocol)}",
            "date_group_key": date_key,
        }

    @staticmethod
    def _collision_audit(
        rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        collisions: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []
        for field, reason in (
            ("paper_family_group_key", "paper_family_crosses_split"),
            ("project_group_key", "project_crosses_split"),
        ):
            by_key: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                by_key.setdefault(row[field], []).append(row)
            for key, grouped in sorted(by_key.items()):
                labels = sorted({_string(row.get("split_label"), "split label") for row in grouped})
                if len(labels) > 1:
                    record_ids = sorted(row["record_id"] for row in grouped)
                    collision = {
                        "collision_type": reason,
                        "group_key": key,
                        "split_labels": labels,
                        "record_ids": record_ids,
                        "resolution": "review_and_keep_group_intact",
                    }
                    collisions.append(collision)
                    reviews.append(
                        {
                            "review_id": f"REVIEW-{len(reviews) + 1:03d}",
                            "reason": reason,
                            "group_key": key,
                            "record_ids": record_ids,
                            "decision": "RETAIN_BROAD_GROUP",
                        }
                    )
        key_to_identity: dict[tuple[str, str], set[str]] = {}
        for row in rows:
            for field in (
                "study_group_key",
                "project_group_key",
                "paper_family_group_key",
                "lab_group_key",
                "material_group_key",
                "bioenvironment_group_key",
                "protocol_group_key",
                "date_group_key",
            ):
                key_to_identity.setdefault((field, row[field]), set()).add(row["record_id"])
        duplicate_keys = [
            {"field": field, "group_key": key, "record_ids": sorted(record_ids)}
            for (field, key), record_ids in sorted(key_to_identity.items())
            if field == "study_group_key" and len(record_ids) > 1
        ]
        if duplicate_keys:
            raise GroupKeysError("study group key collision detected")
        return collisions, reviews

    def run(self, *, fixture: bool = True) -> GroupKeysSummary:
        """Build canonical group keys and collision/review outputs."""
        if not fixture:
            raise GroupKeysError("--fixture is required for group-key build")
        data = self._load_fixture()
        self._verify_inputs(data)
        rows: list[dict[str, Any]] = []
        seen_records: set[str] = set()
        for value in data["records"]:
            record = _mapping(value, "group-key record")
            record_id = _string(record.get("record_id"), "record ID")
            if record_id in seen_records:
                raise GroupKeysError(f"duplicate record ID: {record_id}")
            seen_records.add(record_id)
            keys = self._keys(record)
            row = {
                "record_id": record_id,
                "study_id": _string(record.get("study_id"), "study ID"),
                "project_id": _string(record.get("project_id"), "project ID"),
                "paper_family_id": _string(record.get("paper_family_id"), "paper family ID"),
                "lab_id": record.get("lab_id"),
                "material_entity_id": record.get("material_entity_id"),
                "material_raw": _string(record.get("material_raw"), "raw material"),
                "bioenvironment_id": record.get("bioenvironment_id"),
                "protocol_id": _string(record.get("protocol_id"), "protocol ID"),
                "date": record.get("date"),
                "split_label": _string(record.get("split_label"), "split label"),
                "evidence_locator": _string(record.get("evidence_locator"), "evidence locator"),
                **keys,
            }
            rows.append(row)
        collisions, reviews = self._collision_audit(rows)
        raw_payloads = {
            "groups": {"schema_version": 1, "rows": rows, "split_frozen": False},
            "collisions": {"schema_version": 1, "collisions": collisions},
            "reviews": {"schema_version": 1, "append_only": True, "entries": reviews},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "groups": self.output_root / "group_keys.json",
            "collisions": self.output_root / "collision_audit.json",
            "reviews": self.output_root / "review_queue.json",
            "receipt": self.output_root / "processing_receipt.json",
            "log": self.output_root / "processing_log.json",
            "manifest": self.output_root / "processing_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "fixture": True,
            "rows": len(rows),
            "unique_study": len({row["study_group_key"] for row in rows}),
            "unique_paper_families": len({row["paper_family_group_key"] for row in rows}),
            "unique_projects": len({row["project_group_key"] for row in rows}),
            "collisions": len(collisions),
            "review_rows": len(reviews),
            "unknown_lab_rows": sum(row["lab_id"] is None for row in rows),
            "outcome_leakage": False,
            "split_frozen": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "identity_inputs_verified", "rows": len(rows)},
                {"event": "canonical_keys_built", "group_dimensions": 8},
                {"event": "cross_split_collisions_reviewed", "collisions": len(collisions)},
                {"event": "split_freeze_blocked", "enabled": False},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "rows": len(rows),
            "collisions": len(collisions),
            "review_rows": len(reviews),
            "split_frozen": False,
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
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
                raise GroupKeysError("existing group-key receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise GroupKeysError(f"existing group-key artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return GroupKeysSummary(
            rows=len(rows),
            unique_study=len({row["study_group_key"] for row in rows}),
            unique_paper_families=len({row["paper_family_group_key"] for row in rows}),
            unique_projects=len({row["project_group_key"] for row in rows}),
            collisions=len(collisions),
            review_rows=len(reviews),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
