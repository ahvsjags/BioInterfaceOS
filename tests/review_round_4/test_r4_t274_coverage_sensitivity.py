"""Contract tests for T274 coverage sensitivity."""

import json
from pathlib import Path

from biointerfaceos.r4_t274_coverage_sensitivity import R4T274CoverageSensitivityWorkflow

ROOT = Path(__file__).parents[2]


def test_t274_uses_fixed_panel_and_descriptive_missingness_boundary() -> None:
    protocol = json.loads(
        (ROOT / "docs/data/R4_T273_BIOLOGICAL_UNIT_PRIMARY_PROTOCOL.json").read_text(encoding="utf-8")
    )
    assert protocol["coverage_missingness"]["sensitivity_required"] is True
    assert len(protocol["target_freeze"]["common_targets"]) == 5


def test_t274_workflow_paths_are_root_bound() -> None:
    workflow = R4T274CoverageSensitivityWorkflow(ROOT, output_root=ROOT / ".tmp-t274-contract")
    assert workflow.output_root.is_relative_to(ROOT)
