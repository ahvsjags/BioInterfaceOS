from pathlib import Path

import pytest

from biointerfaceos.geo_processing import GeoProcessingError, GeoProcessingWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_geo_processing_normalizes_ids_and_preserves_studies(tmp_path: Path) -> None:
    summary = GeoProcessingWorkflow(_root(), output_root=tmp_path / "geo").run()

    assert summary.studies_attempted == 2
    assert summary.studies_passed == 2
    assert summary.excluded_studies == 0
    assert summary.genes == 2
    assert summary.samples == 8
    assert summary.contrasts == 4
    assert summary.missing_cells == 0
    assert summary.resumed == 0
    assert summary.receipt_path.is_file()

    studies = (tmp_path / "geo" / "study_objects.json").read_text(encoding="utf-8")
    assert '"study_accession":"GSE12345"' in studies
    assert '"study_accession":"SRP000001"' in studies
    assert '"normalized_gene_id":"GENE1"' in studies


def test_geo_processing_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = GeoProcessingWorkflow(_root(), output_root=tmp_path / "geo")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_geo_processing_rejects_unimplemented_mode(tmp_path: Path) -> None:
    with pytest.raises(GeoProcessingError, match="only processed mode"):
        GeoProcessingWorkflow(_root(), output_root=tmp_path / "geo").run(mode="raw")
