"""Mass-spec conversion and resume tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from biointerfaceos import cli
from biointerfaceos.conversion_workflow import ConversionWorkflow


class ConversionWorkflowTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_bypass_refusal_paths_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            workflow = ConversionWorkflow(self.project_root, output_root=output_root)
            first = workflow.run()
            second = workflow.run()
            self.assertEqual(first.records, 4)
            self.assertEqual(first.completed, 1)
            self.assertEqual(first.refused, 3)
            self.assertEqual(first.resumed, 0)
            self.assertEqual(second.resumed, 1)
            self.assertEqual(first.receipt_path.read_bytes(), second.receipt_path.read_bytes())
            self.assertEqual(len(first.artifact_paths), 1)
            self.assertTrue(first.artifact_paths[0].exists())
            manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["status_counts"],
                {
                    "COMPLETED": 1,
                    "REFUSED_RESTRICTED": 1,
                    "REFUSED_SIZE": 1,
                    "REFUSED_UNSUPPORTED_FORMAT": 1,
                },
            )
            self.assertTrue(manifest["raw_downloaded"] is False)

    def test_cli_conversion_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(["omics", "convert", "--fixture"])
        self.assertEqual(exit_code, 0)
        self.assertIn("CONVERSION_VALID records=4 completed=1 refused=3", output.getvalue())


if __name__ == "__main__":
    unittest.main()
