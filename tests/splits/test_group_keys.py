import json
from pathlib import Path

import pytest

from biointerfaceos.group_keys import GroupKeysError, GroupKeysWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_group_keys_are_deterministic_and_collision_audited(tmp_path: Path) -> None:
    summary = GroupKeysWorkflow(_root(), output_root=tmp_path / "groups").run()

    assert summary.rows == 6
    assert summary.unique_study == 6
    assert summary.unique_paper_families == 3
    assert summary.unique_projects == 4
    assert summary.collisions == 2
    assert summary.review_rows == 2
    assert summary.resumed == 0

    groups = json.loads((tmp_path / "groups" / "group_keys.json").read_text())
    unknown = next(row for row in groups["rows"] if row["record_id"] == "ROW-004")
    assert unknown["lab_group_key"] == "LAB_UNKNOWN:FAMILY_002"
    assert unknown["material_group_key"] == "MATERIAL_UNKNOWN:NANOCOAT_X"
    assert unknown["date_group_key"] == "DATE_UNKNOWN"
    collisions = json.loads((tmp_path / "groups" / "collision_audit.json").read_text())
    assert {row["collision_type"] for row in collisions["collisions"]} == {
        "paper_family_crosses_split",
        "project_crosses_split",
    }


def test_group_keys_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = GroupKeysWorkflow(_root(), output_root=tmp_path / "groups")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_group_keys_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(GroupKeysError, match="--fixture is required"):
        GroupKeysWorkflow(_root(), output_root=tmp_path / "groups").run(fixture=False)
