"""Supplementary spreadsheet and archive parser tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from biointerfaceos.supplements import SupplementParseError, SupplementParser


class SupplementParserTests(unittest.TestCase):
    fixture_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = Path(__file__).resolve().parents[1] / "fixtures/extract"

    def test_xlsx_preserves_merged_headers_formulas_units_and_coordinates(self) -> None:
        document = SupplementParser().parse_file(self.fixture_root / "table.xlsx")
        self.assertEqual(len(document.tables), 1)
        table = document.tables[0]
        self.assertEqual(table.sheet, "Data")
        self.assertEqual(table.header_rows, 2)
        self.assertEqual(table.merged_ranges, ("A1:A2", "C1:C2"))
        cells = {cell.coordinate: cell for cell in table.cells}
        self.assertEqual(cells["B1"].unit, "mg/mL")
        self.assertEqual(cells["C3"].formula, "B3*2")
        self.assertEqual(cells["C3"].raw_value, "20")
        self.assertEqual(cells["A4"].raw_value, "S2")
        self.assertTrue(all(cell.source_sha256 == document.source_sha256 for cell in table.cells))

    def test_delimited_and_safe_zip_tables_preserve_units_and_member_paths(self) -> None:
        parser = SupplementParser()
        csv_document = parser.parse_file(self.fixture_root / "table.csv")
        tsv_document = parser.parse_file(self.fixture_root / "table.tsv")
        self.assertEqual(csv_document.tables[0].cells[1].unit, "mg/mL")
        self.assertEqual(tsv_document.tables[0].cells[1].unit, "a.u.")
        archive = parser.parse_file(self.fixture_root / "safe.zip")
        self.assertEqual(len(archive.archive_members), 1)
        self.assertEqual(archive.tables[0].member_path, "nested/table.csv")
        self.assertEqual(archive.tables[0].cells[0].raw_value, "A [mM]")

    def test_zip_slip_is_blocked_before_member_read(self) -> None:
        parser = SupplementParser()
        with self.assertRaisesRegex(SupplementParseError, "zip-slip"):
            parser.parse_file(self.fixture_root / "zip_slip.zip")


if __name__ == "__main__":
    unittest.main()
