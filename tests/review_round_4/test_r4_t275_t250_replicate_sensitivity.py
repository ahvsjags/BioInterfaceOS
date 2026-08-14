"""Contract tests for T275 T250 technical-replicate sensitivity."""

from pathlib import Path

from biointerfaceos.r4_t275_t250_replicate_sensitivity import R4T275T250ReplicateSensitivityWorkflow

ROOT = Path(__file__).parents[2]


def test_t275_is_explicitly_post_fit_and_not_submission_ready() -> None:
    workflow = R4T275T250ReplicateSensitivityWorkflow(
        ROOT,
        output_root=ROOT / ".tmp-t275-contract",
    )
    assert workflow.output_root.is_relative_to(ROOT)
    assert workflow.T250_OUTPUT.endswith("t250_four_lab_common_target_execution/v1.0.0")


def test_t275_rejects_non_strict_execution() -> None:
    workflow = R4T275T250ReplicateSensitivityWorkflow(
        ROOT,
        output_root=ROOT / ".tmp-t275-contract",
    )
    try:
        workflow.run(strict=False)
    except RuntimeError as error:
        assert "--strict" in str(error)
    else:
        raise AssertionError("T275 must require strict execution")
