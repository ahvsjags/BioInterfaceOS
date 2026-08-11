"""Evidence resolution and reverse trace tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.evidence_resolver import EvidenceResolutionError, EvidenceResolver
from biointerfaceos.ledgers import AppendOnlyJSONL


class EvidenceResolverTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _resolver(self, root: Path) -> EvidenceResolver:
        return EvidenceResolver(
            self.project_root,
            evidence_path=root / "evidence_table.json",
            conflict_path=root / "evidence_conflict_graph.json",
            review_path=root / "evidence_review_queue.jsonl",
            report_path=root / "evidence_trace.md",
        )

    def test_resolves_exact_locators_and_retains_conflict_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._resolver(Path(temporary)).run()
            self.assertEqual(summary.assertions, 6)
            self.assertEqual(summary.resolved, 5)
            self.assertEqual(summary.quarantined, 1)
            self.assertEqual(summary.conflict_nodes, 2)
            self.assertEqual(summary.conflict_edges, 1)
            self.assertEqual(summary.review_items, 1)
            evidence = json.loads(summary.evidence_path.read_text())
            resolved = [row for row in evidence["rows"] if row["resolution_status"] == "RESOLVED"]
            self.assertTrue(all(row["source_asset_id"] for row in resolved))
            trace = self._resolver(Path(temporary)).reverse_trace(
                "asset:asset-table-001/table:table-main/cell:C3"
            )
            self.assertEqual(
                {row["assertion_id"] for row in trace},
                {
                    "rule-outcome-mean",
                    "mock-outcome-mean",
                },
            )
            graph = json.loads(summary.conflict_path.read_text())
            self.assertEqual(len(graph["edges"]), 1)
            self.assertEqual(
                {graph["edges"][0]["from_assertion"], graph["edges"][0]["to_assertion"]},
                {"rule-outcome-mean", "mock-outcome-mean"},
            )

    def test_broken_locator_is_quarantined_and_queue_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resolver = self._resolver(Path(temporary))
            resolver.run()
            resolver.run()
            review_path = Path(temporary) / "evidence_review_queue.jsonl"
            reviews = [
                json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
            ]
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["reason"], "BROKEN_OR_MISSING_EVIDENCE_LOCATOR")
            AppendOnlyJSONL(review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            resolver = EvidenceResolver(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(EvidenceResolutionError, "envelope"):
                resolver.run()


if __name__ == "__main__":
    unittest.main()
