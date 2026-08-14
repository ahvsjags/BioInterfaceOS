"""Unit tests for frozen R3 model-evaluation numerical primitives."""

from __future__ import annotations

import numpy as np
import pytest

from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationError,
    R3ModelEvaluationWorkflow,
    _Observation,
)


def _observation(index: int, target: float, batch: str) -> _Observation:
    return _Observation(
        target_observation_id=f"R3:TEST:{index}",
        source_id="TEST_SOURCE",
        canonical_accession=f"P{index:05d}",
        laboratory_anchor="TEST_LAB",
        measurement_batch_id=batch,
        target=target,
        feature_values=(float(index), float(index % 2)),
    )


def test_spearman_handles_ties_and_constant_predictions() -> None:
    assert R3ModelEvaluationWorkflow._spearman([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) == pytest.approx(-1.0)
    assert R3ModelEvaluationWorkflow._spearman([1.0, 1.0, 2.0], [1.0, 1.0, 2.0]) == pytest.approx(1.0)
    assert R3ModelEvaluationWorkflow._spearman([1.0, 2.0, 3.0], [0.5, 0.5, 0.5]) is None


def test_ridge_standardizes_only_training_partition_and_predicts() -> None:
    training = [_observation(index, float(index), "B1") for index in range(1, 7)]
    testing = [_observation(7, 7.0, "B2"), _observation(8, 8.0, "B2")]

    model = R3ModelEvaluationWorkflow._fit_ridge(training, (0,), alpha=0.01)
    prediction = R3ModelEvaluationWorkflow._predict_ridge(model, testing)

    assert np.all(np.isfinite(prediction))
    assert prediction[1] > prediction[0]
    assert model["means"][0] == pytest.approx(3.5)


def test_batch_metrics_rejects_small_batch() -> None:
    observations = [_observation(index, float(index), "B1") for index in range(1, 10)]

    with pytest.raises(R3ModelEvaluationError, match="fewer than 10 proteins"):
        R3ModelEvaluationWorkflow._batch_metrics(
            observations, [float(index) for index in range(1, 10)], minimum_proteins=10
        )


def test_cluster_bootstrap_is_seed_deterministic() -> None:
    first = R3ModelEvaluationWorkflow._bootstrap([0.1, 0.2, 0.3], resamples=200, seed=11)
    second = R3ModelEvaluationWorkflow._bootstrap([0.1, 0.2, 0.3], resamples=200, seed=11)

    assert first == second
    assert first["lower_95"] <= first["upper_95"]
