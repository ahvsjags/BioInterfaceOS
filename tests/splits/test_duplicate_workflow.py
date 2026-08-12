import json
from pathlib import Path

import pytest

from biointerfaceos.duplicate_workflow import (
    DuplicateDetectionError,
    DuplicateDetectionWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_duplicate_workflow_detects_all_methods_without_cross_split_duplicates(
    tmp_path: Path,
) -> None:
    summary = DuplicateDetectionWorkflow(_root(), output_root=tmp_path / "duplicates").run()

    assert summary.items == 10
    assert summary.exact_edges == 1
    assert summary.composition_edges == 1
    assert summary.structure_edges == 1
    assert summary.text_edges == 1
    assert summary.review_edges == 1
    assert summary.cross_split_duplicates == 0
    assert summary.resumed == 0

    edges = json.loads((tmp_path / "duplicates" / "duplicate_edges.json").read_text())
    assert {edge["method"] for edge in edges["edges"]} == {
        "exact",
        "composition",
        "structure",
        "text",
    }
    receipt = json.loads((tmp_path / "duplicates" / "processing_receipt.json").read_text())
    assert receipt["thresholds_tuned_on_split_labels"] is False


def test_duplicate_workflow_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = DuplicateDetectionWorkflow(_root(), output_root=tmp_path / "duplicates")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_duplicate_workflow_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(DuplicateDetectionError, match="--fixture is required"):
        DuplicateDetectionWorkflow(_root(), output_root=tmp_path / "duplicates").run(fixture=False)
