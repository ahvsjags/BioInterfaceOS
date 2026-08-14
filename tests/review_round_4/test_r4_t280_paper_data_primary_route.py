"""Contract tests for the T280 paper-data route decision."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_t280_selects_t195_as_redistributable_primary() -> None:
    decision = json.loads(
        (ROOT / "docs/data/R4_T280_PAPER_DATA_PRIMARY_ROUTE_DECISION_20260815.json").read_text(
            encoding="utf-8"
        )
    )
    primary = decision["primary_route"]
    assert decision["status"] == "FROZEN_PRIMARY_ROUTE_WITH_EXPLICIT_SECONDARY_SENSITIVITIES"
    assert primary["task"] == "T195"
    assert primary["laboratory_anchor_count"] == 3
    assert primary["common_target_count"] == 9
    assert primary["raw_observation_count"] == 809
    assert primary["source_licenses"] == ["CC-BY-4.0", "CC0", "CC0"]


def test_t280_keeps_secondary_routes_separate_and_gates_closed() -> None:
    decision = json.loads(
        (ROOT / "docs/data/R4_T280_PAPER_DATA_PRIMARY_ROUTE_DECISION_20260815.json").read_text(
            encoding="utf-8"
        )
    )
    assert [route["task"] for route in decision["secondary_routes"]] == ["T265", "T193", "T277"]
    assert all(value is False for value in decision["required_external_gates"].values())
    assert len(decision["non_pooling_rules"]) == 4

