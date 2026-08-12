import json
from pathlib import Path

from biointerfaceos.hypothesis_tournament_workflow import HypothesisTournamentWorkflow


def test_tournament_freezes_config_deduplicates_and_preserves_exploration() -> None:
    root = Path(__file__).parents[2]
    summary = HypothesisTournamentWorkflow(root).run(development=True)

    assert summary.candidates == 3
    assert summary.ranked == 2
    assert summary.duplicates_removed == 1
    assert summary.exclusions == 1
    assert summary.config_frozen is True
    assert summary.lockbox_clean is True
    assert summary.claims_auto_accepted is False
    assert summary.selected_pipeline == "preregistered_tournament"
    ranking = json.loads(
        (root / "reports/claims/tournament/hypothesis_ranking.json").read_text(encoding="utf-8")
    )
    assert all(row["status"] == "EXPLORATORY_RANKED" for row in ranking["ranked"])
    assert all(row["claim_accepted"] is False for row in ranking["ranked"])


def test_tournament_hash_and_lockbox_receipts_are_clean() -> None:
    root = Path(__file__).parents[2]
    HypothesisTournamentWorkflow(root).run(development=True)

    hashes = json.loads(
        (root / "reports/claims/tournament/preregistration_hash_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert hashes["frozen_before_primary"] is True
    assert hashes["config_hash"]
    lockbox = json.loads(
        (root / "reports/claims/tournament/lockbox_scan.json").read_text(encoding="utf-8")
    )
    assert lockbox["clean"] is True
    assert lockbox["findings"] == []


def test_tournament_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = HypothesisTournamentWorkflow(root).run(development=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = HypothesisTournamentWorkflow(root).run(development=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
