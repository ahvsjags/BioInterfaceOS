"""Mock-only PubChem PUG-REST adapter tests."""

from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.sources.base import AdapterError, AssetDescriptor, SourceQuery
from biointerfaceos.sources.pubchem import PubChemAdapter, PubChemConfig


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


class PubChemTests(unittest.TestCase):
    project_root: ClassVar[Path]
    fixtures: ClassVar[dict[str, bytes]]
    calls: list[str]
    sleeps: list[float]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/pubchem"
        cls.fixtures = {
            name: (fixture_root / name).read_bytes()
            for name in (
                "name_aspirin.json",
                "name_ambiguous.json",
                "name_missing.json",
                "properties_2244.json",
            )
        }

    def _adapter(self, root: Path) -> PubChemAdapter:
        self.calls = []
        self.sleeps = []
        clock_state = [0.0]

        def opener(request: Any, *, timeout: float) -> FakeResponse:
            url = request.full_url
            self.calls.append(url)
            if "/compound/name/aspirin/" in url:
                body = self.fixtures["name_aspirin.json"]
            elif "/compound/name/caffeine/" in url:
                body = self.fixtures["name_ambiguous.json"]
            elif "/compound/name/unknown/" in url:
                body = self.fixtures["name_missing.json"]
            elif "/property/" in url:
                body = self.fixtures["properties_2244.json"]
            else:
                raise AssertionError(f"unexpected URL: {url}")
            response = FakeResponse(body)
            return response

        def clock() -> float:
            return clock_state[0]

        def sleep(seconds: float) -> None:
            self.sleeps.append(seconds)
            clock_state[0] += seconds

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                rate_interval=0.2,
                allowed_hosts=("pubchem.ncbi.nlm.nih.gov",),
            ),
            opener=opener,
            sleep=sleep,
            clock=clock,
        )
        return PubChemAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_unique_and_ambiguous_name_resolution_preserve_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            unique = adapter.resolve_name("aspirin")
            self.assertEqual(unique.cids, (2244,))
            self.assertFalse(unique.ambiguous)
            ambiguous = adapter.resolve_name("caffeine")
            self.assertEqual(ambiguous.cids, (2519, 9999))
            self.assertTrue(ambiguous.ambiguous)
            missing = adapter.resolve_name("unknown")
            self.assertTrue(missing.unresolved)
            self.assertEqual(missing.cids, ())

    def test_property_metadata_and_cache_hit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            first = adapter.search(SourceQuery("aspirin"))[0]
            metadata = adapter.metadata(first)
            self.assertEqual(metadata["cid"], 2244)
            self.assertEqual(metadata["inchikey"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
            self.assertFalse(metadata["cached"])
            calls_before = len(self.calls)
            repeat = adapter.metadata(first)
            self.assertTrue(repeat["cached"])
            self.assertEqual(len(self.calls), calls_before)

    def test_rate_interval_is_enforced_by_network_client(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            adapter.search(SourceQuery("aspirin"))
            adapter.search(SourceQuery("caffeine"))
            self.assertTrue(self.sleeps)
            self.assertGreaterEqual(self.sleeps[0], 0.2)

    def test_direct_cid_and_no_binary_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("CID:2244"))[0]
            self.assertEqual(candidate.accession, "2244")
            self.assertEqual(adapter.list_assets(candidate), ())

    def test_config_rejects_fast_rate_and_invalid_fetch(self) -> None:
        with self.assertRaises(AdapterError):
            PubChemConfig(rate_interval=0.1)
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("CID:2244"))[0]
            with self.assertRaises(AdapterError):
                adapter.fetch(
                    candidate,
                    AssetDescriptor(
                        asset_id="none",
                        source_id=candidate.source_id,
                        url="https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244",
                        asset_type="BINARY",
                        accession="2244",
                        sha256=None,
                        size_bytes=None,
                        license="PUBLIC-DOMAIN",
                    ),
                    Path("data/no-binary"),
                )


if __name__ == "__main__":
    unittest.main()
