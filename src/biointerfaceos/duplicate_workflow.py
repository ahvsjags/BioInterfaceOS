"""Detect exact, composition, structure, and semantic material duplicates."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DuplicateDetectionError(RuntimeError):
    """Raised when duplicate provenance or threshold validation fails."""


@dataclass(frozen=True)
class DuplicateDetectionSummary:
    """Summary of one duplicate-detection run."""

    items: int
    edges: int
    clusters: int
    exact_edges: int
    composition_edges: int
    structure_edges: int
    text_edges: int
    review_edges: int
    cross_split_duplicates: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DuplicateDetectionError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DuplicateDetectionError(f"{label} must be a non-empty string")
    return value.strip()


class DuplicateDetectionWorkflow:
    """Build conservative duplicate edges without split-label threshold tuning."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/splits/duplicate_fixture.json")
        self.output_root = output_root or self.root / "reports/splits/duplicates"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DuplicateDetectionError(f"cannot load duplicate fixture: {exc}") from exc
        data = _mapping(fixture, "duplicate fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "duplicate_detection":
            raise DuplicateDetectionError("duplicate fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not data["inputs"]:
            raise DuplicateDetectionError("duplicate fixture has no inputs")
        if not isinstance(data.get("thresholds"), dict) or not isinstance(data.get("items"), list):
            raise DuplicateDetectionError("duplicate fixture thresholds/items are invalid")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> None:
        required = {"T041 material registry", "T063 group keys"}
        labels: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "duplicate input")
            label = _string(row.get("label"), "input label")
            relative = _string(row.get("path"), "input path")
            path = (self.root / relative).resolve(strict=True)
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise DuplicateDetectionError("duplicate input escaped repository") from exc
            expected = _string(row.get("sha256"), "input checksum")
            if _sha256(path.read_bytes()) != expected:
                raise DuplicateDetectionError(f"duplicate input checksum differs: {label}")
            labels.add(label)
        if labels != required:
            raise DuplicateDetectionError("duplicate inputs do not match T041/T063 contract")

    @staticmethod
    def _jaccard(left: str, right: str) -> float:
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        if not left_tokens and not right_tokens:
            return 1.0
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    @staticmethod
    def _composition_l1(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
        keys = set(left) | set(right)
        return sum(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) for key in keys)

    @staticmethod
    def _validate_item(value: Any) -> dict[str, Any]:
        item = _mapping(value, "duplicate item")
        for key in (
            "item_id",
            "normalized_text",
            "structure",
            "group_key",
            "split_label",
            "evidence_locator",
        ):
            _string(item.get(key), key)
        composition = item.get("composition")
        if not isinstance(composition, dict) or not composition:
            raise DuplicateDetectionError("duplicate item composition is invalid")
        return item

    def run(self, *, fixture: bool = True) -> DuplicateDetectionSummary:
        """Detect duplicate edges and retain ambiguous review candidates."""
        if not fixture:
            raise DuplicateDetectionError("--fixture is required for duplicate detection")
        data = self._load_fixture()
        self._verify_inputs(data)
        thresholds = _mapping(data["thresholds"], "thresholds")
        threshold_version = _string(thresholds.get("threshold_version"), "threshold version")
        composition_value = thresholds.get("composition_l1_max")
        text_value = thresholds.get("text_jaccard_min")
        if isinstance(composition_value, bool) or not isinstance(composition_value, int | float):
            raise DuplicateDetectionError("composition threshold must be numeric")
        if isinstance(text_value, bool) or not isinstance(text_value, int | float):
            raise DuplicateDetectionError("text threshold must be numeric")
        composition_threshold = float(composition_value)
        text_threshold = float(text_value)
        items = [self._validate_item(value) for value in data["items"]]
        by_id: dict[str, dict[str, Any]] = {}
        for item in items:
            item_id = item["item_id"]
            if item_id in by_id:
                raise DuplicateDetectionError(f"duplicate item ID: {item_id}")
            by_id[item_id] = item
        edges: list[dict[str, Any]] = []
        reviews: list[dict[str, Any]] = []
        for left_index, left in enumerate(items):
            for right in items[left_index + 1 :]:
                left_id = left["item_id"]
                right_id = right["item_id"]
                text_similarity = round(self._jaccard(left["normalized_text"], right["normalized_text"]), 8)
                composition_distance = round(self._composition_l1(left["composition"], right["composition"]), 8)
                method: str | None = None
                score: float | None = None
                if left["normalized_text"] == right["normalized_text"]:
                    method = "exact"
                    score = 1.0
                elif composition_distance <= composition_threshold:
                    method = "composition"
                    score = composition_distance
                elif left["structure"] == right["structure"]:
                    method = "structure"
                    score = 1.0
                elif text_similarity >= text_threshold:
                    method = "text"
                    score = text_similarity
                elif text_similarity >= 0.4:
                    reviews.append(
                        {
                            "review_id": f"REVIEW-{len(reviews) + 1:03d}",
                            "item_ids": [left_id, right_id],
                            "reason": "semantic_neighbor_below_frozen_threshold",
                            "text_jaccard": text_similarity,
                            "threshold_version": threshold_version,
                            "split_labels": sorted({left["split_label"], right["split_label"]}),
                        }
                    )
                if method is not None:
                    edges.append(
                        {
                            "edge_id": f"EDGE-{len(edges) + 1:03d}",
                            "item_ids": [left_id, right_id],
                            "method": method,
                            "score": score,
                            "text_jaccard": text_similarity,
                            "composition_l1": composition_distance,
                            "threshold_version": threshold_version,
                            "split_labels": sorted({left["split_label"], right["split_label"]}),
                            "status": "DUPLICATE_CANDIDATE",
                        }
                    )
        cross_split = [
            {
                "edge_id": edge["edge_id"],
                "item_ids": edge["item_ids"],
                "method": edge["method"],
                "split_labels": edge["split_labels"],
                "status": "BLOCK_SPLIT_FREEZE",
            }
            for edge in edges
            if len(edge["split_labels"]) > 1
        ]
        parent: dict[str, str] = {item["item_id"]: item["item_id"] for item in items}

        def find(item_id: str) -> str:
            while parent[item_id] != item_id:
                parent[item_id] = parent[parent[item_id]]
                item_id = parent[item_id]
            return item_id

        for edge in edges:
            first, second = edge["item_ids"]
            first_root = find(first)
            second_root = find(second)
            if first_root != second_root:
                parent[second_root] = first_root
        clusters_by_root: dict[str, list[str]] = {}
        for item in items:
            clusters_by_root.setdefault(find(item["item_id"]), []).append(item["item_id"])
        clusters = [
            {
                "cluster_id": f"DUP-{index:03d}",
                "item_ids": sorted(member_ids),
                "methods": sorted({edge["method"] for edge in edges if set(edge["item_ids"]) <= set(member_ids)}),
                "cluster_status": "REVIEW_CROSS_SPLIT"
                if any(set(edge["item_ids"]) <= set(member_ids) and len(edge["split_labels"]) > 1 for edge in edges)
                else "SAFE_WITHIN_SPLIT",
            }
            for index, member_ids in enumerate(sorted(clusters_by_root.values()), start=1)
        ]
        raw_payloads = {
            "edges": {"schema_version": 1, "thresholds": thresholds, "edges": edges},
            "clusters": {"schema_version": 1, "clusters": clusters},
            "reviews": {"schema_version": 1, "append_only": True, "entries": reviews},
            "cross_split": {"schema_version": 1, "duplicates": cross_split},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "edges": self.output_root / "duplicate_edges.json",
            "clusters": self.output_root / "duplicate_clusters.json",
            "reviews": self.output_root / "review_queue.json",
            "cross_split": self.output_root / "cross_split_audit.json",
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
        method_counts = {
            method: sum(edge["method"] == method for edge in edges)
            for method in ("exact", "composition", "structure", "text")
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "fixture": True,
            "items": len(items),
            "edges": len(edges),
            "clusters": len(clusters),
            "method_counts": method_counts,
            "review_edges": len(reviews),
            "cross_split_duplicates": len(cross_split),
            "threshold_version": threshold_version,
            "thresholds_tuned_on_split_labels": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T041_T063_inputs_verified", "items": len(items)},
                {"event": "frozen_thresholds_applied", "threshold_version": threshold_version},
                {"event": "duplicate_edges_detected", "edges": len(edges)},
                {"event": "cross_split_audit_completed", "duplicates": len(cross_split)},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "items": len(items),
            "edges": len(edges),
            "clusters": len(clusters),
            "review_edges": len(reviews),
            "cross_split_duplicates": len(cross_split),
            "thresholds_tuned_on_split_labels": False,
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
                raise DuplicateDetectionError("existing duplicate receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise DuplicateDetectionError(f"existing duplicate artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return DuplicateDetectionSummary(
            items=len(items),
            edges=len(edges),
            clusters=len(clusters),
            exact_edges=method_counts["exact"],
            composition_edges=method_counts["composition"],
            structure_edges=method_counts["structure"],
            text_edges=method_counts["text"],
            review_edges=len(reviews),
            cross_split_duplicates=len(cross_split),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
