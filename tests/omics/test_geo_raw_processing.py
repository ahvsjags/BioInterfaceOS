from pathlib import Path

import pytest

from biointerfaceos.geo_raw_processing import (
    GeoRawProcessingError,
    GeoRawProcessingWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_geo_raw_processing_recovers_expected_counts(tmp_path: Path) -> None:
    summary = GeoRawProcessingWorkflow(_root(), output_root=tmp_path / "geo_raw").run()

    assert summary.studies_attempted == 1
    assert summary.studies_passed == 1
    assert summary.genes == 2
    assert summary.samples == 4
    assert summary.pairs == 18
    assert summary.matched_pairs == 16
    assert summary.unmatched_pairs == 2
    assert summary.resumed == 0
    assert summary.receipt_path.is_file()

    counts = (tmp_path / "geo_raw" / "raw_counts.json").read_text(encoding="utf-8")
    assert '"GENE1":4' in counts
    assert '"GENE2":1' in counts


def test_geo_raw_processing_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = GeoRawProcessingWorkflow(_root(), output_root=tmp_path / "geo_raw")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_geo_raw_processing_requires_raw_mode(tmp_path: Path) -> None:
    with pytest.raises(GeoRawProcessingError, match="only raw mode"):
        GeoRawProcessingWorkflow(_root(), output_root=tmp_path / "geo_raw").run(mode="processed")
