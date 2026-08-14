"""Contract tests for the T273 biological-unit-primary estimand."""

import json
from pathlib import Path

from biointerfaceos.r3_model_evaluation import _Observation
from biointerfaceos.r4_t273_biological_unit_primary import R4T273BiologicalUnitPrimaryWorkflow

ROOT = Path(__file__).parents[2]


def _observation(identifier: str, source: str, batch: str, target: float) -> _Observation:
    return _Observation(identifier, source, "P26038", "lab", batch, target, (1.0, 2.0, 3.0))


def test_t273_protocol_makes_biological_unit_primary() -> None:
    protocol = json.loads(
        (ROOT / "docs/data/R4_T273_BIOLOGICAL_UNIT_PRIMARY_PROTOCOL.json").read_text(encoding="utf-8")
    )
    assert protocol["nested_selection"]["method"].startswith("deterministic five-fold grouped")
    assert protocol["primary_estimand"]["cluster"] == "biological_unit_id"
    assert protocol["negative_control"]["alpha_selection_recomputed_permutation"] is True


def test_t273_inner_group_folds_are_unit_disjoint() -> None:
    workflow = R4T273BiologicalUnitPrimaryWorkflow(ROOT, output_root=ROOT / ".tmp-t273-contract")
    rows = [_observation(f"o{i}", "source", f"batch{i}", 0.1 + i) for i in range(10)]
    workflow._unit_by_observation = {row.target_observation_id: f"source::unit{i}" for i, row in enumerate(rows)}
    folds = workflow._group_folds(rows, 5)
    assert len(folds) == 5
    assert sum(len(units) for _, units in folds) == 10
    assert len(set().union(*(units for _, units in folds))) == 10
    assert all(units for _, units in folds)


def test_t273_primary_unit_metric_averages_batches_within_unit() -> None:
    workflow = R4T273BiologicalUnitPrimaryWorkflow(ROOT, output_root=ROOT / ".tmp-t273-contract")
    rows = [
        _observation("a1", "source", "a", 0.1),
        _observation("a2", "source", "a", 0.2),
        _observation("a3", "source", "a", 0.3),
        _observation("b1", "source", "b", 0.1),
        _observation("b2", "source", "b", 0.2),
        _observation("b3", "source", "b", 0.3),
        _observation("c1", "source", "c", 0.7),
        _observation("c2", "source", "c", 0.8),
        _observation("c3", "source", "c", 0.9),
    ]
    workflow._unit_by_observation = {
        "a1": "source::unit1",
        "a2": "source::unit1",
        "a3": "source::unit1",
        "b1": "source::unit1",
        "b2": "source::unit1",
        "b3": "source::unit1",
        "c1": "source::unit2",
        "c2": "source::unit2",
        "c3": "source::unit2",
    }
    _, unit_rows = workflow._batch_and_unit_metrics(
        rows,
        [0.1, 0.2, 0.3, 0.3, 0.2, 0.1, 0.7, 0.8, 0.9],
        minimum_proteins=3,
    )
    assert [row["biological_unit_id"] for row in unit_rows] == ["source::unit1", "source::unit2"]
    assert unit_rows[0]["measurement_batch_count"] == 2
    assert workflow._unit_summary(unit_rows)["mean_spearman"] is not None
