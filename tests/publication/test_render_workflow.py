import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.publication_render_workflow import (
    PublicationRenderError,
    PublicationRenderWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_render_covers_all_figures_tables_and_statuses(tmp_path: Path) -> None:
    workflow = PublicationRenderWorkflow(_root(), output_root=tmp_path / "publication")
    receipt = workflow.run(strict=True)
    assert receipt["figures"] == 15
    assert receipt["tables"] == 18
    assert receipt["raster_dpi"] == 600
    assert receipt["manual_numeric_edits"] == 0
    workflow.verify()
    assert len(list((tmp_path / "publication" / "figures").glob("*.svg"))) == 15
    assert len(list((tmp_path / "publication" / "figures").glob("*.png"))) == 15
    predictions = (tmp_path / "publication" / "tables" / "paper_c_prelock_Table_2.md").read_text()
    assert "POSTLOCK_REPLICATED" in predictions
    assert "POSTLOCK_REFUTED" in predictions
    assert "POSTLOCK_INCONCLUSIVE" in predictions


def test_render_is_one_shot(tmp_path: Path) -> None:
    workflow = PublicationRenderWorkflow(_root(), output_root=tmp_path / "publication")
    workflow.run(strict=True)
    with pytest.raises(PublicationRenderError, match="already executed"):
        workflow.run(strict=True)


def test_render_rejects_missing_figure_source() -> None:
    paper = {"paper_id": "paper_a", "root": _root() / "release/manuscripts/paper_a"}
    with pytest.raises(PublicationRenderError, match="figure source is missing"):
        PublicationRenderWorkflow(_root())._source_path(paper, "missing_source.json")


def test_render_rejects_protected_path() -> None:
    with pytest.raises(PublicationRenderError, match="protected payload path"):
        PublicationRenderWorkflow(_root())._path("data/locked_test/payload.json", "fixture path")


def test_render_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = PublicationRenderWorkflow(_root(), output_root=tmp_path / "publication")
    workflow.run(strict=True)
    receipt_path = tmp_path / "publication" / "generation_receipt.json"
    receipt_path.chmod(0o644)
    receipt = _json(receipt_path)
    receipt["figures"] = 14
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(PublicationRenderError, match="coverage"):
        workflow.verify()
