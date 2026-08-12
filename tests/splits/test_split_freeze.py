import json
from pathlib import Path

import pytest

from biointerfaceos.split_freeze import SplitFreezeError, SplitFreezeWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_split_freeze_applies_dates_groups_and_blacklist(tmp_path: Path) -> None:
    summary = SplitFreezeWorkflow(_root(), output_root=tmp_path / "frozen").run()

    assert summary.candidates == 5
    assert summary.train == 2
    assert summary.validation == 1
    assert summary.excluded == 2
    assert summary.groups == 2
    assert summary.blacklisted_features == 10
    assert summary.resumed == 0

    split = json.loads((tmp_path / "frozen" / "split_manifest.json").read_text())
    assert split["status"] == "FROZEN_DEV"
    assert {row["split"] for row in split["rows"]} == {"train", "validation"}
    blacklist = json.loads((tmp_path / "frozen" / "feature_blacklist.json").read_text())
    assert "accession" in blacklist["features"]
    assert "outcome_value" not in blacklist["features"]
    leakage = json.loads((tmp_path / "frozen" / "leakage_audit.json").read_text())
    assert leakage["outcome_values_used"] is False
    assert leakage["lockbox_accessed"] is False


def test_split_freeze_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = SplitFreezeWorkflow(_root(), output_root=tmp_path / "frozen")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_split_freeze_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(SplitFreezeError, match="--fixture is required"):
        SplitFreezeWorkflow(_root(), output_root=tmp_path / "frozen").run(fixture=False)
