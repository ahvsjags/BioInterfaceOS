"""Mock-only ontology adapter tests."""

from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.sources.base import AdapterError, SourceQuery
from biointerfaceos.sources.ontology import OntologyAdapter, OntologyConfig


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


class OntologyTests(unittest.TestCase):
    project_root: ClassVar[Path]
    fixtures: ClassVar[dict[str, bytes]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/ontology"
        cls.fixtures = {path.stem: path.read_bytes() for path in fixture_root.glob("*.json")}

    def _adapter(self, root: Path) -> OntologyAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            url = request.full_url
            if "P04637" in url:
                body = self.fixtures["uniprot_P04637"]
            elif "GO%3A0008150" in url:
                body = self.fixtures["go_GO_0008150"]
            elif "GO%3A0030173" in url:
                body = self.fixtures["go_GO_0030173"]
            elif "R-HSA-199420" in url:
                body = self.fixtures["reactome_R-HSA-199420"]
            elif "CVCL_0030" in url and "/search/" not in url:
                body = self.fixtures["cell_CVCL_0030"]
            elif "/search/cell-line" in url:
                body = self.fixtures["cell_search_HeLa"]
            else:
                body = self.fixtures["missing"]
            return FakeResponse(body)

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                allowed_hosts=(
                    "rest.uniprot.org",
                    "www.ebi.ac.uk",
                    "reactome.org",
                    "api.cellosaurus.org",
                )
            ),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return OntologyAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_four_source_records_and_release_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            cases = (
                ("uniprot:P04637", "Cellular tumor antigen p53", "2026_02"),
                ("go:GO:0008150", "biological_process", "2026-01"),
                ("reactome:R-HSA-199420", "????? development", "96"),
                ("cellosaurus:CVCL_0030", "HeLa", "2026-06-01"),
            )
            for query, label, version in cases:
                metadata = adapter.metadata(adapter.search(SourceQuery(query))[0])
                self.assertEqual(metadata["label"], label)
                self.assertEqual(metadata["version"], version)
                self.assertEqual(len(metadata["response_sha256"]), 64)

    def test_obsolete_go_tracks_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("go:GO:0030173"))[0]
            metadata = adapter.metadata(candidate)
            self.assertTrue(metadata["obsolete"])
            self.assertEqual(metadata["replaced_by"], ["GO:0000139"])

    def test_ambiguous_cell_line_label_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidates = adapter.search(SourceQuery("cellosaurus:name:HeLa", limit=10))
            self.assertEqual(
                [candidate.accession for candidate in candidates],
                ["CVCL_0030", "CVCL_1276"],
            )

    def test_missing_identifier_and_config_are_explicit(self) -> None:
        with self.assertRaises(AdapterError):
            OntologyConfig(max_results=0)
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            with self.assertRaises(AdapterError):
                adapter.metadata(adapter.search(SourceQuery("go:GO:9999999"))[0])

    def test_no_binary_assets_and_unknown_source_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("uniprot:P04637"))[0]
            self.assertEqual(adapter.list_assets(candidate), ())
            with self.assertRaises(AdapterError):
                adapter.search(SourceQuery("unknown:ID1"))


if __name__ == "__main__":
    unittest.main()
