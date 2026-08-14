"""Regression tests for the T265 biological common-target route."""

from biointerfaceos.r4_t265_biological_common_target import (
    R4T265BiologicalCommonTargetWorkflow,
)


def test_t265_cluster_interval_is_deterministic() -> None:
    first = R4T265BiologicalCommonTargetWorkflow._cluster_interval([0.1, 0.2, 0.4], 20260814, 200)
    second = R4T265BiologicalCommonTargetWorkflow._cluster_interval([0.1, 0.2, 0.4], 20260814, 200)

    assert first == second
    assert first is not None
    assert first["cluster_count"] == 3
    assert first["lower_95"] <= first["mean"] <= first["upper_95"]
