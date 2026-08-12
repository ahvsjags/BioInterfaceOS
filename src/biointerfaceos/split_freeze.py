"""Freeze a leakage-safe development train/validation manifest."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


class SplitFreezeError(RuntimeError):
    """Raised when development split rules or leakage gates fail."""


@dataclass(frozen=True)
class SplitFreezeSummary:
    """Summary of one development split freeze."""

    candidates: int
    train: int
    validation: int
    excluded: int
    groups: int
    blacklisted_features: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SplitFreezeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SplitFreezeError(f"{label} must be a non-empty string")
    return value.strip()


class SplitFreezeWorkflow:
    """Apply fixed date/group/duplicate rules without reading outcomes."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/splits/split_fixture.json"
        self.output_root = output_root or self.root / "reports/splits/frozen_dev"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SplitFreezeError(f"cannot load split fixture: {exc}") from exc
        data = _mapping(fixture, "split fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "freeze_dev":
            raise SplitFreezeError("split fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("candidates"), list):
            raise SplitFreezeError("split fixture inputs/candidates are invalid")
        if not isinstance(data.get("rules"), dict) or not isinstance(
            data.get("feature_blacklist"), list
        ):
            raise SplitFreezeError("split fixture rules/blacklist are invalid")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> None:
        required = {
            "T063 group keys",
            "T064 cross-split audit",
            "T015 lockbox policy",
            "T047 Silver manifest",
        }
        labels: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "split input")
            label = _string(row.get("label"), "input label")
            relative = _string(row.get("path"), "input path")
            path = (self.root / relative).resolve(strict=True)
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise SplitFreezeError("split input escaped repository") from exc
            expected = _string(row.get("sha256"), "input checksum")
            if _sha256(path.read_bytes()) != expected:
                raise SplitFreezeError(f"split input checksum differs: {label}")
            labels.add(label)
        if labels != required:
            raise SplitFreezeError("split inputs do not match T015/T063/T064/T047 contract")

    @staticmethod
    def _parse_date(value: Any, label: str) -> date:
        try:
            return date.fromisoformat(_string(value, label))
        except ValueError as exc:
            raise SplitFreezeError(f"{label} must be ISO date") from exc

    @staticmethod
    def _validate_blacklist(features: list[Any]) -> list[str]:
        values = [_string(value, "blacklisted feature") for value in features]
        if len(values) != len(set(values)):
            raise SplitFreezeError("feature blacklist contains duplicates")
        return values

    def run(self, *, fixture: bool = True) -> SplitFreezeSummary:
        """Freeze train/validation assignment and exclusion reasons."""
        if not fixture:
            raise SplitFreezeError("--fixture is required for split freeze")
        data = self._load_fixture()
        self._verify_inputs(data)
        rules = _mapping(data["rules"], "split rules")
        train_latest = self._parse_date(rules.get("train_latest_date"), "train latest date")
        validation_start = self._parse_date(
            rules.get("validation_start_date"), "validation start date"
        )
        validation_end = self._parse_date(rules.get("validation_end_date"), "validation end date")
        blacklist = self._validate_blacklist(data["feature_blacklist"])
        if train_latest >= validation_start or validation_start > validation_end:
            raise SplitFreezeError("split date rules overlap or are reversed")
        excluded: list[dict[str, Any]] = []
        assigned: list[dict[str, Any]] = []
        seen_groups: dict[tuple[str, str], str] = {}
        seen_clusters: dict[str, str] = {}
        for value in data["candidates"]:
            candidate = _mapping(value, "split candidate")
            record_id = _string(candidate.get("record_id"), "record ID")
            study_id = _string(candidate.get("study_id"), "study ID")
            evidence = _string(candidate.get("evidence_locator"), "evidence locator")
            date_value = candidate.get("date")
            if date_value is None:
                excluded.append(
                    {
                        "record_id": record_id,
                        "study_id": study_id,
                        "reason": "DATE_MISSING",
                        "evidence_locator": evidence,
                    }
                )
                continue
            observed_date = self._parse_date(date_value, "candidate date")
            group_keys = {
                field: _string(candidate.get(field), field)
                for field in (
                    "paper_family_group_key",
                    "project_group_key",
                    "material_group_key",
                    "bioenvironment_group_key",
                    "duplicate_cluster_id",
                )
            }
            split_label = (
                "train"
                if observed_date <= train_latest
                else "validation"
                if validation_start <= observed_date <= validation_end
                else "excluded"
            )
            if split_label == "excluded":
                reason = "DATE_AFTER_VALIDATION_WINDOW"
                excluded.append(
                    {
                        "record_id": record_id,
                        "study_id": study_id,
                        "date": date_value,
                        "reason": reason,
                        "evidence_locator": evidence,
                    }
                )
                continue
            conflict = next(
                (
                    (field, group_keys[field], seen_groups[(field, group_keys[field])])
                    for field in (
                        "paper_family_group_key",
                        "project_group_key",
                        "material_group_key",
                        "bioenvironment_group_key",
                    )
                    if (field, group_keys[field]) in seen_groups
                    and seen_groups[(field, group_keys[field])] != split_label
                ),
                None,
            )
            if conflict is not None:
                field, key, previous_split = conflict
                excluded.append(
                    {
                        "record_id": record_id,
                        "study_id": study_id,
                        "date": date_value,
                        "reason": "GROUP_CROSSES_SPLIT",
                        "group_field": field,
                        "group_key": key,
                        "previous_split": previous_split,
                        "evidence_locator": evidence,
                    }
                )
                continue
            cluster = group_keys["duplicate_cluster_id"]
            previous_cluster_split = seen_clusters.get(cluster)
            if previous_cluster_split is not None and previous_cluster_split != split_label:
                excluded.append(
                    {
                        "record_id": record_id,
                        "study_id": study_id,
                        "date": date_value,
                        "reason": "DUPLICATE_CLUSTER_CROSSES_SPLIT",
                        "duplicate_cluster_id": cluster,
                        "evidence_locator": evidence,
                    }
                )
                continue
            for field in (
                "paper_family_group_key",
                "project_group_key",
                "material_group_key",
                "bioenvironment_group_key",
            ):
                seen_groups[(field, group_keys[field])] = split_label
            seen_clusters[cluster] = split_label
            assigned.append(
                {
                    "record_id": record_id,
                    "study_id": study_id,
                    "split": split_label,
                    "date": date_value,
                    "paper_family_group_key": group_keys["paper_family_group_key"],
                    "project_group_key": group_keys["project_group_key"],
                    "material_group_key": group_keys["material_group_key"],
                    "bioenvironment_group_key": group_keys["bioenvironment_group_key"],
                    "duplicate_cluster_id": cluster,
                    "evidence_locator": evidence,
                }
            )
        if (
            not assigned
            or not any(row["split"] == "train" for row in assigned)
            or not any(row["split"] == "validation" for row in assigned)
        ):
            raise SplitFreezeError("split freeze has no train or validation rows")
        for row in assigned:
            row["group_key_hash"] = _sha256(
                _canonical(
                    {
                        key: row[key]
                        for key in (
                            "paper_family_group_key",
                            "project_group_key",
                            "material_group_key",
                            "bioenvironment_group_key",
                            "duplicate_cluster_id",
                        )
                    }
                )
            )
        leakage = {
            "schema_version": 1,
            "status": "PASSED",
            "outcome_values_used": False,
            "identity_features_blacklisted": True,
            "blacklisted_features": blacklist,
            "lockbox_accessed": False,
            "paper_family_project_duplicate_containment": True,
            "cross_split_duplicates": 0,
            "split_frozen": True,
        }
        raw_payloads = {
            "splits": {
                "schema_version": 1,
                "status": "FROZEN_DEV",
                "rows": assigned,
                "date_rules": rules,
            },
            "blacklist": {
                "schema_version": 1,
                "version": _string(rules.get("feature_blacklist_version"), "blacklist version"),
                "features": blacklist,
            },
            "excluded": {"schema_version": 1, "append_only": True, "entries": excluded},
            "leakage": leakage,
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "splits": self.output_root / "split_manifest.json",
            "blacklist": self.output_root / "feature_blacklist.json",
            "excluded": self.output_root / "exclusion_ledger.json",
            "leakage": self.output_root / "leakage_audit.json",
            "receipt": self.output_root / "freeze_receipt.json",
            "log": self.output_root / "freeze_log.json",
            "manifest": self.output_root / "freeze_manifest.json",
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
            "status": "FROZEN_DEV",
            "fixture": True,
            "candidates": len(data["candidates"]),
            "train": sum(row["split"] == "train" for row in assigned),
            "validation": sum(row["split"] == "validation" for row in assigned),
            "excluded": len(excluded),
            "groups": len({row["group_key_hash"] for row in assigned}),
            "blacklisted_features": len(blacklist),
            "outcome_values_used": False,
            "lockbox_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T063_T064_T015_inputs_verified", "candidates": len(data["candidates"])},
                {
                    "event": "date_rule_applied",
                    "train_latest": str(train_latest),
                    "validation_window": [str(validation_start), str(validation_end)],
                },
                {"event": "group_duplicate_containment_passed", "assigned": len(assigned)},
                {"event": "feature_blacklist_frozen", "count": len(blacklist)},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "FROZEN_DEV",
            "resume_supported": True,
            "resume_key": resume_key,
            "train": receipt["train"],
            "validation": receipt["validation"],
            "excluded": receipt["excluded"],
            "split_hash": _sha256(payload_bytes["splits"]),
            "feature_blacklist_hash": _sha256(payload_bytes["blacklist"]),
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
                raise SplitFreezeError("existing split freeze receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise SplitFreezeError(f"existing split freeze artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return SplitFreezeSummary(
            candidates=len(data["candidates"]),
            train=receipt["train"],
            validation=receipt["validation"],
            excluded=receipt["excluded"],
            groups=receipt["groups"],
            blacklisted_features=len(blacklist),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
