"""Standard-library tests for the T004 command contract."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from biointerfaceos import cli


class CliTests(unittest.TestCase):
    def test_doctor_strict_succeeds_for_repository_foundation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        checks = cli.foundation_checks(root)

        failures = [check for check in checks if check.mandatory and check.status != "PASS"]
        self.assertEqual([], failures)

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(["doctor", "--strict"])
        self.assertEqual(0, exit_code)
        self.assertIn("SUMMARY mode=strict mandatory_failures=0", output.getvalue())
        self.assertNotIn("NOT_IMPLEMENTED command:state: future task", output.getvalue())

    def test_help_discovers_every_command(self) -> None:
        help_text = cli.build_parser().format_help()
        self.assertIn("doctor", help_text)
        for command in cli.FUTURE_COMMANDS:
            self.assertIn(command, help_text)

    def test_ontology_sync_dry_run_is_network_free(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(["ontology", "sync", "--dry-run"])
        self.assertEqual(0, exit_code)
        self.assertIn("ONTOLOGY_SYNC_DRY_RUN", output.getvalue())
        self.assertIn("network=false", output.getvalue())
        self.assertIn("binary_assets=0", output.getvalue())

    def test_future_commands_are_explicitly_not_implemented(self) -> None:
        for command in cli.FUTURE_COMMANDS:
            with self.subTest(command=command):
                error = io.StringIO()
                with redirect_stderr(error):
                    exit_code = cli.main([command])
                self.assertNotEqual(0, exit_code)
                self.assertIn("NOT_IMPLEMENTED", error.getvalue())


if __name__ == "__main__":
    unittest.main()
