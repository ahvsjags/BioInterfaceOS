"""Table-to-experiment semantic mapping tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.table_semantics import TableSemanticsError, TableSemanticsParser


class TableSemanticsTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _parser(self, root: Path) -> TableSemanticsParser:
        return TableSemanticsParser(
            self.project_root,
            normalized_path=root / "experiment_table_semantics.json",
            review_path=root / "table_review_queue.jsonl",
            report_path=root / "table_semantics.md",
        )

    def test_maps_arms_measurements_and_exact_cell_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._parser(Path(temporary)).run()
            self.assertEqual(summary.tables, 2)
            self.assertEqual(summary.arms, 3)
            self.assertEqual(summary.measurements, 4)
            self.assertEqual(summary.review_items, 2)
            payload = json.loads(summary.normalized_path.read_text())
            main = next(table for table in payload["tables"] if table["table_id"] == "table-main")
            self.assertEqual([arm["sample_size"] for arm in main["arms"]], [5, 5])
            measurement = main["measurements"][0]
            self.assertEqual(measurement["mean"], 1.2)
            self.assertEqual(measurement["error"], 0.1)
            self.assertEqual(measurement["error_type"], "SD")
            self.assertEqual(measurement["unit"], "%")
            self.assertTrue(any(locator.endswith("cell:A3") for locator in measurement["source_cell_locators"]))
            self.assertTrue(measurement["footnotes"])

    def test_ambiguity_is_retained_in_append_only_review_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parser = self._parser(Path(temporary))
            parser.run()
            parser.run()
            reviews = [
                json.loads(line) for line in (Path(temporary) / "table_review_queue.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(reviews), 2)
            self.assertEqual(
                {review["reason"] for review in reviews},
                {"MULTIPLE_OUTCOME_COLUMNS_REQUIRES_REVIEW", "UNIT_MISSING"},
            )
            AppendOnlyJSONL(Path(temporary) / "table_review_queue.jsonl").validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            parser = TableSemanticsParser(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(TableSemanticsError, "envelope"):
                parser.run()


if __name__ == "__main__":
    unittest.main()
