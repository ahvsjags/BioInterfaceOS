"""PDF fallback parser tests."""

from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from biointerfaceos.pdf_parser import PDFParseError, PDFParser


class PDFParserTests(unittest.TestCase):
    fixture_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = Path(__file__).resolve().parents[1] / "fixtures/extract"

    def test_born_digital_fixture_preserves_page_bbox_and_types(self) -> None:
        parsed = PDFParser().parse_file(
            self.fixture_root / "born_digital.pdf",
            source_asset_id="asset-pdf-001",
        )
        self.assertEqual(parsed.page_count, 1)
        self.assertEqual(parsed.quality.status, "BORN_DIGITAL")
        self.assertEqual(parsed.quality.text_blocks, 4)
        self.assertEqual(
            Counter(block.block_type for block in parsed.blocks),
            {
                "text": 2,
                "caption": 1,
                "table": 1,
            },
        )
        for block in parsed.blocks:
            self.assertEqual(parsed.by_locator(block.locator), block)
            self.assertEqual(block.page, 1)
            self.assertLess(block.bbox[0], block.bbox[2])
            self.assertLess(block.bbox[1], block.bbox[3])
            self.assertTrue(block.locator.startswith("asset:asset-pdf-001/page[1]/"))

    def test_textless_fixture_is_marked_without_ocr(self) -> None:
        parsed = PDFParser().parse_file(
            self.fixture_root / "scanned.pdf",
            source_asset_id="asset-pdf-scanned",
        )
        self.assertEqual(parsed.quality.status, "SCANNED_OR_TEXTLESS")
        self.assertEqual(parsed.blocks, ())
        self.assertIn("OCR was not attempted", parsed.quality.warnings[0])

    def test_invalid_header_fails_closed(self) -> None:
        with self.assertRaisesRegex(PDFParseError, "header"):
            PDFParser().parse(b"not a PDF", source_asset_id="bad-pdf")


if __name__ == "__main__":
    unittest.main()
