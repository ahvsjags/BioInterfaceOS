import json
from pathlib import Path

import pytest

from biointerfaceos.link_workflow import LinkModalitiesError, LinkModalitiesWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_link_workflow_separates_direct_indirect_and_unmatched(tmp_path: Path) -> None:
    summary = LinkModalitiesWorkflow(_root(), output_root=tmp_path / "links").run()

    assert summary.links_attempted == 3
    assert summary.direct_links == 1
    assert summary.indirect_links == 1
    assert summary.unmatched_links == 1
    assert summary.candidate_cards == 2
    assert summary.resumed == 0

    pairing = json.loads((tmp_path / "links" / "pairing_audit.json").read_text())
    assert pairing["pseudo_pairs_created"] is False
    assert pairing["indirect_links_have_no_response_sample_ids"] is True
    direct = json.loads((tmp_path / "links" / "direct_strata.json").read_text())
    assert direct["links"][0]["matched_unit_id"] == "MU-001"


def test_link_workflow_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = LinkModalitiesWorkflow(_root(), output_root=tmp_path / "links")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_link_workflow_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(LinkModalitiesError, match="--fixture is required"):
        LinkModalitiesWorkflow(_root(), output_root=tmp_path / "links").run(fixture=False)
