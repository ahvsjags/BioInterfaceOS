"""Audit every repository asset before it can enter the public release scope."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any


class PublicReleaseAuditError(RuntimeError):
    """Raised when a public-release asset cannot be safely classified."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class RegistryEntry:
    """One mutually exclusive asset-classification rule."""

    asset_id: str
    include: tuple[str, ...]
    asset_class: str
    origin: str
    license_expression: str
    redistribution: str
    evidence_status: str
    policy: str


class PublicReleaseAuditWorkflow:
    """Produce an append-only, default-deny public asset inventory."""

    AUDIT_ID = "bioif-public-release-audit-v1.1.0"
    AUDITED_AT = "2026-08-12T00:00:00+00:00"
    REGISTRY_RELATIVE = "docs/release/PUBLIC_ASSET_REGISTRY.json"
    REQUIRED_FILES = (
        "LICENSE",
        "NOTICE",
        "CITATION.cff",
        "README_FIRST.md",
        "release/README.md",
        "release/public/README.md",
        "docs/release/PUBLIC_RELEASE_INVENTORY.md",
    )
    README_PATHS = (
        "README_FIRST.md",
        "release/README.md",
        "release/public/README.md",
        "docs/release/PUBLIC_RELEASE_INVENTORY.md",
    )
    REQUIRED_ENTRY_FIELDS = {
        "asset_id",
        "include",
        "asset_class",
        "origin",
        "license_expression",
        "redistribution",
        "evidence_status",
        "policy",
    }
    ALLOWED_REDISTRIBUTION = {"PUBLIC", "CONTROLLED", "EXCLUDED"}
    ALLOWED_EVIDENCE_STATUS = {
        "NOT_EVIDENCE",
        "FIXTURE_ONLY",
        "HISTORICAL_QUARANTINED",
        "SOFTWARE_REPLAY_ONLY",
        "SOURCE_METADATA_ONLY",
    }

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or (
            self.root / "reports/review_round_2/public_release_audit/v1.1.0"
        )

    def _path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise PublicReleaseAuditError(
                f"required public-release file is missing: {relative_path}"
            )
        return path

    def _tracked_paths(self) -> list[str]:
        """Use Git's index when available; never classify ignored build products."""
        try:
            result = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=self.root,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError):
            ignored = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
            paths = [
                path.relative_to(self.root).as_posix()
                for path in self.root.rglob("*")
                if path.is_file()
                and not any(part in ignored for part in path.relative_to(self.root).parts)
            ]
        else:
            paths = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
        return sorted(paths)

    def _load_registry(self) -> tuple[dict[str, Any], tuple[RegistryEntry, ...]]:
        registry_path = self._path(self.REGISTRY_RELATIVE)
        try:
            raw = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PublicReleaseAuditError("public asset registry is not valid JSON") from exc
        if not isinstance(raw, dict) or set(raw) != {
            "schema_version",
            "registry_id",
            "registry_version",
            "release_scope",
            "entries",
        }:
            raise PublicReleaseAuditError("public asset registry fields are invalid")
        if raw["schema_version"] != 1 or raw["release_scope"] != "repository_tracked_assets":
            raise PublicReleaseAuditError("public asset registry scope is invalid")
        entries_value = raw["entries"]
        if not isinstance(entries_value, list) or not entries_value:
            raise PublicReleaseAuditError("public asset registry has no entries")
        entries: list[RegistryEntry] = []
        seen_ids: set[str] = set()
        for value in entries_value:
            if not isinstance(value, dict) or set(value) != self.REQUIRED_ENTRY_FIELDS:
                raise PublicReleaseAuditError("public asset registry entry fields are invalid")
            asset_id = value["asset_id"]
            include = value["include"]
            if (
                not isinstance(asset_id, str)
                or not asset_id
                or asset_id in seen_ids
                or not isinstance(include, list)
                or not include
                or not all(isinstance(pattern, str) and pattern for pattern in include)
            ):
                raise PublicReleaseAuditError(
                    "public asset registry identifiers or globs are invalid"
                )
            redistribution = value["redistribution"]
            evidence_status = value["evidence_status"]
            if redistribution not in self.ALLOWED_REDISTRIBUTION:
                raise PublicReleaseAuditError("public asset registry redistribution is invalid")
            if evidence_status not in self.ALLOWED_EVIDENCE_STATUS:
                raise PublicReleaseAuditError("public asset registry evidence status is invalid")
            required_values = self.REQUIRED_ENTRY_FIELDS - {"include"}
            if not all(isinstance(value[key], str) and value[key] for key in required_values):
                raise PublicReleaseAuditError("public asset registry has an empty declaration")
            if redistribution == "PUBLIC" and value["license_expression"] == "NOASSERTION":
                raise PublicReleaseAuditError("public assets cannot use NOASSERTION")
            policy = value["policy"].lower()
            needs_exclusion = "excluded" not in policy and "controlled" not in policy
            if redistribution != "PUBLIC" and needs_exclusion:
                raise PublicReleaseAuditError("non-public assets need an explicit exclusion policy")
            seen_ids.add(asset_id)
            entries.append(
                RegistryEntry(
                    asset_id=asset_id,
                    include=tuple(include),
                    asset_class=value["asset_class"],
                    origin=value["origin"],
                    license_expression=value["license_expression"],
                    redistribution=redistribution,
                    evidence_status=evidence_status,
                    policy=value["policy"],
                )
            )
        return raw, tuple(entries)

    @staticmethod
    def _matches(relative_path: str, entry: RegistryEntry) -> bool:
        return any(fnmatchcase(relative_path, pattern) for pattern in entry.include)

    def _inventory(
        self, entries: tuple[RegistryEntry, ...]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        paths = self._tracked_paths()
        inventory: list[dict[str, Any]] = []
        findings: list[str] = []
        for entry in entries:
            if not any(self._matches(path, entry) for path in paths):
                findings.append(f"registry entry does not match a tracked asset: {entry.asset_id}")
        for relative_path in paths:
            matches = [entry for entry in entries if self._matches(relative_path, entry)]
            if not matches:
                findings.append(f"unregistered tracked asset: {relative_path}")
                continue
            if len(matches) != 1:
                findings.append(f"ambiguous public asset classification: {relative_path}")
                continue
            entry = matches[0]
            path = self._path(relative_path)
            inventory.append(
                {
                    "path": relative_path,
                    "sha256": _sha256(path),
                    "asset_id": entry.asset_id,
                    "asset_class": entry.asset_class,
                    "origin": entry.origin,
                    "license_expression": entry.license_expression,
                    "redistribution": entry.redistribution,
                    "evidence_status": entry.evidence_status,
                    "policy": entry.policy,
                }
            )
        return inventory, findings

    def _readme_findings(self) -> list[str]:
        findings: list[str] = []
        link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        code_pattern = re.compile(r"`([^`]+)`")
        for relative_path in self.README_PATHS:
            path = self._path(relative_path)
            text = path.read_text(encoding="utf-8")
            for destination in link_pattern.findall(text):
                target = destination.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (path.parent / target).resolve(strict=False)
                if not resolved.is_relative_to(self.root) or not resolved.exists():
                    findings.append(
                        f"README path does not resolve: {relative_path} -> {destination}"
                    )
            for token in code_pattern.findall(text):
                candidate = token.strip()
                looks_like_path = (
                    "/" in candidate
                    or candidate.startswith(".")
                    or bool(re.search(r"\.(?:md|json|yaml|yml|toml|py|sh|tsv|txt)$", candidate))
                )
                if (
                    not looks_like_path
                    or any(character.isspace() for character in candidate)
                    or candidate.startswith("http")
                ):
                    continue
                candidates = (
                    (self.root / candidate).resolve(strict=False),
                    (path.parent / candidate).resolve(strict=False),
                )
                if not any(
                    resolved.is_relative_to(self.root) and resolved.exists()
                    for resolved in candidates
                ):
                    findings.append(f"README path does not resolve: {relative_path} -> {candidate}")
        public_readme = self._path("release/public/README.md").read_text(encoding="utf-8").lower()
        required_language = (
            "software replay only",
            "not scientific replication",
            "not empirical validation",
        )
        for phrase in required_language:
            if phrase not in public_readme:
                findings.append(f"release/public README lacks required evidence boundary: {phrase}")
        return findings

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise PublicReleaseAuditError("T117 requires --strict")
        if self.output_root.exists():
            raise PublicReleaseAuditError("public-release audit already executed")
        for relative_path in self.REQUIRED_FILES:
            self._path(relative_path)
        registry, entries = self._load_registry()
        inventory, findings = self._inventory(entries)
        findings.extend(self._readme_findings())
        status = "PASS_PUBLIC_RELEASE_AUDIT" if not findings else "BLOCKED_PUBLIC_RELEASE_AUDIT"
        by_redistribution = {
            state: sum(item["redistribution"] == state for item in inventory)
            for state in sorted(self.ALLOWED_REDISTRIBUTION)
        }
        inventory_payload = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "registry_id": registry["registry_id"],
            "registry_version": registry["registry_version"],
            "assets": inventory,
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": status,
            "asset_count": len(inventory),
            "redistribution_counts": by_redistribution,
            "blocking_findings": findings,
            "historical_fixture_bundle_publicly_released": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        inventory_path = self.output_root / "asset_inventory.json"
        report_path = self.output_root / "public_release_audit.json"
        inventory_path.write_bytes(_canonical(inventory_payload))
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": status,
            "inventory_sha256": _sha256(inventory_path),
            "report_sha256": _sha256(report_path),
            "historical_fixture_bundle_publicly_released": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "audit_receipt.json"
        receipt_path.write_bytes(_canonical(receipt))
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return report

    def verify(self) -> dict[str, Any]:
        inventory_path = self.output_root / "asset_inventory.json"
        report_path = self.output_root / "public_release_audit.json"
        receipt_path = self.output_root / "audit_receipt.json"
        if not inventory_path.is_file() or not report_path.is_file() or not receipt_path.is_file():
            raise PublicReleaseAuditError("public-release audit outputs are missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PublicReleaseAuditError("public-release audit outputs are invalid") from exc
        if not isinstance(receipt, dict) or not isinstance(report, dict):
            raise PublicReleaseAuditError("public-release audit outputs must be objects")
        if (
            receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != report.get("status")
            or receipt.get("inventory_sha256") != _sha256(inventory_path)
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("historical_fixture_bundle_publicly_released") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise PublicReleaseAuditError("public-release audit receipt is invalid")
        return report
