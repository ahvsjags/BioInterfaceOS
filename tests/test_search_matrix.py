"""Offline search matrix validation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from biointerfaceos.search_matrix import SearchMatrixError, load_matrix, validate_matrix


class SearchMatrixTests(unittest.TestCase):
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]

    def test_versioned_matrix_has_all_axes_and_scopes(self) -> None:
        summary = load_matrix(self.root / "configs/search_queries.yaml")
        self.assertEqual(summary.queries, 22)
        self.assertEqual(
            summary.axes,
            ("assay", "corona", "data_code", "endpoint", "material", "protocol", "species"),
        )
        self.assertEqual(summary.scopes, ("train", "validation"))
        self.assertGreaterEqual(len(summary.sources), 8)
        self.assertEqual(len(summary.sha256), 64)

    def test_duplicate_lockbox_and_scope_errors_are_explicit(self) -> None:
        fixture_root = self.root / "tests/fixtures/search_queries"
        for filename, message in (
            ("duplicate.yaml", "duplicate query definition"),
            ("lockbox.yaml", "lockbox"),
            ("scope_mismatch.yaml", "validation scope"),
        ):
            with self.subTest(filename=filename):
                value = yaml.safe_load((fixture_root / filename).read_text(encoding="utf-8"))
                with self.assertRaisesRegex(SearchMatrixError, message):
                    validate_matrix(value)

    def test_missing_trailing_newline_is_rejected(self) -> None:
        source = (self.root / "configs/search_queries.yaml").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "queries.yaml"
            path.write_bytes(source.rstrip(b"\n"))
            with self.assertRaisesRegex(SearchMatrixError, "newline"):
                load_matrix(path)


if __name__ == "__main__":
    unittest.main()
