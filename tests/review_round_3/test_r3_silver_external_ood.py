"""Unit tests for frozen R3 silver-source OOD target construction."""

from __future__ import annotations

import pytest

from biointerfaceos.r3_silver_external_ood import R3SilverExternalOODWorkflow


def _row(coordinate: str, value: str, eligible: str = "true") -> dict[str, str]:
    return {
        "measurement_batch_id": "PH_1_REP_1",
        "source_coordinate": coordinate,
        "author_numeric_value": value,
        "rank_target_eligible": eligible,
    }


def test_external_rank_target_uses_descending_midranks_and_excludes_ineligible_rows() -> None:
    rows = [
        _row("D12", "10"),
        _row("D10", "10"),
        _row("D11", "5"),
        _row("D13", "0", "false"),
    ]

    ranks = R3SilverExternalOODWorkflow._rank_percentiles(rows)

    assert ranks["PH_1_REP_1:D10"] == pytest.approx((0.75, 3))
    assert ranks["PH_1_REP_1:D12"] == pytest.approx((0.75, 3))
    assert ranks["PH_1_REP_1:D11"] == pytest.approx((0.0, 3))
    assert "PH_1_REP_1:D13" not in ranks
