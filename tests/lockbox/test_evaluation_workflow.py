import json
from pathlib import Path

import pytest

from biointerfaceos.lockbox_evaluation_workflow import (
    LockboxEvaluationError,
    LockboxEvaluationWorkflow,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_one_shot_evaluation_seals_metadata_only_results(tmp_path: Path) -> None:
    workflow = LockboxEvaluationWorkflow(_root(), output_root=tmp_path / "evaluation")
    first = workflow.run(release="FROZEN_DEV", once=True)
    assert first.prediction_count == 5
    assert first.contract_matched == 2
    assert first.contract_contradicted == 1
    assert first.contract_indeterminate == 2
    assert first.abstentions == 2
    assert first.raw_values_written is False
    assert first.train_calls == 0
    assert first.tune_calls == 0
    verified = workflow.verify()
    assert verified.receipt_path.read_bytes() == first.receipt_path.read_bytes()
    assert "REPLICATED" not in (tmp_path / "evaluation" / "evaluation_results.json").read_text()
    assert "REFUTED" not in (tmp_path / "evaluation" / "evaluation_results.json").read_text()
    with pytest.raises(LockboxEvaluationError, match="already executed"):
        workflow.run(release="FROZEN_DEV", once=True)


def test_evaluation_rejects_wrong_release_or_non_once(tmp_path: Path) -> None:
    workflow = LockboxEvaluationWorkflow(_root(), output_root=tmp_path / "evaluation")
    with pytest.raises(LockboxEvaluationError, match="requires"):
        workflow.run(release="DEV", once=True)
    with pytest.raises(LockboxEvaluationError, match="requires"):
        workflow.run(release="FROZEN_DEV", once=False)


def test_evaluation_rejects_fixture_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/lockbox/evaluate_fixture.json").read_text())
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(LockboxEvaluationError, match="checksum differs"):
        LockboxEvaluationWorkflow(_root(), fixture_path=fixture_path, output_root=tmp_path / "evaluation").run(
            release="FROZEN_DEV", once=True
        )


def test_evaluation_rejects_forbidden_operation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/lockbox/evaluate_fixture.json").read_text())
    fixture["operations"] = ["verify_release", "train"]
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(LockboxEvaluationError, match="operation sequence"):
        LockboxEvaluationWorkflow(_root(), fixture_path=fixture_path, output_root=tmp_path / "evaluation").run(
            release="FROZEN_DEV", once=True
        )


def test_evaluation_rejects_tampered_sealed_result(tmp_path: Path) -> None:
    workflow = LockboxEvaluationWorkflow(_root(), output_root=tmp_path / "evaluation")
    workflow.run(release="FROZEN_DEV", once=True)
    path = tmp_path / "evaluation" / "evaluation_results.json"
    path.chmod(0o644)
    payload = json.loads(path.read_text())
    payload["rows"][0]["status"] = "INCONCLUSIVE"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(LockboxEvaluationError, match="hash mismatch"):
        workflow.verify()


def test_evaluation_rejects_protected_path_in_fixture(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/lockbox/evaluate_fixture.json").read_text())
    fixture["inputs"][0]["path"] = "data/locked_test/payload.json"
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(LockboxEvaluationError, match="protected payload path"):
        LockboxEvaluationWorkflow(_root(), fixture_path=fixture_path, output_root=tmp_path / "evaluation").run(
            release="FROZEN_DEV", once=True
        )
