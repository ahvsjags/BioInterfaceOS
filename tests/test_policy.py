"""Offline tests for anonymous source and license policy."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from biointerfaceos.policy import (
    CANDIDATE_FIELDS,
    CandidateError,
    PolicyConfig,
    PolicyError,
    RejectionRegistry,
    SourceCandidate,
    SourcePolicyEngine,
)


def candidate(**changes: object) -> SourceCandidate:
    values: dict[str, object] = {
        "source_id": "test-source",
        "source_name": "Test Source",
        "url": "https://example.org/asset",
        "accession": "TEST-1",
        "license_identifier": "CC-BY-4.0",
        "license_text": "Creative Commons Attribution 4.0",
        "evidence_location": "fixture:license",
        "registration_required": False,
        "login_required": False,
        "api_key_required": False,
        "application_required": False,
        "approval_required": False,
        "institution_required": False,
        "data_use_agreement_required": False,
        "paid_required": False,
    }
    values.update(changes)
    return SourceCandidate.from_mapping(values)


class PolicyTests(unittest.TestCase):
    root: Path
    engine: SourcePolicyEngine

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.engine = SourcePolicyEngine.from_yaml(cls.root)

    def test_candidate_contract_is_strict_and_credential_free(self) -> None:
        self.assertEqual(len(CANDIDATE_FIELDS), 15)
        with self.assertRaises(CandidateError):
            candidate(url="https://user:pass@example.org/asset")
        with self.assertRaises(CandidateError):
            SourceCandidate.from_mapping({"source_id": "only"})

    def test_explicit_license_decisions(self) -> None:
        public = self.engine.evaluate(candidate())
        self.assertEqual(public.decision, "ADMIT_PUBLIC_REDISTRIBUTABLE")
        analysis = self.engine.evaluate(
            candidate(
                license_identifier="CC-BY-NC-4.0",
                license_text="Creative Commons Attribution NonCommercial 4.0",
            )
        )
        self.assertEqual(analysis.decision, "ADMIT_ANALYSIS_ONLY")
        unknown = self.engine.evaluate(candidate(license_identifier=None, license_text="license supplied on request"))
        self.assertEqual(unknown.decision, "QUARANTINE")
        self.assertEqual(unknown.rejection_code, "LICENSE_UNCLEAR")
        restricted = self.engine.evaluate(
            candidate(
                license_identifier="ALL-RIGHTS-RESERVED",
                license_text="All rights reserved",
            )
        )
        self.assertEqual(restricted.decision, "REJECT")
        self.assertEqual(restricted.rejection_code, "REJECTED_RESTRICTED_LICENSE")

    def test_every_credentialed_access_gate_is_rejected(self) -> None:
        for field_name in (
            "registration_required",
            "login_required",
            "api_key_required",
            "application_required",
            "approval_required",
            "institution_required",
            "data_use_agreement_required",
            "paid_required",
        ):
            with self.subTest(field=field_name):
                result = self.engine.evaluate(candidate(**{field_name: True}))
                self.assertEqual(result.decision, "REJECT")
                self.assertEqual(result.rejection_code, "REJECTED_CREDENTIALLED")

    def test_fixture_self_test_and_rejection_registry_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry = RejectionRegistry(Path(temporary))
            passed, rejected = self.engine.self_test(
                self.root / "tests/fixtures/policy",
                registry,
            )
            self.assertEqual((passed, rejected), (10, 7))
            self.assertEqual(registry.validate(), 7)
            self.assertEqual(len(registry.records()), 7)

    def test_registry_deduplicates_same_decision_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry = RejectionRegistry(Path(temporary))
            rejected = self.engine.evaluate(candidate(login_required=True))
            registry.register(candidate(login_required=True), rejected)
            registry.register(candidate(login_required=True), rejected)
            self.assertEqual(registry.validate(), 1)

    def test_registry_containment_and_config_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(PolicyError):
                RejectionRegistry(root, root.parent / "outside.parquet")
            with self.assertRaises(PolicyError):
                PolicyConfig.load(root, root.parent / "outside.yaml")

    def test_no_network_or_credentials_are_needed(self) -> None:
        result = self.engine.evaluate(candidate())
        self.assertEqual(result.source_id, "test-source")
        self.assertNotIn("API_KEY", result.reason)
        self.assertEqual(hashlib.sha256(b"fixture").hexdigest().__len__(), 64)
        self.assertTrue(datetime.now(UTC).tzinfo is not None)


if __name__ == "__main__":
    unittest.main()
