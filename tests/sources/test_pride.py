"""Mock-only PRIDE Archive adapter tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from typing import Any, ClassVar

from biointerfaceos.network import AnonymousHttpClient, NetworkConfig
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.sources.base import AdapterError, AdapterPolicyError, SourceQuery
from biointerfaceos.sources.pride import PrideAdapter, PrideConfig


class FakeResponse:
    def __init__(
        self,
        body: bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self._stream = BytesIO(body)
        self.status = status
        self.headers = headers or {}

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def close(self) -> None:
        return None

    def getcode(self) -> int:
        return self.status


class PrideTests(unittest.TestCase):
    project_root: ClassVar[Path]
    project: ClassVar[bytes]
    files: ClassVar[bytes]
    search: ClassVar[bytes]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/pride"
        cls.project = (fixture_root / "project_PXD000001.json").read_bytes()
        cls.files = (fixture_root / "files_PXD000001.json").read_bytes()
        cls.search = (fixture_root / "search_corona.json").read_bytes()

    def _adapter(self, root: Path) -> PrideAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            url = request.full_url
            if "/search/projects" in url:
                return FakeResponse(self.search)
            if url.endswith("/projects/PXD000001"):
                return FakeResponse(self.project)
            if url.endswith("/projects/files-path/PXD000001"):
                return FakeResponse(self.files)
            if request.get_header("Range") is not None:
                return FakeResponse(
                    b"rest",
                    status=206,
                    headers={"Content-Range": "bytes 4-7/*"},
                )
            return FakeResponse(b"rest")

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(allowed_hosts=("www.ebi.ac.uk", "ftp.pride.ebi.ac.uk")),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return PrideAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_project_search_metadata_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidates = adapter.search(SourceQuery("corona", limit=10))
            self.assertEqual(
                [candidate.accession for candidate in candidates],
                ["PXD000001", "PXD000002"],
            )
            self.assertEqual(candidates[0].license_identifier, "Creative Commons Public Domain (CC0)")
            self.assertIsNone(candidates[1].license_identifier)
            metadata = adapter.metadata(candidates[0])
            self.assertEqual(metadata["submission_date"], "2026-01-15")
            self.assertEqual(metadata["species"], ["Homo sapiens"])
            self.assertEqual(metadata["instruments"], ["Orbitrap Fusion"])
            self.assertEqual(metadata["response_sha256"], hashlib.sha256(self.project).hexdigest())

    def test_file_manifest_checksum_and_restricted_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("PXD000001"))[0]
            assets = adapter.list_assets(candidate)
            self.assertEqual([asset.asset_type for asset in assets], ["RESULT", "RAW"])
            self.assertEqual(assets[0].size_bytes, 13)
            self.assertEqual(assets[0].sha256, json.loads(self.files)["files"][0]["checksum"].lower())
            self.assertEqual(assets[1].size_bytes, 2000000000)
            self.assertTrue(assets[1].sha256)
            self.assertTrue(assets[1].url.startswith("https://ftp.pride.ebi.ac.uk/"))

    def test_no_license_candidate_is_rejected_before_file_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("corona"))[1]
            with self.assertRaises(AdapterPolicyError):
                adapter.metadata(candidate)
            with self.assertRaises(AdapterPolicyError):
                adapter.list_assets(candidate)

    def test_large_file_dry_run_and_checksum_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = self._adapter(root)
            candidate = adapter.search(SourceQuery("PXD000001"))[0]
            assets = adapter.list_assets(candidate)
            plan = adapter.dry_run(candidate, assets[1])
            self.assertTrue(plan["large_file"])
            self.assertFalse(plan["downloaded"])
            digest = hashlib.sha256(b"partrest").hexdigest()
            asset = type(assets[0])(
                asset_id="resume",
                source_id=candidate.source_id,
                url=assets[0].url,
                asset_type="RESULT",
                accession="PXD000001",
                sha256=digest,
                size_bytes=8,
                license="CC0",
            )
            (root / "data").mkdir()
            (root / "data/resume.part").write_bytes(b"part")
            result = adapter.fetch(candidate, asset, Path("data/resume"))
            self.assertEqual(result.path.read_bytes(), b"partrest")
            self.assertEqual(result.sha256, digest)

    def test_config_and_invalid_accession_are_rejected(self) -> None:
        with self.assertRaises(AdapterError):
            PrideConfig(page_size=0)
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            with self.assertRaises(AdapterError):
                adapter.search(SourceQuery("PXDbad"))


if __name__ == "__main__":
    unittest.main()
