"""Fixture-backed initial search runner tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.policy import SourcePolicyEngine
from biointerfaceos.search_runner import SearchRunError, SearchRunner


class SearchRunnerTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]

    def _runner(self, root: Path) -> SearchRunner:
        return SearchRunner(
            root,
            SourcePolicyEngine.from_yaml(self.project_root),
            matrix_path=self.project_root / "configs/search_queries.yaml",
            fixture_path=self.project_root / "tests/fixtures/search/search_results.json",
        )

    def test_development_run_paginates_deduplicates_and_records_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._runner(Path(temporary)).run("development")
            self.assertEqual(summary.scope, "development")
            self.assertEqual(summary.query_blocks, 13)
            self.assertEqual(summary.pages, 15)
            self.assertEqual(summary.raw_hits, 17)
            self.assertEqual(summary.unique_candidates, 14)
            self.assertEqual(summary.admitted, 13)
            self.assertEqual(summary.quarantined, 1)
            self.assertEqual(len(summary.response_hashes), 15)
            run_ledger = AppendOnlyJSONL(Path(temporary) / "reports/search_runs.jsonl")
            candidate_ledger = AppendOnlyJSONL(Path(temporary) / "registry/search_candidates.jsonl")
            run_ledger.validate()
            candidate_ledger.validate()
            rows = [
                json.loads(line)
                for line in candidate_ledger.path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 14)
            self.assertEqual(
                len({row["candidate_id"] for row in rows}),
                14,
            )
            self.assertTrue(
                all(row["locked_test_accessed"] is False for row in rows) if rows else True
            )

    def test_validation_run_uses_only_validation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._runner(Path(temporary)).run("validation")
            self.assertEqual(summary.query_blocks, 9)
            self.assertEqual(summary.scope, "validation")
            self.assertEqual(summary.quarantined, 2)

    def test_invalid_scope_and_repeated_cursor_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = self._runner(Path(temporary))
            with self.assertRaisesRegex(SearchRunError, "scope"):
                runner.run("lockbox")
            fixture = json.loads(
                (self.project_root / "tests/fixtures/search/search_results.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture["results"]["epmc-train-01"]["pages"] = [
                {"cursor": "*", "next_cursor": "*", "hits": []}
            ]
            bad_path = Path(temporary) / "bad_results.json"
            bad_path.write_text(json.dumps(fixture), encoding="utf-8")
            bad_runner = SearchRunner(
                Path(temporary),
                SourcePolicyEngine.from_yaml(self.project_root),
                matrix_path=self.project_root / "configs/search_queries.yaml",
                fixture_path=bad_path,
            )
            with self.assertRaisesRegex(SearchRunError, "cursor"):
                bad_runner.run("development")


if __name__ == "__main__":
    unittest.main()
