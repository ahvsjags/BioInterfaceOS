"""Deterministic storage accounting and quota safeguards."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

DEFAULT_CONFIG_PATH = Path("config/storage.yaml")
EXCLUDED_DIRECTORIES = frozenset({".git", ".venv", "__pycache__"})


class StorageError(Exception):
    """Base class for storage configuration and guard errors."""


class StorageConfigError(StorageError):
    """Raised when the storage configuration is invalid."""


class OutsideStorageRootError(StorageError):
    """Raised when a path is outside all declared storage roots."""


class BudgetExceededError(StorageError):
    """Raised when a proposed write would exceed the storage budget."""


class RawDataDeletionError(StorageError):
    """Raised when deletion of raw data is requested."""


def _contained(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


@dataclass(frozen=True)
class StorageConfig:
    """Validated repository-local storage configuration."""

    root: Path
    budget_bytes: int
    roots: tuple[Path, ...]

    @classmethod
    def from_yaml(cls, root: Path, path: Path | str = DEFAULT_CONFIG_PATH) -> StorageConfig:
        """Load a storage configuration and enforce repository containment."""
        repository = root.resolve(strict=True)
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = repository / config_path
        config_path = config_path.resolve(strict=True)
        if not _contained(config_path, repository):
            raise StorageConfigError(f"configuration is outside repository: {config_path}")
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise StorageConfigError(f"cannot read storage configuration: {exc}") from exc
        if not isinstance(raw, dict):
            raise StorageConfigError("storage configuration must be a mapping")
        budget = raw.get("budget_bytes")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
            raise StorageConfigError("budget_bytes must be a non-negative integer")
        configured_roots = raw.get("roots")
        if not isinstance(configured_roots, list) or not configured_roots:
            raise StorageConfigError("roots must be a non-empty list")
        roots: list[Path] = []
        for value in configured_roots:
            if not isinstance(value, str) or not value:
                raise StorageConfigError("each storage root must be a non-empty string")
            candidate = Path(value)
            if candidate.is_absolute():
                raise StorageConfigError(f"storage root must be repository-relative: {value}")
            resolved = (repository / candidate).resolve(strict=False)
            if not _contained(resolved, repository):
                raise StorageConfigError(f"storage root is outside repository: {value}")
            if resolved in roots:
                raise StorageConfigError(f"duplicate storage root: {value}")
            roots.append(resolved)
        return cls(root=repository, budget_bytes=budget, roots=tuple(roots))


@dataclass(frozen=True)
class RootUsage:
    """Usage totals for one declared root."""

    root: str
    bytes: int
    files: int


@dataclass(frozen=True)
class ManifestEntry:
    """Content identity for one accounted file."""

    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class DuplicateGroup:
    """Files sharing identical SHA-256 content."""

    sha256: str
    bytes: int
    paths: tuple[str, ...]


@dataclass(frozen=True)
class StorageAudit:
    """Deterministic storage audit result."""

    budget_bytes: int
    total_bytes: int
    total_files: int
    within_budget: bool
    roots: tuple[RootUsage, ...]
    manifest: tuple[ManifestEntry, ...]
    manifest_sha256: str
    duplicates: tuple[DuplicateGroup, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable report."""
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _included_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in EXCLUDED_DIRECTORIES for part in relative_parts):
            continue
        if path.name == "storage_usage.json" or path.name.endswith(".tmp") or path.is_symlink() or not path.is_file():
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix())


def audit_storage(root: Path, config: StorageConfig) -> StorageAudit:
    """Account for regular files under configured roots without mutation."""
    repository = root.resolve(strict=True)
    if repository != config.root:
        raise StorageConfigError("audit root does not match configuration root")
    entries: list[ManifestEntry] = []
    usage: list[RootUsage] = []
    hashes: dict[str, list[ManifestEntry]] = {}
    for storage_root in config.roots:
        root_entries: list[ManifestEntry] = []
        for path in _included_files(storage_root):
            size = path.stat().st_size
            digest = _sha256(path)
            relative = path.relative_to(repository).as_posix()
            entry = ManifestEntry(path=relative, bytes=size, sha256=digest)
            root_entries.append(entry)
            hashes.setdefault(digest, []).append(entry)
        entries.extend(root_entries)
        usage.append(
            RootUsage(
                root=storage_root.relative_to(repository).as_posix(),
                bytes=sum(entry.bytes for entry in root_entries),
                files=len(root_entries),
            )
        )
    entries.sort(key=lambda entry: entry.path)
    manifest_bytes = json.dumps([asdict(entry) for entry in entries], sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    duplicates = tuple(
        DuplicateGroup(
            sha256=digest,
            bytes=group[0].bytes,
            paths=tuple(sorted(entry.path for entry in group)),
        )
        for digest, group in sorted(hashes.items())
        if len(group) > 1
    )
    total_bytes = sum(entry.bytes for entry in entries)
    return StorageAudit(
        budget_bytes=config.budget_bytes,
        total_bytes=total_bytes,
        total_files=len(entries),
        within_budget=total_bytes <= config.budget_bytes,
        roots=tuple(usage),
        manifest=tuple(entries),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        duplicates=duplicates,
    )


def write_json_report(report: StorageAudit, path: Path) -> None:
    """Write an audit report as stable, human-readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


class StorageGuard:
    """Enforce configured path, quota, and raw-data deletion policies."""

    def __init__(self, root: Path, config: StorageConfig) -> None:
        self.root = root.resolve(strict=True)
        if self.root != config.root:
            raise StorageConfigError("guard root does not match configuration root")
        self.config = config

    def _storage_path(self, path: Path) -> Path:
        candidate = path if path.is_absolute() else self.root / path
        resolved = candidate.resolve(strict=False)
        if not any(_contained(resolved, storage_root) for storage_root in self.config.roots):
            raise OutsideStorageRootError(f"path is outside declared storage roots: {path}")
        return resolved

    def can_write(self, path: Path, size: int) -> bool:
        """Return true when a proposed write is contained and within budget."""
        self._storage_path(path)
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise StorageError("write size must be a non-negative integer")
        usage = audit_storage(self.root, self.config).total_bytes
        if usage + size > self.config.budget_bytes:
            raise BudgetExceededError(f"write would exceed budget: {usage} + {size} > {self.config.budget_bytes}")
        return True

    def deny_delete(self, path: Path) -> None:
        """Reject deletion of any path at or below data/raw."""
        candidate = self._storage_path(path)
        raw_root = (self.root / "data" / "raw").resolve(strict=False)
        if _contained(candidate, raw_root):
            raise RawDataDeletionError(f"raw data deletion is denied: {path}")

    def dry_run_cleanup(self) -> tuple[Path, ...]:
        """List transient cleanup candidates without changing the filesystem."""
        raw_root = (self.root / "data" / "raw").resolve(strict=False)
        candidates: set[Path] = set()
        for storage_root in self.config.roots:
            if not storage_root.is_dir():
                continue
            for path in storage_root.rglob("*"):
                if path.is_symlink() or _contained(path.resolve(strict=False), raw_root):
                    continue
                if (
                    path.is_file()
                    and path.name.endswith(".tmp")
                    or path.is_file()
                    and "__pycache__" in path.relative_to(storage_root).parts
                ):
                    candidates.add(path)
        return tuple(sorted(candidates, key=lambda item: item.as_posix()))
