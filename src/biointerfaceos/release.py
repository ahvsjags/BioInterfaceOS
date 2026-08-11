"""Immutable fixture release and checksum receipt system."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RELEASE_ROOT = Path("release/fixtures")
RELEASE_INPUTS = (
    Path("registry/SOURCE_MANIFEST.parquet"),
    Path("registry/ASSET_INDEX.parquet"),
    Path("registry/rejected_sources.parquet"),
    Path("registry/catalog.duckdb"),
    Path("configs/source_policy.yaml"),
    Path("schemas/source.v1.json"),
)


class ReleaseError(RuntimeError):
    """Raised when a release cannot be safely frozen or verified."""


@dataclass(frozen=True)
class ReleaseSummary:
    """Identity and file count of a verified release."""

    release_id: str
    manifest_hash: str
    data_hash: str
    config_hash: str
    file_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _contained(root: Path, candidate: Path) -> Path:
    repository = root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    if resolved != repository and repository not in resolved.parents:
        raise ReleaseError(f"path escapes repository: {candidate}")
    if "locked_test" in resolved.parts:
        raise ReleaseError("locked-test paths are forbidden")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"invalid release JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"release JSON must be an object: {path}")
    return value


class ReleaseManager:
    """Create and verify immutable fixture releases."""

    def __init__(self, root: Path, release_root: Path | str = RELEASE_ROOT) -> None:
        self.root = root.resolve(strict=True)
        candidate = Path(release_root)
        self.release_root = _contained(
            self.root,
            candidate if candidate.is_absolute() else self.root / candidate,
        )
        if self.release_root == self.root:
            raise ReleaseError("release root cannot be repository root")

    def _input_entries(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for relative in RELEASE_INPUTS:
            path = _contained(self.root, self.root / relative)
            if not path.is_file():
                raise ReleaseError(f"release input is missing: {relative}")
            entries.append(
                {
                    "path": relative.as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
        return entries

    @staticmethod
    def _manifest_hash(entries: Sequence[Mapping[str, Any]]) -> str:
        return hashlib.sha256(_canonical(list(entries))).hexdigest()

    @staticmethod
    def _data_hash(entries: Sequence[Mapping[str, Any]]) -> str:
        selected = [entry for entry in entries if str(entry["path"]).startswith("registry/")]
        return hashlib.sha256(_canonical(selected)).hexdigest()

    @staticmethod
    def _config_hash(entries: Sequence[Mapping[str, Any]]) -> str:
        selected = [
            entry for entry in entries if str(entry["path"]).startswith(("configs/", "schemas/"))
        ]
        return hashlib.sha256(_canonical(selected)).hexdigest()

    def _git_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ReleaseError(f"cannot determine Git commit: {exc}") from exc
        commit = result.stdout.strip()
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
            raise ReleaseError("git commit is not a full hexadecimal object ID")
        return commit

    @staticmethod
    def _make_read_only(directory: Path) -> None:
        for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        directory.chmod(0o555)

    @staticmethod
    def _is_read_only(directory: Path) -> bool:
        return all(
            not bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            for path in (directory, *directory.rglob("*"))
        )

    def freeze(
        self,
        *,
        fixture: bool = False,
        git_commit: str | None = None,
        now: datetime | None = None,
    ) -> ReleaseSummary:
        """Freeze one fixture release and reject same-name overwrite."""
        if not fixture:
            raise ReleaseError("only explicit fixture freezes are enabled in T014")
        entries = self._input_entries()
        manifest_hash = self._manifest_hash(entries)
        data_hash = self._data_hash(entries)
        config_hash = self._config_hash(entries)
        commit = git_commit or self._git_commit()
        if len(commit) < 7 or any(char not in "0123456789abcdef" for char in commit.lower()):
            raise ReleaseError("git_commit must be hexadecimal")
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise ReleaseError("release timestamp must include timezone")
        release_id = f"bioif-data-{current.astimezone(UTC):%Y%m%d}-{commit[:7]}-{manifest_hash[:8]}"
        target = self.release_root / release_id
        if target.exists():
            raise ReleaseError(f"release already exists; overwrite refused: {target}")
        self.release_root.mkdir(parents=True, exist_ok=True)
        temporary = self.release_root / f".{release_id}.{uuid.uuid4().hex}.tmp"
        temporary.mkdir()
        try:
            manifest = {
                "schema_version": 1,
                "release_id": release_id,
                "git_commit": commit,
                "manifest_hash": manifest_hash,
                "data_hash": data_hash,
                "config_hash": config_hash,
                "files": entries,
            }
            (temporary / "release_manifest.json").write_bytes(_canonical(manifest))
            checksums = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
            (temporary / "checksums.txt").write_text(checksums, encoding="utf-8")
            receipt = {
                "schema_version": 1,
                "release_id": release_id,
                "fixture": True,
                "frozen": True,
                "created_at": current.astimezone(UTC).isoformat(),
                "git_commit": commit,
                "manifest_hash": manifest_hash,
                "data_hash": data_hash,
                "config_hash": config_hash,
                "file_count": len(entries),
                "manifest_file": "release_manifest.json",
                "checksums_file": "checksums.txt",
            }
            (temporary / "release_receipt.json").write_bytes(_canonical(receipt))
            self._make_read_only(temporary)
            os.replace(temporary, target)
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise
        return ReleaseSummary(release_id, manifest_hash, data_hash, config_hash, len(entries))

    def _resolve_release(self, release_id: str | None) -> Path:
        if release_id is not None:
            candidate = self.release_root / release_id
            if not candidate.is_dir():
                raise ReleaseError(f"release does not exist: {release_id}")
            return _contained(self.root, candidate)
        if not self.release_root.is_dir():
            raise ReleaseError("no fixture release directory exists")
        candidates = sorted(
            path
            for path in self.release_root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        if not candidates:
            raise ReleaseError("no fixture release exists")
        return candidates[-1]

    def verify(self, release_id: str | None = None) -> ReleaseSummary:
        """Verify an immutable release against current authoritative inputs."""
        directory = self._resolve_release(release_id)
        if not self._is_read_only(directory):
            raise ReleaseError("release directory is writable")
        receipt = _read_json(directory / "release_receipt.json")
        manifest = _read_json(directory / "release_manifest.json")
        if receipt.get("frozen") is not True or receipt.get("fixture") is not True:
            raise ReleaseError("release receipt is not a frozen fixture")
        if (
            receipt.get("release_id") != directory.name
            or manifest.get("release_id") != directory.name
        ):
            raise ReleaseError("release identity mismatch")
        entries = manifest.get("files")
        if not isinstance(entries, list) or not entries:
            raise ReleaseError("release manifest has no files")
        if self._manifest_hash(entries) != manifest.get("manifest_hash"):
            raise ReleaseError("release manifest hash mismatch")
        if manifest.get("data_hash") != self._data_hash(entries):
            raise ReleaseError("release data hash mismatch")
        if manifest.get("config_hash") != self._config_hash(entries):
            raise ReleaseError("release config hash mismatch")
        expected_inputs = self._input_entries()
        if entries != expected_inputs:
            raise ReleaseError("authoritative inputs differ from frozen manifest")
        checksums_path = directory / "checksums.txt"
        actual_checksums = checksums_path.read_text(encoding="utf-8")
        expected_checksums = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries)
        if actual_checksums != expected_checksums:
            raise ReleaseError("checksums.txt differs from release manifest")
        if receipt.get("manifest_hash") != manifest.get("manifest_hash"):
            raise ReleaseError("receipt manifest hash mismatch")
        return ReleaseSummary(
            directory.name,
            str(manifest["manifest_hash"]),
            str(manifest["data_hash"]),
            str(manifest["config_hash"]),
            len(entries),
        )
