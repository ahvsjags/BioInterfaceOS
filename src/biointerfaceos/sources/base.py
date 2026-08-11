"""Typed source-adapter contract and deterministic offline fixture harness."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.network import AnonymousHttpClient
from biointerfaceos.policy import PolicyDecision, SourceCandidate, SourcePolicyEngine


class AdapterError(RuntimeError):
    """Base source adapter contract error."""


class AdapterPolicyError(AdapterError):
    """Raised when a candidate fails anonymous/license policy."""


class AdapterFixtureError(AdapterError):
    """Raised when a fixture is unsafe, invalid, or non-deterministic."""


@dataclass(frozen=True)
class SourceQuery:
    """Deterministic source search request."""

    text: str
    limit: int = 20

    def __post_init__(self) -> None:
        if not self.text.strip() or not 0 < self.limit <= 1000:
            raise AdapterError("query text and bounded positive limit are required")


@dataclass(frozen=True)
class AssetDescriptor:
    """Provider-neutral asset metadata returned by list_assets."""

    asset_id: str
    source_id: str
    url: str
    asset_type: str
    accession: str | None
    sha256: str | None
    size_bytes: int | None
    license: str | None


@dataclass(frozen=True)
class FetchResult:
    """Result of an adapter fetch."""

    path: Path
    sha256: str
    size_bytes: int


class SourceAdapter(ABC):
    """Abstract contract shared by every anonymous source adapter."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        client: AnonymousHttpClient | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.policy = policy
        self.client = client

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable adapter identifier."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Pinned adapter version."""

    @abstractmethod
    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        """Return deterministic candidate metadata without downloading assets."""

    @abstractmethod
    def metadata(self, candidate: SourceCandidate) -> Mapping[str, Any]:
        """Return metadata for one policy-checked candidate."""

    @abstractmethod
    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        """List remote assets without downloading bytes."""

    @abstractmethod
    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        """Fetch one policy-checked asset into a repository-contained path."""

    def policy_decision(self, candidate: SourceCandidate) -> PolicyDecision:
        return self.policy.evaluate(candidate)

    def require_admitted(self, candidate: SourceCandidate) -> PolicyDecision:
        decision = self.policy_decision(candidate)
        if decision.decision not in {"ADMIT_PUBLIC_REDISTRIBUTABLE", "ADMIT_ANALYSIS_ONLY"}:
            raise AdapterPolicyError(
                f"{candidate.source_id} is not admitted: "
                f"{decision.decision}/{decision.rejection_code}"
            )
        return decision


_PRIVATE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private",
)
_VOLATILE_KEYS = frozenset(
    {
        "date",
        "server",
        "etag",
        "last-modified",
        "request-id",
        "trace-id",
        "timestamp",
        "downloaded_at",
        "received_at",
    }
)


class FixtureHarness:
    """Canonicalize and atomically record provider response fixtures."""

    def __init__(self, root: Path, adapter_name: str) -> None:
        self.root = root.resolve(strict=True)
        if not re.fullmatch(r"[a-z0-9_]+", adapter_name):
            raise AdapterFixtureError("adapter_name must be lowercase identifier")
        self.adapter_name = adapter_name
        self.fixture_root = self.root / "tests/fixtures/sources" / adapter_name

    @classmethod
    def sanitize(cls, value: Any, *, key: str | None = None) -> Any:
        """Recursively remove private and volatile keys."""
        if key is not None:
            lowered = key.lower().replace("-", "_")
            if lowered in _VOLATILE_KEYS or any(part in lowered for part in _PRIVATE_KEY_PARTS):
                return None
        if isinstance(value, Mapping):
            clean: dict[str, Any] = {}
            for name in sorted(value):
                sanitized = cls.sanitize(value[name], key=str(name))
                if sanitized is not None and not (
                    isinstance(sanitized, dict | list) and not sanitized
                ):
                    clean[str(name)] = sanitized
            return clean
        if isinstance(value, list):
            return [cls.sanitize(item) for item in value]
        if isinstance(value, tuple):
            return [cls.sanitize(item) for item in value]
        if isinstance(value, str | int | float | bool) or value is None:
            return value
        raise AdapterFixtureError(f"unsupported fixture value: {type(value).__name__}")

    def record(self, name: str, payload: Any) -> Path:
        """Write one sanitized canonical JSON fixture atomically."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise AdapterFixtureError("fixture name is invalid")
        sanitized = self.sanitize(payload)
        encoded = (
            json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode("utf-8")
        self.fixture_root.mkdir(parents=True, exist_ok=True)
        target = self.fixture_root / f"{name}.json"
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=self.fixture_root,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
            temporary_name = None
        except Exception as exc:
            raise AdapterFixtureError(f"cannot write fixture: {exc}") from exc
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
        return target

    def load(self, name: str) -> Any:
        target = self.fixture_root / f"{name}.json"
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AdapterFixtureError(f"cannot load fixture {name}: {exc}") from exc

    @staticmethod
    def digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


class FixtureAdapter(SourceAdapter):
    """Provider-neutral in-memory adapter used only for contract tests."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        candidates: Sequence[SourceCandidate],
        metadata_by_source: Mapping[str, Mapping[str, Any]],
        assets_by_source: Mapping[str, Sequence[AssetDescriptor]],
        payloads: Mapping[str, bytes],
    ) -> None:
        super().__init__(root, policy)
        self._candidates = tuple(candidates)
        self._metadata = {key: dict(value) for key, value in metadata_by_source.items()}
        self._assets = {key: tuple(value) for key, value in assets_by_source.items()}
        self._payloads = dict(payloads)

    @property
    def name(self) -> str:
        return "fixture"

    @property
    def version(self) -> str:
        return "1.0.0"

    def search(self, query: SourceQuery) -> tuple[SourceCandidate, ...]:
        needle = query.text.lower()
        matches = tuple(
            candidate
            for candidate in self._candidates
            if needle in candidate.source_id.lower()
            or needle in candidate.source_name.lower()
            or needle in candidate.url.lower()
        )
        return tuple(sorted(matches, key=lambda item: item.source_id)[: query.limit])

    def metadata(self, candidate: SourceCandidate) -> Mapping[str, Any]:
        self.require_admitted(candidate)
        try:
            return dict(self._metadata[candidate.source_id])
        except KeyError as exc:
            raise AdapterError(f"metadata fixture missing: {candidate.source_id}") from exc

    def list_assets(self, candidate: SourceCandidate) -> tuple[AssetDescriptor, ...]:
        self.require_admitted(candidate)
        return tuple(self._assets.get(candidate.source_id, ()))

    def fetch(
        self,
        candidate: SourceCandidate,
        asset: AssetDescriptor,
        destination: Path,
    ) -> FetchResult:
        self.require_admitted(candidate)
        if asset.source_id != candidate.source_id:
            raise AdapterError("asset source mismatch")
        try:
            payload = self._payloads[asset.asset_id]
        except KeyError as exc:
            raise AdapterError(f"payload fixture missing: {asset.asset_id}") from exc
        target = (destination if destination.is_absolute() else self.root / destination).resolve(
            strict=False
        )
        if target != self.root and self.root not in target.parents:
            raise AdapterError("fetch destination escapes repository")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.part")
        temporary.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        if asset.sha256 is not None and asset.sha256 != digest:
            raise AdapterError("fixture payload hash mismatch")
        os.replace(temporary, target)
        return FetchResult(target, digest, len(payload))
