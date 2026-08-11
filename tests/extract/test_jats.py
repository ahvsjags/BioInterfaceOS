"""JATS/XML parser tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from biointerfaceos.jats_parser import JATSParseError, JATSParser


class JATSParserTests(unittest.TestCase):
    project_root: Path
    fixture_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]
        cls.fixture_path = cls.project_root / "tests/fixtures/extract/article.xml"

    def test_graph_preserves_required_nodes_and_round_trip_locators(self) -> None:
        parsed = JATSParser().parse_file(self.fixture_path, source_asset_id="asset-jats-001")
        self.assertEqual(parsed.article_id, "JATS-FIXTURE-001")
        counts = Counter(parsed.node_types())
        self.assertEqual(counts["section"], 2)
        self.assertEqual(counts["paragraph"], 5)
        self.assertEqual(counts["table"], 1)
        self.assertEqual(counts["figure"], 1)
        self.assertEqual(counts["reference"], 1)
        self.assertEqual(counts["supplementary_link"], 2)
        self.assertEqual(parsed.warnings, ())
        table = next(node for node in parsed.nodes if node.node_type == "table")
        self.assertIn("Exposure conditions", table.attributes["caption"])
        self.assertIn("Condition", table.attributes["headers"])
        figure = next(node for node in parsed.nodes if node.node_type == "figure")
        self.assertEqual(figure.attributes["graphic_href"], "figures/uptake.png")
        link_hrefs = {
            node.attributes["href"]
            for node in parsed.nodes
            if node.node_type == "supplementary_link"
        }
        self.assertEqual(
            link_hrefs,
            {
                "supplementary/data.csv",
                "https://fixture.example.org/dataset",
            },
        )
        for node in parsed.nodes:
            self.assertEqual(parsed.by_locator(node.locator), node)
            self.assertTrue(node.locator.startswith("asset:asset-jats-001/article/"))

    def test_optional_structure_emits_warning_without_dropping_table(self) -> None:
        raw = (
            b"<article><front><article-meta><article-id>WARN-001</article-id>"
            b"</article-meta></front><body><table-wrap><table><tr><td>x</td></tr>"
            b"</table></table-wrap></body></article>"
        )
        parsed = JATSParser().parse(raw, source_asset_id="asset-warn")
        self.assertEqual(sum(node.node_type == "table" for node in parsed.nodes), 1)
        self.assertTrue(any("table has no caption" in warning for warning in parsed.warnings))

    def test_unsafe_or_malformed_xml_fails_closed(self) -> None:
        parser = JATSParser()
        with self.assertRaisesRegex(JATSParseError, "DTD"):
            parser.parse(
                b"<!DOCTYPE article [ <!ENTITY x SYSTEM 'file:///secret'> ]><article/>",
                source_asset_id="asset-unsafe",
            )
        with self.assertRaisesRegex(JATSParseError, "malformed"):
            parser.parse(b"<article><broken>", source_asset_id="asset-malformed")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"not": "xml"}), encoding="utf-8")
            with self.assertRaises(JATSParseError):
                parser.parse_file(path, source_asset_id="asset-file")


if __name__ == "__main__":
    unittest.main()
