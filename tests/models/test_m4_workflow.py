import json
from pathlib import Path

import pytest

from biointerfaceos.m4_workflow import M4Error, M4Workflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m4_fit_checks_simplex_zeros_sensitivity_and_toy_recovery(tmp_path: Path) -> None:
    summary = M4Workflow(_root(), output_root=tmp_path / "m4").run()

    assert summary.rows == 16
    assert summary.train == 8
    assert summary.validation == 8
    assert summary.alternatives == 2
    assert summary.best_rmse >= 0.0
    assert summary.toy_recovery is True
    assert summary.resumed == 0

    simplex = json.loads((tmp_path / "m4" / "simplex_audit.json").read_text())
    assert simplex["all_simplex_sums_one"] is True
    zero = json.loads((tmp_path / "m4" / "zero_audit.json").read_text())
    assert zero["zero_mask_preserved"] is True
    assert zero["raw_zero_rows"] == 2
    results = json.loads((tmp_path / "m4" / "m4_results.json").read_text())
    assert {row["alternative"] for row in results["alternatives"]} == {
        "raw_zero_floor",
        "pseudocount",
    }
    comparison = json.loads((tmp_path / "m4" / "m4_comparison.json").read_text())
    assert "m4_not_worse_than_m3" in comparison
    toy = json.loads((tmp_path / "m4" / "toy_recovery.json").read_text())
    assert toy["status"] == "PASSED"


def test_m4_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = M4Workflow(_root(), output_root=tmp_path / "m4")
    first = workflow.run()
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_m4_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(M4Error, match="--fixture is required"):
        M4Workflow(_root(), output_root=tmp_path / "m4").run(fixture=False)
