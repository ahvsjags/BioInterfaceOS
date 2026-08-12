import json
from pathlib import Path

import pytest

from biointerfaceos.source_license_workflow import SourceLicenseError, SourceLicenseWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_source_scout_and_license_gate_recover_and_reject(tmp_path: Path) -> None:
    summary = SourceLicenseWorkflow(_root(), output_root=tmp_path / "source_license").run()

    assert summary.cases == 5
    assert summary.recovered == 2
    assert summary.rejected_or_quarantined == 3
    assert summary.evidence_complete is True
    assert summary.no_credentials_requested is True
    assert summary.agent_value == 0
    assert summary.resumed == 0

    gate = json.loads((tmp_path / "source_license" / "license_gate.json").read_text())
    codes = {row["rejection_code"] for row in gate["decisions"]}
    assert "REJECTED_CREDENTIALLED" in codes
    assert "REJECTED_RESTRICTED_LICENSE" in codes
    assert "LICENSE_UNCLEAR" in codes
    assert all(row["evidence_location"] for row in gate["decisions"])


def test_source_license_rejection_registry_is_deterministic(tmp_path: Path) -> None:
    workflow = SourceLicenseWorkflow(_root(), output_root=tmp_path / "source_license")
    first = workflow.run()
    registry_before = (tmp_path / "source_license" / "rejected_sources.parquet").read_bytes()
    second = workflow.run()

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == first.receipt_path.read_bytes()
    assert (
        tmp_path / "source_license" / "rejected_sources.parquet"
    ).read_bytes() == registry_before


def test_source_license_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(SourceLicenseError, match="--fixture is required"):
        SourceLicenseWorkflow(_root(), output_root=tmp_path / "source_license").run(fixture=False)
