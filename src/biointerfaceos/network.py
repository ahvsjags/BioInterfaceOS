"""Credential-free, deterministic HTTP helpers for public anonymous sources."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

PROJECT_USER_AGENT = "BioInterfaceOS/0.1 (anonymous)"
_RETRYABLE_STATUS = frozenset({429})
_CREDENTIAL_HEADER_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api-key",
    "apikey",
)


class NetworkError(RuntimeError):
    """Base class for network policy, transport, and payload failures."""


class NetworkPolicyError(NetworkError):
    """Raised when a request violates anonymous-access policy."""


class NetworkHTTPError(NetworkError):
    """Raised for HTTP responses that cannot be returned to the caller."""

    def __init__(self, url: str, status: int, reason: str = "") -> None:
        detail = f"HTTP {status} for {url}"
        if reason:
            detail = f"{detail}: {reason}"
        super().__init__(detail)
        self.url = url
        self.status = status
        self.reason = reason


class ChecksumMismatchError(NetworkError):
    """Raised when a resumable download does not match its expected digest."""


@dataclass(frozen=True)
class NetworkConfig:
    """Validated anonymous-network policy and bounded retry settings."""

    timeout: float = 30.0
    max_retries: int = 3
    backoff_factor: float = 0.5
    max_backoff: float = 30.0
    rate_interval: float = 0.0
    allowed_hosts: tuple[str, ...] = ()
    user_agent: str = PROJECT_USER_AGENT
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 < self.timeout <= 300:
            raise NetworkPolicyError("timeout must be in (0, 300]")
        if not 0 <= self.max_retries <= 10:
            raise NetworkPolicyError("max_retries must be between 0 and 10")
        if not 0 <= self.backoff_factor <= 60:
            raise NetworkPolicyError("backoff_factor must be between 0 and 60")
        if not 0 < self.max_backoff <= 300:
            raise NetworkPolicyError("max_backoff must be in (0, 300]")
        if not 0 <= self.rate_interval <= 3600:
            raise NetworkPolicyError("rate_interval must be between 0 and 3600")
        if self.user_agent != PROJECT_USER_AGENT:
            raise NetworkPolicyError("the project User-Agent is fixed")
        normalized_hosts: list[str] = []
        for host in self.allowed_hosts:
            if not isinstance(host, str) or not host.strip():
                raise NetworkPolicyError("allowed_hosts entries must be non-empty strings")
            parsed = urlsplit(f"https://{host.strip()}")
            if parsed.hostname is None or parsed.path not in ("", "/") or parsed.query:
                raise NetworkPolicyError(f"invalid allowed host: {host}")
            normalized_hosts.append(parsed.hostname.lower())
        object.__setattr__(self, "allowed_hosts", tuple(dict.fromkeys(normalized_hosts)))
        for name, value in self.headers.items():
            lowered = name.lower().strip()
            if lowered != "user-agent" or value != PROJECT_USER_AGENT:
                raise NetworkPolicyError("custom request headers are forbidden; only the fixed User-Agent is allowed")


class AnonymousHttpClient:
    """A mockable GET client that never uses credentials or real ambient auth."""

    def __init__(
        self,
        root: Path | None = None,
        config: NetworkConfig | None = None,
        *,
        opener: Callable[..., Any] | None = None,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.root = (root or Path.cwd()).resolve(strict=True)
        self.config = config or NetworkConfig()
        self._opener = opener or urlopen
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        self._last_request_at: float | None = None

    def _validate_url(self, url: str) -> str:
        if not isinstance(url, str) or not url:
            raise NetworkPolicyError("URL must be a non-empty string")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise NetworkPolicyError("only absolute HTTP(S) URLs are allowed")
        if parsed.username is not None or parsed.password is not None:
            raise NetworkPolicyError("URL credentials are forbidden")
        try:
            port = parsed.port
        except ValueError as exc:
            raise NetworkPolicyError("URL port is invalid") from exc
        if port is not None and not 1 <= port <= 65535:
            raise NetworkPolicyError("URL port is invalid")
        host = parsed.hostname.lower()
        if self.config.allowed_hosts and host not in self.config.allowed_hosts:
            raise NetworkPolicyError(f"host is not allowed: {host}")
        return url

    def _pace(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self.config.rate_interval - (now - self._last_request_at)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at = self._clock()

    @staticmethod
    def _header(response: Any, name: str) -> str | None:
        headers = getattr(response, "headers", None)
        if headers is None:
            return None
        value = headers.get(name)
        if value is None:
            value = headers.get(name.lower())
        return str(value).strip() if value is not None else None

    def _retry_after(self, response: Any) -> float | None:
        raw = self._header(response, "Retry-After")
        if raw is None or not raw.isdigit():
            return None
        value = float(raw)
        return min(value, self.config.max_backoff)

    def _delay(self, attempt: int, response: Any = None) -> float:
        exponential: float = float(
            min(
                self.config.max_backoff,
                self.config.backoff_factor * (2**attempt),
            )
        )
        retry_after = self._retry_after(response) if response is not None else None
        if retry_after is None:
            return exponential
        retry_delay: float = float(retry_after)
        return max(exponential, retry_delay)

    @staticmethod
    def _status(response: Any) -> int:
        value = getattr(response, "status", None)
        if value is None:
            value = response.getcode()
        return int(value or 200)

    @staticmethod
    def _close(response: Any) -> None:
        close = getattr(response, "close", None)
        if close is not None:
            close()

    def _request(self, url: str, *, range_header: str | None = None) -> Any:
        validated = self._validate_url(url)
        for attempt in range(self.config.max_retries + 1):
            self._pace()
            request = Request(validated, method="GET", headers={"User-Agent": PROJECT_USER_AGENT})
            if range_header is not None:
                request.add_header("Range", range_header)
            try:
                response = self._opener(request, timeout=self.config.timeout)
                status = self._status(response)
                if 200 <= status < 300:
                    return response
                if status in _RETRYABLE_STATUS or 500 <= status <= 599:
                    if attempt >= self.config.max_retries:
                        self._close(response)
                        raise NetworkHTTPError(validated, status)
                    delay = self._delay(attempt, response)
                    self._close(response)
                    self._sleep(delay)
                    continue
                reason = self._header(response, "X-Error") or ""
                self._close(response)
                raise NetworkHTTPError(validated, status, reason)
            except HTTPError as exc:
                if exc.code not in _RETRYABLE_STATUS and not 500 <= exc.code <= 599:
                    raise
                if attempt >= self.config.max_retries:
                    raise
                self._sleep(self._delay(attempt, exc))
            except (URLError, TimeoutError):
                if attempt >= self.config.max_retries:
                    raise
                self._sleep(self._delay(attempt))

        raise NetworkError("request retry loop ended unexpectedly")

    def get_bytes(self, url: str) -> bytes:
        """Fetch one anonymous GET response as bytes."""
        response = self._request(url)
        try:
            body = response.read()
        except (URLError, TimeoutError) as exc:
            raise NetworkError(f"failed reading {url}: {exc}") from exc
        finally:
            self._close(response)
        if not isinstance(body, bytes):
            raise NetworkError("HTTP response did not return bytes")
        return body

    def get_json(self, url: str) -> Any:
        """Fetch one anonymous GET response and decode UTF-8 JSON."""
        try:
            return json.loads(self.get_bytes(url).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NetworkError(f"invalid JSON response from {url}") from exc

    def iter_json_pages(
        self,
        url: str,
        *,
        next_field: str = "next",
        max_pages: int = 1000,
    ) -> Iterator[Mapping[str, Any]]:
        """Yield pages by following deterministic absolute or relative next URLs."""
        if max_pages <= 0:
            raise NetworkPolicyError("max_pages must be positive")
        current = self._validate_url(url)
        seen: set[str] = set()
        for _ in range(max_pages):
            if current in seen:
                raise NetworkError(f"pagination cycle detected at {current}")
            seen.add(current)
            page = self.get_json(current)
            if not isinstance(page, Mapping):
                raise NetworkError("paginated response must be a JSON object")
            yield page
            next_url = page.get(next_field)
            if next_url in (None, ""):
                return
            if not isinstance(next_url, str):
                raise NetworkError(f"pagination field {next_field!r} must be a URL or null")
            current = self._validate_url(urljoin(current, next_url))
        raise NetworkError(f"pagination exceeded max_pages={max_pages}")

    def iter_paginated_items(
        self,
        url: str,
        *,
        items_field: str = "items",
        next_field: str = "next",
        max_pages: int = 1000,
    ) -> Iterator[Any]:
        """Yield list items from each deterministic JSON page."""
        for page in self.iter_json_pages(url, next_field=next_field, max_pages=max_pages):
            items = page.get(items_field)
            if not isinstance(items, list):
                raise NetworkError(f"pagination field {items_field!r} must be a list")
            yield from items

    def paginate(self, url: str, **kwargs: Any) -> Iterator[Any]:
        """Compatibility alias for item pagination."""
        return self.iter_paginated_items(url, **kwargs)

    def _destination(self, destination: Path | str) -> tuple[Path, Path]:
        candidate = Path(destination)
        resolved = (candidate if candidate.is_absolute() else self.root / candidate).resolve(strict=False)
        if resolved == self.root or self.root not in resolved.parents:
            raise NetworkPolicyError(f"destination is outside repository: {destination}")
        parent = resolved.parent.resolve(strict=False)
        if self.root not in parent.parents and parent != self.root:
            raise NetworkPolicyError(f"destination parent is outside repository: {destination}")
        part = Path(f"{resolved}.part")
        part_resolved = part.resolve(strict=False)
        if self.root not in part_resolved.parents:
            raise NetworkPolicyError(f"partial destination is outside repository: {part}")
        return resolved, part

    @staticmethod
    def _validate_digest(expected_sha256: str) -> str:
        normalized = expected_sha256.lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise NetworkPolicyError("expected_sha256 must be a 64-character hexadecimal digest")
        return normalized

    def download(
        self,
        url: str,
        destination: Path | str,
        *,
        expected_sha256: str,
        chunk_size: int = 1024 * 1024,
    ) -> Path:
        """Resume a sibling .part file and atomically promote a verified result."""
        if chunk_size <= 0:
            raise NetworkPolicyError("chunk_size must be positive")
        expected = self._validate_digest(expected_sha256)
        resolved, part = self._destination(destination)
        if part.exists() and not part.is_file():
            raise NetworkPolicyError(f"partial destination is not a regular file: {part}")
        existing_size = part.stat().st_size if part.exists() else 0
        range_header = f"bytes={existing_size}-" if existing_size else None
        response = self._request(url, range_header=range_header)
        status = self._status(response)
        append = existing_size > 0 and status == 206
        if existing_size > 0 and status not in {200, 206}:
            self._close(response)
            raise NetworkHTTPError(url, status)
        if status == 206:
            content_range = self._header(response, "Content-Range")
            if existing_size > 0 and (content_range is None or not content_range.startswith(f"bytes {existing_size}-")):
                self._close(response)
                raise NetworkError("server returned an incompatible Content-Range")
            append = existing_size > 0
        mode = "ab" if append else "wb"
        digest = hashlib.sha256()
        try:
            if append:
                with part.open("rb") as previous:
                    for chunk in iter(lambda: previous.read(chunk_size), b""):
                        digest.update(chunk)
            part.parent.mkdir(parents=True, exist_ok=True)
            with part.open(mode) as stream:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise NetworkError("HTTP response did not return bytes")
                    stream.write(chunk)
                    digest.update(chunk)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            self._close(response)
        actual = digest.hexdigest()
        if actual != expected:
            raise ChecksumMismatchError(
                f"checksum mismatch for {resolved}: expected {expected}, got {actual}; partial file preserved at {part}"
            )
        os.replace(part, resolved)
        return resolved
