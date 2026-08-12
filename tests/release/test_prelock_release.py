import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from biointerfaceos.prelock_release_workflow import PrelockReleaseError, PrelockReleaseWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_prelock_release_freezes_signature_and_resumes(tmp_path: Path) -> None:
    workflow = PrelockReleaseWorkflow(_root(), output_root=tmp_path / "release")
    first = workflow.run(fixture=True, strict=False, now=datetime(2026, 8, 12, tzinfo=UTC))
    assert first.release_id == "bioif-internal-prelock-v1.0.0"
    assert first.input_count == 25
    assert first.claim_count == 24
    assert first.manuscript_count == 3
    assert first.figure_count == 15
    assert first.authorization_scope == "evaluator_only"
    assert first.lockbox_accessed is False
    assert first.resumed == 0
    verified = workflow.verify()
    assert verified.signature == first.signature
    second = workflow.run(fixture=True, strict=False, now=datetime(2026, 8, 12, tzinfo=UTC))
    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()
    authorization = json.loads((tmp_path / "release" / "evaluator_authorization.json").read_text())
    assert authorization["scope"] == "evaluator_only"
    assert authorization["not_for_development"] is True


def test_prelock_release_rejects_checksum_mutation(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/release/prelock_fixture.json").read_text())
    fixture["inputs"][0]["sha256"] = "0" * 64
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(PrelockReleaseError, match="checksum differs"):
        PrelockReleaseWorkflow(
            _root(), fixture_path=fixture_path, output_root=tmp_path / "release"
        ).run()


def test_prelock_release_rejects_tampering(tmp_path: Path) -> None:
    workflow = PrelockReleaseWorkflow(_root(), output_root=tmp_path / "release")
    workflow.run()
    path = tmp_path / "release" / "release_manifest.json"
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(PrelockReleaseError, match="immutable pre-lock artifact differs"):
        workflow.run()


def test_prelock_release_rejects_dirty_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow = PrelockReleaseWorkflow(_root(), output_root=tmp_path / "release")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, " M dirty\n", ""),
    )
    with pytest.raises(PrelockReleaseError, match="clean working tree"):
        workflow.run(strict=True)


def test_prelock_release_rejects_development_authorization(tmp_path: Path) -> None:
    fixture = json.loads((_root() / "tests/fixtures/release/prelock_fixture.json").read_text())
    fixture["preregistration"]["lockbox_access"] = "development"
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(PrelockReleaseError, match="authorization boundary"):
        PrelockReleaseWorkflow(
            _root(), fixture_path=fixture_path, output_root=tmp_path / "release"
        ).run()


def test_prelock_release_rejects_signature_tamper(tmp_path: Path) -> None:
    workflow = PrelockReleaseWorkflow(_root(), output_root=tmp_path / "release")
    workflow.run()
    path = tmp_path / "release" / "signature.json"
    signature = json.loads(path.read_text())
    signature["signature"] = "0" * 64
    path.write_text(json.dumps(signature), encoding="utf-8")
    with pytest.raises(PrelockReleaseError, match="signature mismatch"):
        workflow.verify()
