import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.submission_figure_qa_workflow import (
    SubmissionFigureQAError,
    SubmissionFigureQAWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_r2_suite_is_field_mapped_protocol_only_and_withdraws_legacy_figures(
    tmp_path: Path,
) -> None:
    workflow = SubmissionFigureQAWorkflow(_root(), output_root=tmp_path / "figures")
    receipt = workflow.run(strict=True)

    assert receipt["status"] == "PASS_R2_PROTOCOL_FIGURE_SUITE"
    assert receipt["figure_count"] == 3
    assert receipt["withdrawn_historical_figure_count"] == 15
    assert receipt["empirical_values_rendered"] is False
    assert workflow.verify()["field_mapped"] is True
    manifest = _json(tmp_path / "figures" / "figure_manifest.json")
    assert manifest["publication_status"] == "PROTOCOL_ONLY"
    assert len(manifest["figures"]) == 3
    assert len(_json(tmp_path / "figures" / "withdrawal_ledger.json")["withdrawals"]) == 15
    for figure in manifest["figures"]:
        svg = (tmp_path / "figures" / figure["svg"]).read_text(encoding="utf-8").lower()
        assert "scientific replication" not in svg
        assert "empirical validation" not in svg
        qa = _json(tmp_path / "figures" / figure["qa"])
        assert qa["geometry"]["overlaps"] == 0
        assert qa["geometry"]["label_clipping"] == 0
        assert qa["raster"]["png_width"] >= 3000
        assert qa["raster"]["png_height"] >= 1500
        assert qa["raster"]["embedded_pixels_per_meter_x"] == 23622
        assert qa["raster"]["embedded_pixels_per_meter_y"] == 23622
        assert qa["raster"]["embedded_resolution_unit"] == "meter"
    assert receipt["embedded_png_resolution_verified"] is True


def test_r2_suite_rejects_tampered_source_checksum() -> None:
    workflow = SubmissionFigureQAWorkflow(_root())
    _, _, figures = workflow._load_specs()
    data_path, _, flows = workflow._load_data()
    tampered = {**figures[0], "source": {**figures[0]["source"], "sha256": "0" * 64}}

    with pytest.raises(SubmissionFigureQAError, match="checksum"):
        workflow._validate_figure(tampered, flows, data_path)


def test_r2_suite_rejects_clipped_or_overlapping_geometry() -> None:
    workflow = SubmissionFigureQAWorkflow(_root())
    _, _, figures = workflow._load_specs()
    _, _, flows = workflow._load_data()
    figure_id = figures[0]["figure_id"]
    clipped = {
        **flows["EVIDENCE_BOUNDARY"],
        "nodes": [{**flows["EVIDENCE_BOUNDARY"]["nodes"][0], "x": 1}] + flows["EVIDENCE_BOUNDARY"]["nodes"][1:],
    }
    with pytest.raises(SubmissionFigureQAError, match="out of bounds"):
        workflow._geometry(figure_id, clipped)

    overlap = {
        **flows["EVIDENCE_BOUNDARY"],
        "nodes": [
            flows["EVIDENCE_BOUNDARY"]["nodes"][0],
            {**flows["EVIDENCE_BOUNDARY"]["nodes"][1], "x": 100},
        ]
        + flows["EVIDENCE_BOUNDARY"]["nodes"][2:],
    }
    with pytest.raises(SubmissionFigureQAError, match="overlap"):
        workflow._geometry(figure_id, overlap)


def test_r2_suite_is_one_shot_and_detects_output_tampering(tmp_path: Path) -> None:
    workflow = SubmissionFigureQAWorkflow(_root(), output_root=tmp_path / "figures")
    workflow.run(strict=True)
    with pytest.raises(SubmissionFigureQAError, match="already executed"):
        workflow.run(strict=True)
    manifest = _json(tmp_path / "figures" / "figure_manifest.json")
    output = tmp_path / "figures" / manifest["figures"][0]["svg"]
    output.chmod(0o644)
    output.write_text("<svg/>", encoding="utf-8")
    with pytest.raises(SubmissionFigureQAError, match="output hash"):
        workflow.verify()
