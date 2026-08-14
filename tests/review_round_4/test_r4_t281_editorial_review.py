"""Contract tests for the post-T280 evidence-bound editorial review."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_t281_scorecard_is_hard_gated_by_external_evidence() -> None:
    review = json.loads(
        (ROOT / "docs/review_round_4/R4_T281_POST_T280_MULTI_AGENT_EDITORIAL_REVIEW_20260815.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["primary_route"] == "T195"
    assert review["module_scores"]["data_compatibility_and_sample_foundation"] == 90
    assert review["module_scores"]["models_ablation_ood_uncertainty"] == 84
    assert review["arithmetic_mean"] == 46.0
    assert all(value is False for value in review["hard_gate_state"].values())
    assert review["decision"] == "MAJOR_REVISION"

