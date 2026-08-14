"""Lockbox path firewall and development-artifact contamination scanner."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

LOCKBOX_CONFIG = Path("config/lockbox.yaml")
AUDIT_PATH = Path("reports/lockbox_audit.json")


class LockboxError(RuntimeError):
    """Base lockbox access and contamination error."""


class LockboxAccessError(LockboxError):
    """Raised when a development operation would read protected content."""


class ContaminationError(LockboxError):
    """Raised when a forbidden field or hash is detected."""


@dataclass(frozen=True)
class LockboxPolicy:
    """Validated path and contamination rules."""

    locked_root: Path
    metadata_whitelist: frozenset[str]
    forbidden_fields: tuple[str, ...]

    @classmethod
    def load(cls, root: Path, path: Path | str = LOCKBOX_CONFIG) -> LockboxPolicy:
        candidate = Path(path)
        config_path = (candidate if candidate.is_absolute() else root / candidate).resolve(strict=False)
        repository = root.resolve(strict=True)
        if config_path != repository and repository not in config_path.parents:
            raise LockboxError("lockbox config escapes repository")
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise LockboxError(f"cannot load lockbox config: {exc}") from exc
        expected = {"schema_version", "locked_root", "metadata_whitelist", "forbidden_fields"}
        if not isinstance(raw, dict) or set(raw) != expected or raw["schema_version"] != 1:
            raise LockboxError("lockbox config schema is invalid")
        locked_value = raw["locked_root"]
        whitelist = raw["metadata_whitelist"]
        forbidden = raw["forbidden_fields"]
        if (
            not isinstance(locked_value, str)
            or not isinstance(whitelist, list)
            or not whitelist
            or not all(isinstance(item, str) and item for item in whitelist)
            or not isinstance(forbidden, list)
            or not forbidden
            or not all(isinstance(item, str) and item for item in forbidden)
        ):
            raise LockboxError("lockbox config values are invalid")
        locked_root = (repository / locked_value).resolve(strict=False)
        if repository not in locked_root.parents:
            raise LockboxError("locked root escapes repository")
        return cls(locked_root, frozenset(whitelist), tuple(forbidden))


@dataclass(frozen=True)
class ContaminationFinding:
    """One forbidden hash or field finding."""

    path: str
    kind: str
    value: str


@dataclass(frozen=True)
class ContaminationReport:
    """Deterministic scan result."""

    checked_paths: tuple[str, ...]
    findings: tuple[ContaminationFinding, ...]

    @property
    def clean(self) -> bool:
        return not self.findings

    def to_mapping(self) -> dict[str, Any]:
        return {
            "checked_paths": list(self.checked_paths),
            "findings": [asdict(finding) for finding in self.findings],
            "clean": self.clean,
        }


class LockboxFirewall:
    """Separate development reads from explicitly whitelisted metadata reads."""

    def __init__(self, root: Path, policy: LockboxPolicy | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.policy = policy or LockboxPolicy.load(self.root)
        self.locked_root = self.policy.locked_root

    def _resolve(self, path: Path | str) -> Path:
        candidate = Path(path)
        resolved = (candidate if candidate.is_absolute() else self.root / candidate).resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise LockboxAccessError(f"path escapes repository: {path}")
        return resolved

    def assert_development_read_allowed(self, path: Path | str) -> Path:
        """Guard a normal development read; every locked path is denied."""
        resolved = self._resolve(path)
        if resolved == self.locked_root or self.locked_root in resolved.parents:
            raise LockboxAccessError("development reads of data/locked_test are denied")
        return resolved

    def open_development(self, path: Path | str, mode: str = "rb") -> Any:
        """Open a non-lockbox file for development-only reads."""
        if any(token in mode for token in ("w", "a", "x", "+")):
            raise LockboxAccessError("firewall open is read-only")
        return self.assert_development_read_allowed(path).open(mode)

    def read_metadata(self, path: Path | str) -> Mapping[str, Any] | str:
        """Read only one explicitly whitelisted metadata file under lockbox."""
        resolved = self._resolve(path)
        if self.locked_root not in resolved.parents:
            raise LockboxAccessError("metadata path is not under lockbox")
        relative = resolved.relative_to(self.locked_root)
        if len(relative.parts) != 1 or relative.name not in self.policy.metadata_whitelist:
            raise LockboxAccessError("metadata filename is not whitelisted")
        if not resolved.is_file():
            raise LockboxAccessError("whitelisted metadata file is missing")
        if resolved.suffix == ".json":
            try:
                value = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise LockboxAccessError(f"metadata JSON is invalid: {exc}") from exc
            if not isinstance(value, dict):
                raise LockboxAccessError("metadata JSON must be an object")
            return value
        return resolved.read_text(encoding="utf-8")

    def scan(
        self,
        paths: Sequence[Path | str],
        *,
        forbidden_hashes: Sequence[str] = (),
    ) -> ContaminationReport:
        """Scan selected development artifacts for forbidden fields and exact hashes."""
        blocked_hashes = frozenset(forbidden_hashes)
        findings: list[ContaminationFinding] = []
        checked: list[str] = []
        pattern_cache = tuple(
            (
                field,
                re.compile(r"(?<![A-Za-z0-9_])" + re.escape(field.lower()) + r"(?![A-Za-z0-9_])"),
            )
            for field in self.policy.forbidden_fields
        )
        for value in paths:
            resolved = self.assert_development_read_allowed(value)
            if not resolved.is_file():
                raise LockboxError(f"scan path is not a regular file: {value}")
            data = resolved.read_bytes()
            relative = resolved.relative_to(self.root).as_posix()
            checked.append(relative)
            digest = hashlib.sha256(data).hexdigest()
            if digest in blocked_hashes:
                findings.append(ContaminationFinding(relative, "forbidden_hash", digest))
            text = data.decode("utf-8", errors="ignore").lower()
            for field, pattern in pattern_cache:
                if pattern.search(text):
                    findings.append(ContaminationFinding(relative, "forbidden_field", field))
        return ContaminationReport(tuple(sorted(checked)), tuple(findings))

    def write_audit(self, report: Mapping[str, Any], path: Path | str = AUDIT_PATH) -> Path:
        """Write a stable JSON audit receipt inside the repository."""
        target = Path(path)
        resolved = target if target.is_absolute() else self.root / target
        resolved = resolved.resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise LockboxAccessError("audit path escapes repository")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return resolved

    def self_test(self, fixture_dir: Path) -> dict[str, Any]:
        """Run local scanner fixtures without opening the real lockbox payload."""
        blocked = False
        try:
            self.assert_development_read_allowed(self.locked_root / "payload.bin")
        except LockboxAccessError:
            blocked = True
        if not blocked:
            raise LockboxError("development lockbox read was not blocked")
        clean_path = fixture_dir / "clean.json"
        contaminated_path = fixture_dir / "contaminated.json"
        clean_report = self.scan([clean_path])
        contaminated_bytes = contaminated_path.read_bytes()
        contaminated_hash = hashlib.sha256(contaminated_bytes).hexdigest()
        contaminated_report = self.scan(
            [contaminated_path],
            forbidden_hashes=[contaminated_hash],
        )
        field_detected = any(finding.kind == "forbidden_field" for finding in contaminated_report.findings)
        hash_detected = any(finding.kind == "forbidden_hash" for finding in contaminated_report.findings)
        if not clean_report.clean or not field_detected or not hash_detected:
            raise ContaminationError("lockbox self-test fixtures did not exercise all gates")
        return {
            "blocked_development_lockbox_read": blocked,
            "metadata_whitelist_count": len(self.policy.metadata_whitelist),
            "clean_fixture": clean_report.to_mapping(),
            "contaminated_fixture": contaminated_report.to_mapping(),
            "forbidden_field_detected": field_detected,
            "forbidden_hash_detected": hash_detected,
            "locked_root_payload_opened": False,
            "passed": True,
        }
