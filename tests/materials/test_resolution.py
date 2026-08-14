"""Material entity and formulation graph resolution tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.material_resolution import MaterialResolutionError, MaterialResolver


class MaterialResolverTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _resolver(self, root: Path) -> MaterialResolver:
        return MaterialResolver(
            self.project_root,
            entities_path=root / "material_entities.json",
            graphs_path=root / "formulation_graphs.json",
            review_path=root / "material_review_queue.jsonl",
            report_path=root / "material_resolution.md",
        )

    def test_resolves_material_classes_roles_and_valid_fraction_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._resolver(Path(temporary)).run()
            self.assertEqual(summary.mentions, 4)
            self.assertEqual(summary.resolved_entities, 3)
            self.assertEqual(summary.ambiguous_mentions, 1)
            self.assertEqual(summary.formulations, 2)
            self.assertEqual(summary.valid_formulations, 1)
            self.assertEqual(summary.graph_edges, 2)
            self.assertEqual(summary.review_items, 2)
            entities = json.loads(summary.entities_path.read_text())["entities"]
            dspc = next(item for item in entities if item["mention_id"] == "mat-dspc")
            self.assertEqual(dspc["resolved_entity"]["material_class"], "lipid")
            self.assertEqual(dspc["resolved_entity"]["structure_id"], "CHEBI:47785")
            trade = next(item for item in entities if item["mention_id"] == "mat-tradename")
            self.assertEqual(trade["status"], "AMBIGUOUS")
            self.assertEqual(len(trade["candidate_aliases"]), 2)
            graphs = json.loads(summary.graphs_path.read_text())["formulations"]
            valid = next(item for item in graphs if item["formulation_id"] == "formulation-valid")
            self.assertTrue(valid["valid"])
            self.assertAlmostEqual(valid["fraction_total"], 1.0)
            self.assertEqual({edge["relation"] for edge in valid["edges"]}, {"FORMULATION_COMPONENT"})

    def test_ambiguity_and_invalid_fraction_are_queued_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resolver = self._resolver(Path(temporary))
            resolver.run()
            resolver.run()
            review_path = Path(temporary) / "material_review_queue.jsonl"
            reviews = [json.loads(line) for line in review_path.read_text().splitlines() if line.strip()]
            self.assertEqual(len(reviews), 2)
            self.assertEqual(
                {review["reason"] for review in reviews},
                {"AMBIGUOUS_MATERIAL_MENTION", "MIXTURE_FRACTIONS_DO_NOT_SUM_TO_ONE"},
            )
            AppendOnlyJSONL(review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            resolver = MaterialResolver(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(MaterialResolutionError, "envelope"):
                resolver.run()


if __name__ == "__main__":
    unittest.main()
