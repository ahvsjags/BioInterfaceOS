"""Mock-only GEO/SRA adapter tests."""

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
from biointerfaceos.sources.geo import GeoConfig, GeoSraAdapter


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


class GeoSraTests(unittest.TestCase):
    project_root: ClassVar[Path]
    soft: ClassVar[dict[str, bytes]]
    runinfo: ClassVar[bytes]

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        fixture_root = cls.project_root / "tests/fixtures/sources/geo"
        cls.soft = {
            accession: (fixture_root / f"{accession}.soft").read_bytes()
            for accession in ("GSE12345", "GSE99999")
        }
        cls.runinfo = (fixture_root / "SRR000001.runinfo.csv").read_bytes()

    def _adapter(self, root: Path) -> GeoSraAdapter:
        def opener(request: Any, *, timeout: float) -> FakeResponse:
            url = request.full_url
            if "/geo/query/acc.cgi" in url:
                accession = parse_qs(urlsplit(url).query)["acc"][0]
                return FakeResponse(self.soft[accession])
            if "/runinfo" in url:
                return FakeResponse(self.runinfo)
            return FakeResponse(b"raw")

        client = AnonymousHttpClient(
            root=root,
            config=NetworkConfig(
                allowed_hosts=(
                    "www.ncbi.nlm.nih.gov",
                    "ftp.ncbi.nlm.nih.gov",
                    "trace.ncbi.nlm.nih.gov",
                    "sra-download.ncbi.nlm.nih.gov",
                    "ftp.sra.ebi.ac.uk",
                )
            ),
            opener=opener,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
        return GeoSraAdapter(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            client=client,
        )

    def test_geo_metadata_maps_samples_sra_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("GSE12345"))[0]
            metadata = adapter.metadata(candidate)
            self.assertEqual(metadata["accession"], "GSE12345")
            self.assertEqual(metadata["samples"], ["GSM1001", "GSM1002"])
            self.assertEqual(metadata["sra_accessions"], ["SRP000001"])
            self.assertEqual(metadata["bioproject"], "PRJNA999")
            self.assertEqual(
                metadata["response_sha256"], hashlib.sha256(self.soft["GSE12345"]).hexdigest()
            )

    def test_processed_and_raw_assets_are_linked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("GSE12345"))[0]
            assets = adapter.list_assets(candidate)
            self.assertEqual(
                [asset.asset_type for asset in assets],
                ["SERIES_MATRIX", "SOFT", "SUPPLEMENTARY", "SRA_RAW"],
            )
            self.assertTrue(assets[0].sha256)
            self.assertTrue(assets[-1].url.startswith("https://sra-download.ncbi.nlm.nih.gov/"))

    def test_restricted_series_is_rejected_before_asset_access(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            candidate = adapter.search(SourceQuery("GSE99999"))[0]
            with self.assertRaises(AdapterPolicyError):
                adapter.metadata(candidate)
            with self.assertRaises(AdapterPolicyError):
                adapter.list_assets(candidate)

    def test_sra_run_metadata_and_checksum_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter = self._adapter(root)
            candidate = adapter.search(SourceQuery("SRR000001"))[0]
            metadata = adapter.metadata(candidate)
            self.assertEqual(metadata["study"], "SRP000001")
            self.assertEqual(
                metadata["response_sha256"],
                hashlib.sha256(self.runinfo).hexdigest(),
            )
            assets = adapter.list_assets(candidate)
            self.assertEqual(assets[0].asset_type, "SRA_RAW")
            asset = AssetDescriptor(
                asset_id="raw",
                source_id=candidate.source_id,
                url=assets[0].url,
                asset_type="SRA_RAW",
                accession="SRR000001",
                sha256=hashlib.sha256(b"raw").hexdigest(),
                size_bytes=3,
                license="PUBLIC-DOMAIN",
            )
            result = adapter.fetch(candidate, asset, Path("data/raw.sra"))
            self.assertEqual(result.path.read_bytes(), b"raw")

    def test_config_and_invalid_accession(self) -> None:
        with self.assertRaises(AdapterError):
            GeoConfig(max_runs=0)
        with tempfile.TemporaryDirectory() as temporary:
            adapter = self._adapter(Path(temporary))
            with self.assertRaises(AdapterError):
                adapter.search(SourceQuery("XYZ1"))


if __name__ == "__main__":
    unittest.main()
