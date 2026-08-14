"""Contract tests for the T277 replicate-aware T250 refit."""

import json
from pathlib import Path

from biointerfaceos.r4_t277_t250_replicate_aware_refit import (
    R4T277T250ReplicateAwareRefitWorkflow,
)

ROOT = Path(__file__).parents[2]


def test_t277_contract_is_exploratory_and_pre_model() -> None:
    workflow = R4T277T250ReplicateAwareRefitWorkflow(
        ROOT,
        output_root=ROOT / ".tmp-t277-contract",
    )
    registry = json.loads(
        (ROOT / workflow.REGISTRY_RELATIVE).read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (ROOT / workflow.PROTOCOL_RELATIVE).read_text(encoding="utf-8")
    )
    assert workflow.output_root.is_relative_to(ROOT)
    assert registry["scientific_submission_ready"] is False
    assert protocol["technical_replicate_policy"]["applied_before"] == [
        "outer laboratory split",
        "inner alpha selection",
        "model fitting",
        "negative-control permutation",
    ]
    assert protocol["negative_control"]["selection_reexecution_per_resample"] is True


def test_t277_rejects_non_strict_execution() -> None:
    workflow = R4T277T250ReplicateAwareRefitWorkflow(
        ROOT,
        output_root=ROOT / ".tmp-t277-contract",
    )
    try:
        workflow.run(strict=False)
    except RuntimeError as error:
        assert "--strict" in str(error)
    else:
        raise AssertionError("T277 must require strict execution")
