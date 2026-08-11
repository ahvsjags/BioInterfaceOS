"""Mock-only PMC Open Access adapter tests."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlsplit

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.sources.base import (
    AdapterError,
    AdapterPolicyError,
    AssetDescriptor,
    SourceQuery,
)
from biointerfaceos.sources.pmc_oa import PmcOaAdapter, PmcOaConfig


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


class PmcOaTests(unittest.TestCase):
    project_root: ClassVar[Path]
    pages: ClassVar[dict[str, bytes]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/pmc_oa"
        cls.pages = {
            accession: (fixture_root / f"{accession}.xml").read_bytes()
            for accession in ("PMC123", "PMC999")
        }

    def _adapter(self, root: Path) -> PmcOaAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            if "oa.fcgi" in request.full_url:
                accession = parse_qs(urlsplit(request.full_url).query)["id"][0]
                return FakeResponse(self.pages[accession])
            return FakeResponse(b"package-bytes")

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(allowed_hosts=("www.ncbi.nlm.nih.gov", "ftp.ncbi.nlm.nih.gov")),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return PmcOaAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_search_preserves_oa_membership_license_and_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidates = adapter.search(SourceQuery("PMC123 PMC999", limit=10))
            self.assertEqual(
                [candidate.accession for candidate in candidates], ["PMC123", "PMC999"]
            )
            self.assertEqual(candidates[0].license_identifier, "CC BY")
            self.assertIsNone(candidates[1].license_identifier)
            self.assertIn("oa.fcgi", candidates[1].url)
            self.assertIn("non-OA", candidates[1].evidence_location or "")

    def test_metadata_records_response_hash_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("PMC123"))[0]
            metadata = adapter.metadata(candidate)
            self.assertTrue(metadata["open_access_subset"])
            self.assertEqual(metadata["license"], "CC BY")
            self.assertEqual(
                metadata["response_sha256"],
                hashlib.sha256(self.pages["PMC123"]).hexdigest(),
            )
            links = metadata["links"]
            self.assertEqual(len(links), 5)
            self.assertTrue(str(links[0]["url"]).startswith("https://ftp.ncbi.nlm.nih.gov/"))

    def test_assets_include_jats_figures_supplement_and_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("PMC123"))[0]
            assets = adapter.list_assets(candidate)
            self.assertEqual(
                [asset.asset_type for asset in assets],
                ["OA_PACKAGE", "JATS", "PDF", "FIGURE", "SUPPLEMENTARY"],
            )
            self.assertTrue(all(asset.sha256 is None for asset in assets))
            self.assertTrue(all(asset.license == "CC BY" for asset in assets))

    def test_non_oa_candidate_is_policy_rejected_before_asset_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("PMC999"))[0]
            with self.assertRaises(AdapterPolicyError):
                adapter.metadata(candidate)
            with self.assertRaises(AdapterPolicyError):
                adapter.list_assets(candidate)

    def test_fetch_requires_checksum_and_promotes_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = self._adapter(root)
            candidate = adapter.search(SourceQuery("PMC123"))[0]
            payload = b"package-bytes"
            digest = hashlib.sha256(payload).hexdigest()
            asset = AssetDescriptor(
                asset_id="package",
                source_id=candidate.source_id,
                url="https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/PMC123.tar.gz",
                asset_type="OA_PACKAGE",
                accession="PMC123",
                sha256=digest,
                size_bytes=len(payload),
                license="CC BY",
            )
            result = adapter.fetch(candidate, asset, Path("data/pmc123.tar.gz"))
            self.assertEqual(result.sha256, digest)
            self.assertEqual(result.path.read_bytes(), payload)
            with self.assertRaises(AdapterError):
                adapter.fetch(
                    candidate,
                    AssetDescriptor(
                        asset_id="no-hash",
                        source_id=candidate.source_id,
                        url=asset.url,
                        asset_type="OA_PACKAGE",
                        accession="PMC123",
                        sha256=None,
                        size_bytes=None,
                        license="CC BY",
                    ),
                    Path("data/no-hash"),
                )

    def test_config_rejects_unbounded_records(self) -> None:
        with self.assertRaises(AdapterError):
            PmcOaConfig(max_records=0)


if __name__ == "__main__":
    unittest.main()
