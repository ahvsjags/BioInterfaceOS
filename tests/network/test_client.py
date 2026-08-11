"""Mock-only tests for the anonymous network client."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

from biointerfaceos.network import (
    PROJECT_USER_AGENT,
    AnonymousHttpClient,
    ChecksumMismatchError,
    NetworkConfig,
    NetworkError,
    NetworkHTTPError,
    NetworkPolicyError,
)


class FakeResponse:
    def __init__(self, body: bytes = b"", status: int = 200, headers: dict[str, str] | None = None):
        self._stream = BytesIO(body)
        self.status = status
        self.headers = headers or {}
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def close(self) -> None:
        self.closed = True

    def getcode(self) -> int:
        return self.status


class AnonymousNetworkTests(unittest.TestCase):
    def test_policy_rejects_credentials_and_non_http_urls(self) -> None:
        with self.assertRaises(NetworkPolicyError):
            NetworkConfig(headers={"Authorization": "Bearer secret"})
        with self.assertRaises(NetworkPolicyError):
            NetworkConfig(user_agent="custom-agent")
        client = AnonymousHttpClient(
            root=Path.cwd(),
            config=NetworkConfig(allowed_hosts=("public.example",)),
        )
        with self.assertRaises(NetworkPolicyError):
            client.get_bytes("https://user:pass@public.example/path")
        with self.assertRaises(NetworkPolicyError):
            client.get_bytes("ftp://public.example/file")

    def test_get_retries_transient_status_with_retry_after_and_fixed_headers(self) -> None:
        responses = [
            FakeResponse(status=503, headers={"Retry-After": "2"}),
            FakeResponse(b'{"ok": true}'),
        ]
        requests: list[tuple[Request, float]] = []
        sleeps: list[float] = []

        def opener(request: Request, *, timeout: float) -> FakeResponse:
            requests.append((request, timeout))
            return responses.pop(0)

        client = AnonymousHttpClient(
            config=NetworkConfig(backoff_factor=0.5),
            opener=opener,
            sleep=sleeps.append,
            clock=lambda: 0.0,
        )
        self.assertEqual(client.get_json("https://public.example/status"), {"ok": True})
        self.assertEqual(sleeps, [2.0])
        self.assertEqual(len(requests), 2)
        for request, timeout in requests:
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.get_header("User-agent"), PROJECT_USER_AGENT)
            self.assertIsNone(request.get_header("Authorization"))
            self.assertEqual(timeout, 30.0)

    def test_transport_errors_retry_but_other_client_errors_do_not(self) -> None:
        calls = 0

        def temporary_then_ok(request: Request, *, timeout: float) -> FakeResponse:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise URLError("temporary")
            return FakeResponse(b"ok")

        client = AnonymousHttpClient(
            config=NetworkConfig(backoff_factor=0.0),
            opener=temporary_then_ok,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        self.assertEqual(client.get_bytes("https://public.example/retry"), b"ok")
        self.assertEqual(calls, 2)

        calls = 0

        def not_found(request: Request, *, timeout: float) -> FakeResponse:
            nonlocal calls
            calls += 1
            return FakeResponse(status=404)

        client = AnonymousHttpClient(
            config=NetworkConfig(max_retries=5),
            opener=not_found,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        with self.assertRaises(NetworkHTTPError):
            client.get_bytes("https://public.example/missing")
        self.assertEqual(calls, 1)

    def test_rate_interval_is_enforced_between_request_starts(self) -> None:
        now = [0.0]
        sleeps: list[float] = []

        def clock() -> float:
            return now[0]

        def sleep(seconds: float) -> None:
            sleeps.append(seconds)
            now[0] += seconds

        def opener(request: Request, *, timeout: float) -> FakeResponse:
            return FakeResponse(b"ok")

        client = AnonymousHttpClient(
            config=NetworkConfig(rate_interval=2.0),
            opener=opener,
            sleep=sleep,
            clock=clock,
        )
        client.get_bytes("https://public.example/a")
        client.get_bytes("https://public.example/b")
        self.assertEqual(sleeps, [2.0])

    def test_pagination_is_deterministic_and_rejects_cycles(self) -> None:
        pages = {
            "https://public.example/page/1": b'{"items": [1, 2], "next": "/page/2"}',
            "https://public.example/page/2": b'{"items": [3], "next": null}',
        }
        seen: list[str] = []

        def opener(request: Request, *, timeout: float) -> FakeResponse:
            seen.append(request.full_url)
            return FakeResponse(pages[request.full_url])

        client = AnonymousHttpClient(opener=opener, clock=lambda: 0.0, sleep=lambda _: None)
        self.assertEqual(
            list(client.iter_paginated_items("https://public.example/page/1")),
            [1, 2, 3],
        )
        self.assertEqual(seen, ["https://public.example/page/1", "https://public.example/page/2"])

        cycle_client = AnonymousHttpClient(
            opener=lambda request, *, timeout: FakeResponse(b'{"items": [], "next": "/same"}'),
            clock=lambda: 0.0,
            sleep=lambda _: None,
        )
        with self.assertRaises(NetworkError):
            list(cycle_client.iter_json_pages("https://public.example/same", max_pages=3))

    def test_download_resume_checksum_and_atomic_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "data" / "payload.bin"
            destination.parent.mkdir()
            destination.write_bytes(b"old")
            part = Path(f"{destination}.part")
            part.write_bytes(b"abc")
            requests = []

            def opener(request: Request, *, timeout: float) -> FakeResponse:
                requests.append(request)
                self.assertEqual(request.get_header("Range"), "bytes=3-")
                return FakeResponse(
                    b"def",
                    status=206,
                    headers={"Content-Range": "bytes 3-5/6"},
                )

            client = AnonymousHttpClient(
                root=root, opener=opener, clock=lambda: 0.0, sleep=lambda _: None
            )
            expected = hashlib.sha256(b"abcdef").hexdigest()
            result = client.download(
                "https://public.example/file", destination, expected_sha256=expected
            )
            self.assertEqual(result, destination)
            self.assertEqual(destination.read_bytes(), b"abcdef")
            self.assertFalse(part.exists())
            self.assertEqual(len(requests), 1)

    def test_download_restarts_when_server_ignores_range_and_preserves_failed_part(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "data" / "payload.bin"
            destination.parent.mkdir()
            destination.write_bytes(b"old")
            part = Path(f"{destination}.part")
            part.write_bytes(b"partial")

            def opener(request: Request, *, timeout: float) -> FakeResponse:
                self.assertEqual(request.get_header("Range"), "bytes=7-")
                return FakeResponse(b"fresh")

            client = AnonymousHttpClient(
                root=root, opener=opener, clock=lambda: 0.0, sleep=lambda _: None
            )
            with self.assertRaises(ChecksumMismatchError):
                client.download(
                    "https://public.example/file",
                    destination,
                    expected_sha256=hashlib.sha256(b"wrong").hexdigest(),
                )
            self.assertEqual(destination.read_bytes(), b"old")
            self.assertEqual(part.read_bytes(), b"fresh")

    def test_download_contains_destination_and_requires_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            client = AnonymousHttpClient(
                root=root, opener=lambda *args, **kwargs: FakeResponse(b"")
            )
            with self.assertRaises(NetworkPolicyError):
                client.download(
                    "https://public.example/file",
                    root.parent / "outside.bin",
                    expected_sha256=hashlib.sha256(b"").hexdigest(),
                )
            with self.assertRaises(NetworkPolicyError):
                client.download(
                    "https://public.example/file",
                    "data/file",
                    expected_sha256="bad",
                )


if __name__ == "__main__":
    unittest.main()
