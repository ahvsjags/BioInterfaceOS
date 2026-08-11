"""Mock-only Europe PMC adapter tests."""

from __future__ import annotations

import hashlib
import json
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
from biointerfaceos.sources.europe_pmc import EuropePmcAdapter


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


class EuropePmcTests(unittest.TestCase):
    project_root: ClassVar[Path]
    pages: ClassVar[dict[str, dict[str, Any]]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/europe_pmc"
        cls.pages = {
            "*": json.loads((fixture_root / "search_page_1.json").read_text()),
            "CURSOR-2": json.loads((fixture_root / "search_page_2.json").read_text()),
        }

    def _adapter(self, root: Path) -> EuropePmcAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            if request.full_url.endswith("/fullTextXML"):
                return FakeResponse(b"xml payload")
            cursor = parse_qs(urlsplit(request.full_url).query)["cursorMark"][0]
            return FakeResponse(json.dumps(self.pages[cursor]).encode("utf-8"))

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(allowed_hosts=("www.ebi.ac.uk",)),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return EuropePmcAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_search_cursor_pagination_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidates = adapter.search(SourceQuery("nanoparticle", limit=10))
            self.assertEqual(
                [candidate.accession for candidate in candidates], ["PMC123", "PMC124"]
            )
            self.assertEqual(candidates[0].license_identifier, "CC-BY-4.0")
            self.assertEqual(candidates[0].evidence_location, "Europe PMC REST search result")

    def test_metadata_links_and_asset_listing_use_policy_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("query"))[0]
            metadata = adapter.metadata(candidate)
            self.assertTrue(str(metadata["full_text_url"]).endswith("/PMC123/fullTextXML"))
            self.assertTrue(
                str(metadata["supplementary_url"]).endswith("/PMC123/supplementaryFiles")
            )
            assets = adapter.list_assets(candidate)
            self.assertEqual([asset.asset_type for asset in assets], ["JATS", "SUPPLEMENTARY"])
            self.assertTrue(all(asset.sha256 is None for asset in assets))
            unlicensed = type(candidate).from_mapping(
                {
                    **candidate.__dict__,
                    "license_identifier": None,
                    "license_text": None,
                }
            )
            with self.assertRaises(AdapterPolicyError):
                adapter.metadata(unlicensed)

    def test_fetch_requires_checksum_and_uses_atomic_network_client(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = self._adapter(root)
            candidate = adapter.search(SourceQuery("query"))[0]
            payload = b"xml payload"
            digest = hashlib.sha256(payload).hexdigest()
            asset = AssetDescriptor(
                asset_id="asset",
                source_id=candidate.source_id,
                url="https://www.ebi.ac.uk/europepmc/webservices/rest/PMC123/fullTextXML",
                asset_type="JATS",
                accession="PMC123",
                sha256=digest,
                size_bytes=len(payload),
                license="CC-BY-4.0",
            )
            result = adapter.fetch(candidate, asset, Path("data/pmc.xml"))
            self.assertEqual(result.sha256, digest)
            self.assertEqual(result.path.read_bytes(), payload)
            with self.assertRaises(AdapterError):
                adapter.fetch(
                    candidate,
                    AssetDescriptor(
                        asset_id="no-hash",
                        source_id=candidate.source_id,
                        url=asset.url,
                        asset_type="JATS",
                        accession="PMC123",
                        sha256=None,
                        size_bytes=None,
                        license="CC-BY-4.0",
                    ),
                    Path("data/no-hash"),
                )

    def test_config_rejects_unbounded_pagination(self) -> None:
        from biointerfaceos.sources.europe_pmc import EuropePmcConfig

        with self.assertRaises(AdapterError):
            EuropePmcConfig(max_pages=0)


if __name__ == "__main__":
    unittest.main()
