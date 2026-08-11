"""Fixture-backed citation and linked-resource expansion tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.expansion import ExpansionError, ExpansionRunner
from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.policy import SourcePolicyEngine


class ExpansionTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]

    def _runner(self, root: Path) -> ExpansionRunner:
        return ExpansionRunner(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            seed_path=self.project_root / "registry/search_candidates.jsonl",
            fixture_path=self.project_root / "tests/fixtures/expansion/expansion_results.json",
        )

    def test_depth_two_expansion_deduplicates_targets_and_preserves_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._runner(Path(temporary)).run("development", depth=2)
            self.assertEqual(summary.seed_candidates, 14)
            self.assertEqual(summary.raw_edges, 44)
            self.assertEqual(summary.unique_targets, 17)
            self.assertEqual(summary.admitted, 16)
            self.assertEqual(summary.quarantined, 1)
            edge_ledger = AppendOnlyJSONL(Path(temporary) / "registry/expansion_edges.jsonl")
            run_ledger = AppendOnlyJSONL(Path(temporary) / "reports/expansion_runs.jsonl")
            edge_ledger.validate()
            run_ledger.validate()
            rows = [
                json.loads(line)
                for line in edge_ledger.path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 17)
            self.assertEqual(len({row["target_key"] for row in rows}), 17)
            self.assertTrue(all(row["locked_test_accessed"] is False for row in rows))

    def test_rerun_does_not_duplicate_edge_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = self._runner(Path(temporary))
            runner.run("development", depth=2)
            runner.run("development", depth=2)
            rows = (
                Path(temporary, "registry/expansion_edges.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            self.assertEqual(len(rows), 17)

    def test_depth_scope_and_malformed_edges_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = self._runner(Path(temporary))
            with self.assertRaisesRegex(ExpansionError, "scope"):
                runner.run("validation", depth=2)
            with self.assertRaisesRegex(ExpansionError, "depth"):
                runner.run("development", depth=3)
            value = json.loads(
                (self.project_root / "tests/fixtures/expansion/expansion_results.json").read_text(
                    encoding="utf-8"
                )
            )
            value["edges"]["europe_pmc:PMID:EXP-001"][0].pop("url")
            bad_path = Path(temporary) / "bad_expansion.json"
            bad_path.write_text(json.dumps(value), encoding="utf-8")
            bad_runner = ExpansionRunner(
                Path(temporary),
                SourcePolicyEngine.from_yaml(self.project_root),
                seed_path=self.project_root / "registry/search_candidates.jsonl",
                fixture_path=bad_path,
            )
            with self.assertRaisesRegex(ExpansionError, "no URL"):
                bad_runner.run("development", depth=2)


if __name__ == "__main__":
    unittest.main()
