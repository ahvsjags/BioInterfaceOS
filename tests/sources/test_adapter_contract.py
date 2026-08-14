"""Offline contract tests for source adapters and fixture recording."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.sources import (
    AdapterPolicyError,
    AssetDescriptor,
    FixtureAdapter,
    FixtureHarness,
    SourceAdapter,
    SourceQuery,
)


def candidate(source_id: str = "fixture-source", *, login: bool = False) -> SourceCandidate:
    return SourceCandidate.from_mapping(
        {
            "source_id": source_id,
            "source_name": "Fixture Public Source",
            "url": "https://example.org/" + source_id,
            "accession": "FIX-001",
            "license_identifier": "CC-BY-4.0",
            "license_text": "Creative Commons Attribution 4.0",
            "evidence_location": "fixture:license",
            "registration_required": False,
            "login_required": login,
            "api_key_required": False,
            "application_required": False,
            "approval_required": False,
            "institution_required": False,
            "data_use_agreement_required": False,
            "paid_required": False,
        }
    )


class AdapterContractTests(unittest.TestCase):
    def _adapter(self, root: Path) -> tuple[FixtureAdapter, SourceCandidate, AssetDescriptor, bytes]:
        public = candidate()
        payload = b"fixture asset bytes"
        digest = hashlib.sha256(payload).hexdigest()
        asset = AssetDescriptor(
            asset_id="asset-1",
            source_id=public.source_id,
            url="https://example.org/asset-1",
            asset_type="JSON",
            accession="FIX-001",
            sha256=digest,
            size_bytes=len(payload),
            license="CC-BY-4.0",
        )
        adapter = FixtureAdapter(
            root,
            SourcePolicyEngine.from_yaml(Path(__file__).resolve().parents[2]),
            [public],
            {public.source_id: {"title": "fixture"}},
            {public.source_id: [asset]},
            {asset.asset_id: payload},
        )
        return adapter, public, asset, payload

    def test_four_method_contract_and_deterministic_search(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter, public, asset, _ = self._adapter(root)
            self.assertIsInstance(adapter, SourceAdapter)
            self.assertEqual(adapter.name, "fixture")
            self.assertEqual(adapter.search(SourceQuery("FIXTURE")), (public,))
            self.assertEqual(adapter.metadata(public)["title"], "fixture")
            self.assertEqual(adapter.list_assets(public), (asset,))

    def test_fetch_is_atomic_and_hash_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter, public, asset, payload = self._adapter(root)
            result = adapter.fetch(public, asset, Path("data/fetched.json"))
            self.assertEqual(result.sha256, hashlib.sha256(payload).hexdigest())
            self.assertEqual(result.path.read_bytes(), payload)
            self.assertFalse((root / "data/.fetched.json.part").exists())

    def test_policy_gate_rejects_credentialed_candidate_for_metadata_assets_and_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            adapter, _, asset, _ = self._adapter(root)
            rejected = candidate("login-source", login=True)
            for action in (
                lambda: adapter.metadata(rejected),
                lambda: adapter.list_assets(rejected),
                lambda: adapter.fetch(rejected, asset, Path("data/rejected")),
            ):
                with self.assertRaises(AdapterPolicyError):
                    action()

    def test_fixture_harness_strips_private_volatile_and_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harness = FixtureHarness(root, "fixture")
            payload = {
                "title": "stable",
                "date": "volatile",
                "headers": {"Authorization": "secret", "ETag": "volatile"},
                "nested": {"api_key": "private", "value": 1},
            }
            first = harness.record("response", payload)
            first_bytes = first.read_bytes()
            second = harness.record("response", payload)
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, second.read_bytes())
            loaded = json.loads(first.read_text())
            self.assertEqual(loaded, {"nested": {"value": 1}, "title": "stable"})
            self.assertEqual(harness.load("response"), loaded)


if __name__ == "__main__":
    unittest.main()
