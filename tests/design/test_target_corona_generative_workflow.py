import json
from pathlib import Path

from biointerfaceos.target_corona_generative_workflow import (
    TargetCoronaGenerativeWorkflow,
)


def test_target_corona_generator_beats_baseline_with_ood_gate(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = TargetCoronaGenerativeWorkflow(root, output_root=tmp_path / "generative")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.rows == 12
    assert first.groups == 4
    assert first.heldout == 4
    assert first.sufficiency_passed is True
    assert first.generator_attempted is True
    assert first.baseline_validity == 0.66666667
    assert first.generator_validity == 0.83333333
    assert first.novelty_gain >= 0.05
    assert first.pareto_gain == 1
    assert first.ood_uncertainty_delta < 0
    assert first.ablations == 3
    assert first.selected_method == "conditional_generator"
    assert first.fallback == 0
    assert first.abstentions == 2
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False

    comparison = json.loads(
        (tmp_path / "generative" / "validity_novelty_pareto.json").read_text(encoding="utf-8")
    )
    assert comparison["generator_beats_baseline"] is True


def test_target_corona_generator_waives_when_sufficiency_fails(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    fixture = json.loads(
        (root / "tests/fixtures/design/target_corona_generative_fixture.json").read_text(
            encoding="utf-8"
        )
    )
    fixture["support_rows"] = fixture["support_rows"][:2]
    fixture_path = tmp_path / "insufficient.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    summary = TargetCoronaGenerativeWorkflow(
        root,
        fixture_path=fixture_path,
        output_root=tmp_path / "fallback",
    ).run(fixture=True)

    assert summary.sufficiency_passed is False
    assert summary.generator_attempted is False
    assert summary.selected_method == "bo_style_baseline"
    assert summary.fallback == 1
