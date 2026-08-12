import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.final_acceptance_workflow import FinalAcceptanceError, FinalAcceptanceWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_final_acceptance_requires_t114_only_active() -> None:
    gate = FinalAcceptanceWorkflow(_root())._task_gate()
    assert gate["status"] == "PASS"
    assert gate["current_task"] == "T114"
    assert gate["completed_or_waived_before_T114"] == 114


def test_final_acceptance_forbidden_paths_are_rejected() -> None:
    workflow = FinalAcceptanceWorkflow(_root())
    assert any("data/locked_test/" in part for part in workflow.FORBIDDEN_PARTS)
    assert any("data/raw/" in part for part in workflow.FORBIDDEN_PARTS)


def test_final_acceptance_rejects_tampered_input_fixture(tmp_path: Path) -> None:
    fixture = _json(_root() / "tests/fixtures/acceptance/final_fixture.json")
    fixture["inputs"][0]["sha256"] = "0" * 64
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    workflow = FinalAcceptanceWorkflow(_root(), fixture_path=path)
    with pytest.raises(FinalAcceptanceError, match="checksum differs"):
        workflow._verify_input_hashes(fixture)


def test_final_acceptance_rejects_existing_release(tmp_path: Path) -> None:
    output = tmp_path / "release"
    output.mkdir()
    workflow = FinalAcceptanceWorkflow(_root(), output_root=output)
    with pytest.raises(FinalAcceptanceError, match="already executed"):
        workflow._build_public_release({})


def test_final_acceptance_report_status_is_explicit() -> None:
    assert FinalAcceptanceWorkflow.ACCEPTANCE_ID == "bioif-final-acceptance-v1.0.0"
    assert FinalAcceptanceWorkflow.RELEASE_ID == "bioif-public-v1.0.0"
