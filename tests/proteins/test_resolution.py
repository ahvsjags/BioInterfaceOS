"""Protein identifier and orthology resolution tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.protein_resolution import ProteinResolutionError, ProteinResolver


class ProteinResolverTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _resolver(self, root: Path) -> ProteinResolver:
        return ProteinResolver(
            self.project_root,
            entities_path=root / "protein_entities.json",
            orthology_path=root / "orthology_groups.json",
            review_path=root / "protein_review_queue.jsonl",
            report_path=root / "protein_resolution.md",
        )

    def test_species_accessions_and_one_to_many_orthology_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._resolver(Path(temporary)).run()
            self.assertEqual(summary.mentions, 5)
            self.assertEqual(summary.resolved, 3)
            self.assertEqual(summary.ambiguous, 1)
            self.assertEqual(summary.obsolete_review, 1)
            self.assertEqual(summary.orthology_groups, 1)
            self.assertEqual(summary.orthology_edges, 2)
            self.assertEqual(summary.review_items, 2)
            entities = json.loads(summary.entities_path.read_text())["entities"]
            human = next(item for item in entities if item["mention_id"] == "protein-human-tp53")
            self.assertEqual(human["resolved_protein"]["accession"], "P04637")
            self.assertEqual(human["resolved_protein"]["gene_id"], "HGNC:11998")
            isoform = next(
                item for item in entities if item["mention_id"] == "protein-human-tp53-isoform"
            )
            self.assertEqual(isoform["status"], "AMBIGUOUS")
            self.assertEqual(len(isoform["candidate_mappings"]), 2)
            obsolete = next(item for item in entities if item["mention_id"] == "protein-obsolete")
            self.assertEqual(obsolete["status"], "OBSOLETE_REVIEW")
            self.assertEqual(obsolete["candidate_mappings"][0]["replaced_by"], "P04637")
            groups = json.loads(summary.orthology_path.read_text())["orthology_groups"]
            self.assertEqual(len(groups[0]["members"]), 3)
            self.assertTrue(
                all(edge["relation"] == "ONE_TO_MANY_ORTHOLOGY" for edge in groups[0]["edges"])
            )

    def test_ambiguity_queue_is_append_only_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resolver = self._resolver(Path(temporary))
            resolver.run()
            resolver.run()
            review_path = Path(temporary) / "protein_review_queue.jsonl"
            reviews = [
                json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
            ]
            self.assertEqual(len(reviews), 2)
            self.assertEqual(
                {review["reason"] for review in reviews},
                {"ISOFORM_AMBIGUITY", "OBSOLETE_ACCESSION_REQUIRES_REVIEW"},
            )
            AppendOnlyJSONL(review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            resolver = ProteinResolver(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(ProteinResolutionError, "envelope"):
                resolver.run()


if __name__ == "__main__":
    unittest.main()
