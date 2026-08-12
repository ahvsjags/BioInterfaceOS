"""Tests for the R2 external literature, comparator, and glossary gate."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from biointerfaceos.related_work_workflow import RelatedWorkError, RelatedWorkWorkflow

ROOT = Path(__file__).resolve().parents[2]


def _copy_literature_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    shutil.copytree(ROOT / "docs" / "literature", root / "docs" / "literature")
    return root


def test_related_work_packet_covers_r2_manuscript_scopes(tmp_path: Path) -> None:
    workflow = RelatedWorkWorkflow(ROOT, output_root=tmp_path / "related-work")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.citation_count == 12
    assert summary.comparator_count == 8
    assert summary.manuscript_scope_count == 2
    assert summary.glossary_term_count == 7
    assert receipt["historical_fixture_manuscripts_retroactively_cleared"] is False
    assert receipt["scientific_submission_ready"] is False


def test_related_work_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RelatedWorkWorkflow(ROOT, output_root=tmp_path / "related-work")

    with pytest.raises(RelatedWorkError, match="requires --strict"):
        workflow.run()


def test_related_work_rejects_unverified_scope_citation(tmp_path: Path) -> None:
    root = _copy_literature_root(tmp_path)
    mapping = json.loads(
        (root / "docs/literature/R2_MANUSCRIPT_COMPARATOR_MAP.json").read_text(encoding="utf-8")
    )
    mapping["manuscript_scopes"][0]["citation_keys"].append("NOT_A_VERIFIED_CITATION")
    map_path = root / "docs/literature/invalid-map.json"
    map_path.write_text(json.dumps(mapping), encoding="utf-8")
    workflow = RelatedWorkWorkflow(
        root,
        map_path=map_path,
        output_root=root / "related-work",
    )

    with pytest.raises(RelatedWorkError, match="unverified external reference"):
        workflow.run(strict=True)


def test_related_work_rejects_missing_glossary_boundary(tmp_path: Path) -> None:
    root = _copy_literature_root(tmp_path)
    glossary_path = root / "docs/literature/invalid-glossary.md"
    glossary = (root / "docs/literature/R2_OPERATIONAL_GLOSSARY.md").read_text(encoding="utf-8")
    glossary_path.write_text(
        glossary.replace("source_not_stated", "unit_was_not_given"), encoding="utf-8"
    )
    workflow = RelatedWorkWorkflow(
        root,
        glossary_path=glossary_path,
        output_root=root / "related-work",
    )

    with pytest.raises(RelatedWorkError, match="missing-unit comparability boundary"):
        workflow.run(strict=True)
