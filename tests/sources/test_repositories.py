"""Mock-only public repository adapter tests."""

from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.sources.base import AdapterError, AdapterPolicyError, SourceQuery
from biointerfaceos.sources.repositories import HOSTS, RepositoryAdapter, RepositoryConfig


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._stream = BytesIO(body)
        self.status = status
        self.headers: dict[str, str] = {}

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def close(self) -> None:
        return None

    def getcode(self) -> int:
        return self.status


class RepositoryTests(unittest.TestCase):
    project_root: ClassVar[Path]
    fixtures: ClassVar[dict[str, bytes]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/repositories"
        cls.fixtures = {path.stem: path.read_bytes() for path in fixture_root.glob("*.json")}

    def _adapter(self, root: Path) -> RepositoryAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            url = request.full_url
            if "/api/records/12345" in url:
                body = self.fixtures["zenodo_12345"]
            elif "/api/records/999" in url:
                body = self.fixtures["zenodo_missing_license"]
            elif "api/records?" in url and "page=2" in url:
                body = self.fixtures["zenodo_search_page_2"]
            elif "api/records?" in url:
                body = self.fixtures["zenodo_search_page_1"]
            elif "/v2/articles/987" in url:
                body = self.fixtures["figshare_987"]
            elif "/v2/nodes/abc12/files/osfstorage" in url:
                body = self.fixtures["osf_files_abc12"]
            elif "/v2/nodes/abc12" in url:
                body = self.fixtures["osf_abc12"]
            elif "/repos/openai/demo/releases" in url:
                body = self.fixtures["github_release_demo"]
            elif "/repos/openai/demo" in url:
                body = self.fixtures["github_repo_demo"]
            else:
                raise AssertionError(f"unexpected URL: {url}")
            return FakeResponse(body)

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                rate_interval=0.2,
                allowed_hosts=HOSTS,
            ),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return RepositoryAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_four_provider_metadata_preserves_release_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            cases = (
                ("zenodo:12345", "Biointerface benchmark", "1.2.0", "CC-BY-4.0"),
                ("figshare:987", "Public assay data", "2", "CC-BY-4.0"),
                ("osf:abc12", "OSF analysis release", None, "CC0"),
                ("github:openai/demo@v1.0.0", "v1.0.0", "v1.0.0", "CC-BY-4.0"),
            )
            for query, title, version, license_id in cases:
                candidate = adapter.search(SourceQuery(query))[0]
                metadata = adapter.metadata(candidate)
                self.assertEqual(metadata["title"], title)
                self.assertEqual(metadata["version"], version)
                self.assertEqual(metadata["license"], license_id)
                self.assertEqual(len(metadata["response_sha256"]), 64)

    def test_zenodo_search_follows_page_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidates = adapter.search(SourceQuery("zenodo:search:corona", limit=10))
            self.assertEqual(
                [candidate.accession for candidate in candidates],
                ["12345", "23456"],
            )

    def test_release_assets_keep_provider_ids_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            expected = {
                "zenodo:12345": (("z1",), ("a" * 64,)),
                "figshare:987": (("1", "2"), ("b" * 64, "e" * 64)),
                "osf:abc12": (("file1",), ("c" * 64,)),
                "github:openai/demo@v1.0.0": (("7",), ("d" * 64,)),
            }
            for query, (accessions, digests) in expected.items():
                candidate = adapter.search(SourceQuery(query))[0]
                assets = adapter.list_assets(candidate)
                self.assertEqual([asset.accession for asset in assets], list(accessions))
                self.assertEqual([asset.sha256 for asset in assets], list(digests))
                self.assertTrue(all(asset.source_id == candidate.source_id for asset in assets))

    def test_duplicate_download_urls_remain_distinct_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("figshare:987"))[0]
            assets = adapter.list_assets(candidate)
            self.assertEqual(len(assets), 2)
            self.assertEqual(assets[0].url, assets[1].url)
            self.assertNotEqual(assets[0].asset_id, assets[1].asset_id)

    def test_rate_limit_response_is_retried_without_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            calls = 0

            def opener(request: Any, *, timeout: float) -> FakeResponse:
                nonlocal calls
                calls += 1
                if calls == 1:
                    return FakeResponse(b"{}", status=429)
                return FakeResponse(self.fixtures["zenodo_12345"])

            client = AnonymousHttpClient(
                root=Path(temporary),
                config=NetworkConfig(
                    max_retries=2,
                    rate_interval=0.2,
                    allowed_hosts=HOSTS,
                ),
                opener=opener,
                sleep=lambda _: None,
                clock=lambda: 0.0,
            )
            adapter = RepositoryAdapter(
                Path(temporary),
                SourcePolicyEngine.from_yaml(self.project_root),
                client=client,
            )
            candidate = adapter.search(SourceQuery("zenodo:12345"))[0]
            self.assertEqual(candidate.accession, "12345")
            self.assertEqual(calls, 2)

    def test_missing_license_is_quarantined_before_metadata_and_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("zenodo:999"))[0]
            self.assertEqual(adapter.policy_decision(candidate).decision, "QUARANTINE")
            with self.assertRaises(AdapterPolicyError):
                adapter.metadata(candidate)
            with self.assertRaises(AdapterPolicyError):
                adapter.list_assets(candidate)

    def test_bounds_and_unverifiable_assets_are_explicit(self) -> None:
        with self.assertRaises(AdapterError):
            RepositoryConfig(max_pages=0)
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("zenodo:12345"))[0]
            asset = adapter.list_assets(candidate)[0]
            self.assertEqual(
                adapter.policy_decision(candidate).decision, "ADMIT_PUBLIC_REDISTRIBUTABLE"
            )
            with self.assertRaises(AdapterError):
                adapter.fetch(
                    candidate,
                    asset.__class__(
                        asset_id=asset.asset_id,
                        source_id=asset.source_id,
                        url=asset.url,
                        asset_type=asset.asset_type,
                        accession=asset.accession,
                        sha256=None,
                        size_bytes=asset.size_bytes,
                        license=asset.license,
                    ),
                    Path(temporary) / "download.zip",
                )


if __name__ == "__main__":
    unittest.main()
