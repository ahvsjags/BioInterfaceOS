"""Mock-only ChEMBL Web Services tests."""

from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.sources.base import AdapterError, SourceQuery
from biointerfaceos.sources.chembl import ChemblAdapter, ChemblConfig


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


class ChemblTests(unittest.TestCase):
    project_root: ClassVar[Path]
    fixtures: ClassVar[dict[str, bytes]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/chembl"
        cls.fixtures = {
            name: (fixture_root / name).read_bytes()
            for name in (
                "search_page_1.json",
                "search_page_2.json",
                "molecule_CHEMBL25.json",
                "molecule_CHEMBL1000.json",
                "status.json",
            )
        }

    def _adapter(self, root: Path) -> ChemblAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            url = request.full_url
            if "/status.json" in url:
                body = self.fixtures["status.json"]
            elif "offset=2" in url:
                body = self.fixtures["search_page_2.json"]
            elif "/molecule?" in url or "/molecule.json" in url:
                body = self.fixtures["search_page_1.json"]
            elif "/molecule/CHEMBL1000.json" in url:
                body = self.fixtures["molecule_CHEMBL1000.json"]
            elif "/molecule/CHEMBL25.json" in url:
                body = self.fixtures["molecule_CHEMBL25.json"]
            else:
                raise AssertionError(f"unexpected URL: {url}")
            return FakeResponse(body)

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                rate_interval=0.2,
                allowed_hosts=("www.ebi.ac.uk",),
            ),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return ChemblAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_pagination_preserves_parent_and_salt_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidates = adapter.search(SourceQuery("aspirin", limit=10))
            self.assertEqual(
                [candidate.accession for candidate in candidates],
                ["CHEMBL25", "CHEMBL999", "CHEMBL1000"],
            )

    def test_metadata_captures_structure_version_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("CHEMBL25"))[0]
            metadata = adapter.metadata(candidate)
            self.assertEqual(metadata["inchikey"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
            self.assertEqual(metadata["chembl_db_version"], "35")
            self.assertEqual(metadata["chembl_api_version"], "1.6.0")
            self.assertEqual(len(metadata["response_sha256"]), 64)
            self.assertEqual(len(metadata["status_response_sha256"]), 64)

    def test_missing_structure_fields_remain_null(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("CHEMBL1000"))[0]
            metadata = adapter.metadata(candidate)
            self.assertIsNone(metadata["canonical_smiles"])
            self.assertIsNone(metadata["inchi"])
            self.assertIsNone(metadata["inchikey"])

    def test_no_binary_assets_and_config_bounds(self) -> None:
        with self.assertRaises(AdapterError):
            ChemblConfig(max_pages=0)
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("CHEMBL25"))[0]
            self.assertEqual(adapter.list_assets(candidate), ())


if __name__ == "__main__":
    unittest.main()
