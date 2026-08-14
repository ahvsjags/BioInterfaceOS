"""Tests for T123 resumable author-result staging without target promotion."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
from pathlib import Path
from urllib.request import Request

import pytest

from biointerfaceos.real_proteomics_acquisition import (
    RealProteomicsAcquisitionError,
    RealProteomicsAcquisitionWorkflow,
    TransferAsset,
)

ROOT = Path(__file__).resolve().parents[2]


class _Response:
    def __init__(self, body: bytes, *, status: int = 200, headers: dict[str, str] | None = None):
        self._stream = BytesIO(body)
        self.status = status
        self.headers = headers or {}
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def getcode(self) -> int:
        return self.status

    def close(self) -> None:
        self.closed = True


def _asset(
    *,
    expected_bytes: int | None,
    checksum: str,
    representation: str = "FILE_BYTES",
) -> TransferAsset:
    return TransferAsset(
        source_id="PRIDE-PXD017776",
        accession="PXD017776",
        asset_id="PXD017776:test",
        file_name="test.mzid.gz",
        relative_path="PXD017776/author_results/test.mzid.gz",
        url="https://ftp.pride.ebi.ac.uk/pride/data/archive/2020/02/PXD017776/test.mzid.gz",
        role="author_result",
        publisher_api_bytes=expected_bytes or 1,
        expected_bytes=expected_bytes,
        publisher_checksum=checksum,
        publisher_checksum_algorithm="SHA1",
        checksum_representation=representation,
        byte_verification=(
            "EXACT_FILE_BYTES"
            if expected_bytes is not None
            else "INFORMATIONAL_ONLY_PUBLISHER_API_SIZE_MISMATCH_OBSERVED"
        ),
    )


def test_transfer_manifest_binds_preflight_and_fixed_source_counts(tmp_path: Path) -> None:
    workflow = RealProteomicsAcquisitionWorkflow(ROOT, raw_root=tmp_path / "raw")

    manifest, assets = workflow._manifest()

    assert manifest["manifest_id"] == "bioif-r2-real-proteomics-transfer-manifest-v1.0.0"
    assert len(assets) == 27
    assert {asset.source_id for asset in assets} == {
        "PRIDE-PXD017776",
        "PRIDE-PXD052701",
        "PRIDE-PXD032162",
    }
    assert sum(asset.publisher_checksum is not None for asset in assets) == 16


def test_download_resumes_and_validates_a_publisher_sha1(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    body = b"verified-public-result"
    partial = raw_root / "PXD017776" / "author_results" / "test.mzid.gz.part"
    partial.parent.mkdir(parents=True)
    partial.write_bytes(body[:8])
    requests: list[Request] = []

    def opener(request: Request, *, timeout: float) -> _Response:
        requests.append(request)
        return _Response(
            body[8:],
            status=206,
            headers={"Content-Range": f"bytes 8-{len(body) - 1}/{len(body)}"},
        )

    workflow = RealProteomicsAcquisitionWorkflow(
        ROOT,
        raw_root=raw_root,
        opener=opener,
        sleep=lambda _: None,
    )
    record = workflow._download(_asset(expected_bytes=len(body), checksum=hashlib.sha1(body).hexdigest()))

    destination = raw_root / "PXD017776" / "author_results" / "test.mzid.gz"
    assert destination.read_bytes() == body
    assert record["publisher_checksum_verified"] is True
    assert record["local_sha256"] == hashlib.sha256(body).hexdigest()
    assert requests[0].get_header("Range") == "bytes=8-"


def test_download_recovers_when_an_expected_length_stream_ends_early(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    body = b"server-short-read-must-resume"
    requests: list[Request] = []

    def opener(request: Request, *, timeout: float) -> _Response:
        requests.append(request)
        if len(requests) == 1:
            return _Response(body[:9])
        return _Response(
            body[9:],
            status=206,
            headers={"Content-Range": f"bytes 9-{len(body) - 1}/{len(body)}"},
        )

    workflow = RealProteomicsAcquisitionWorkflow(
        ROOT,
        raw_root=raw_root,
        opener=opener,
        sleep=lambda _: None,
    )
    record = workflow._download(_asset(expected_bytes=len(body), checksum=hashlib.sha1(body).hexdigest()))

    assert record["bytes_on_disk"] == len(body)
    assert len(requests) == 2
    assert requests[1].get_header("Range") == "bytes=9-"


def test_download_checks_decompressed_gzip_sha1(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    payload = b"mzIdentML content"
    compressed = gzip.compress(payload)
    workflow = RealProteomicsAcquisitionWorkflow(ROOT, raw_root=raw_root)
    path = raw_root / "PXD017776" / "author_results" / "test.mzid.gz"
    path.parent.mkdir(parents=True)
    path.write_bytes(compressed)

    record = workflow._verify_path(
        path,
        _asset(
            expected_bytes=len(compressed),
            checksum=hashlib.sha1(payload).hexdigest(),
            representation="GZIP_DECOMPRESSED_BYTES",
        ),
    )

    assert record["publisher_checksum_verified"] is True


def test_verified_partial_with_no_exact_size_is_promoted_without_redownload(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    payload = b"complete gzip content despite a misleading API size"
    partial = raw_root / "PXD017776" / "author_results" / "test.mzid.gz.part"
    partial.parent.mkdir(parents=True)
    with gzip.open(partial, "wb") as stream:
        stream.write(payload)

    def opener(request: Request, *, timeout: float) -> _Response:
        raise AssertionError(f"unexpected redownload: {request.full_url}")

    workflow = RealProteomicsAcquisitionWorkflow(ROOT, raw_root=raw_root, opener=opener)
    record = workflow._download(
        _asset(
            expected_bytes=None,
            checksum=hashlib.sha1(payload).hexdigest(),
            representation="GZIP_DECOMPRESSED_BYTES",
        )
    )

    assert record["publisher_checksum_verified"] is True
    assert not partial.exists()


def test_stage_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RealProteomicsAcquisitionWorkflow(ROOT, raw_root=tmp_path / "raw")

    with pytest.raises(RealProteomicsAcquisitionError, match="requires --strict"):
        workflow.stage()
