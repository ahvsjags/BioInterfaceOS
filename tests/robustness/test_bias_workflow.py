import json
from pathlib import Path

from biointerfaceos.bias_workflow import BiasWorkflow


def test_bias_workflow_compares_models_and_downgrades_sensitive_claim(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = BiasWorkflow(root, output_root=tmp_path / "bias")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.rows == 8
    assert first.clusters == 4
    assert first.models == 4
    assert first.observed_rows == 5
    assert first.missing_rows == 3
    assert first.missing_mechanisms == 3
    assert first.interval_records == 4
    assert first.model_disagreement >= 0.05
    assert first.p_values_used is False
    assert first.claim_status == "DOWNGRADED_SELECTION_SENSITIVE"
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_bias_workflow_keeps_missingness_and_pvalue_policy_explicit(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = BiasWorkflow(root, output_root=tmp_path / "bias")
    workflow.run(fixture=True)

    missing = json.loads((tmp_path / "bias" / "missingness_audit.json").read_text(encoding="utf-8"))
    comparison = json.loads((tmp_path / "bias" / "model_comparison.json").read_text(encoding="utf-8"))
    assert missing["mechanism_counts"] == {"MCAR": 1, "MAR": 1, "MNAR": 1}
    assert missing["p_values_used"] is False
    assert all(row["p_values_used"] is False for row in comparison["models"].values())
