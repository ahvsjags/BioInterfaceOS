from pathlib import Path

import pytest

from biointerfaceos.evidence_semantics import (
    EvidenceClass,
    EvidenceSemanticsError,
    forbidden_terms,
    metadata_for,
    normalize_contract_status,
    require_metadata,
)
from biointerfaceos.evidence_semantics_audit import EvidenceSemanticsAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_fixture_contract_statuses_are_not_scientific_labels() -> None:
    assert normalize_contract_status("CONTRACT_EXPECTATION_MET") == "CONTRACT_EXPECTATION_MET"
    assert normalize_contract_status("REPLICATED") == "CONTRACT_EXPECTATION_MET"
    assert "REPLICATED" not in normalize_contract_status("REPLICATED")


def test_fixture_wording_rejects_empirical_inference() -> None:
    findings = forbidden_terms(
        "The fixture provides an independent study with replicated empirical validation.",
        EvidenceClass.FIXTURE_TEST,
    )
    assert findings


def test_evidence_metadata_is_required_and_cannot_be_upgraded() -> None:
    evidence_class, claim_level = require_metadata(metadata_for(EvidenceClass.FIXTURE_TEST), "fixture")
    assert evidence_class is EvidenceClass.FIXTURE_TEST
    assert claim_level.value == metadata_for(EvidenceClass.FIXTURE_TEST)["allowed_claim_level"]
    with pytest.raises(EvidenceSemanticsError, match="missing or invalid"):
        require_metadata({}, "fixture")
    with pytest.raises(EvidenceSemanticsError, match="exceeds"):
        require_metadata(
            {
                "evidence_class": "FIXTURE_TEST",
                "allowed_claim_level": "EXTERNALLY_REPRODUCED",
            },
            "fixture",
        )


def test_audit_quarantines_legacy_claims_without_mutating_their_sources(
    tmp_path: Path,
) -> None:
    paper_path = _root() / "release/manuscripts/paper_a/paper_a.md"
    before = paper_path.read_bytes()
    workflow = EvidenceSemanticsAuditWorkflow(_root(), output_root=tmp_path / "audit")
    report = workflow.run(strict=True)
    assert report["status"] == "PASS_EVIDENCE_SEMANTICS_WITH_QUARANTINED_LEGACY_FIXTURES"
    assert report["blocking_findings"] == 0
    assert len(report["quarantined_historical_findings"]) == 1
    assert workflow.verify()["historical_sources_mutated"] is False
    assert paper_path.read_bytes() == before
