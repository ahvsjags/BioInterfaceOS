"""State graph and append-only ledger contract tests for T006."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from biointerfaceos.ledgers import (
    AppendOnlyJSONL,
    LedgerIntegrityError,
    initialize_standard_ledgers,
)
from biointerfaceos.state import (
    ProjectState,
    StateValidationError,
    Task,
    TransitionValidationError,
    load_project_state,
    load_tasks,
    next_ready_task,
    validate_project_state,
    validate_repository_state,
    validate_transition,
)


class RepositoryStateTests(unittest.TestCase):
    root: Path
    state: ProjectState
    tasks: tuple[Task, ...]

    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.state = load_project_state(cls.root / "PROJECT_STATE.yaml")
        cls.tasks = load_tasks(cls.root / "TASKS.tsv")

    def test_repository_state_validation_and_next(self) -> None:
        state, tasks = validate_repository_state(self.root)

        self.assertEqual(self.state, state)
        self.assertEqual("T007", next_ready_task(tasks).id)  # type: ignore[union-attr]

    def test_repository_state_rejects_summary_disagreement(self) -> None:
        invalid = replace(self.state, ready_tasks=())

        with self.assertRaisesRegex(StateValidationError, "ready_tasks"):
            validate_project_state(invalid, self.tasks)

    def test_invalid_done_transition_is_rejected(self) -> None:
        ready_task = next(task for task in self.tasks if task.id == "T007")
        with self.assertRaisesRegex(TransitionValidationError, "not allowed"):
            validate_transition(
                ready_task,
                "DONE",
                self.tasks,
                acceptance_evidence={"tests": "passed"},
            )

        active_task = next(task for task in self.tasks if task.id == "T006")
        with self.assertRaisesRegex(TransitionValidationError, "acceptance evidence"):
            validate_transition(active_task, "DONE", self.tasks)


class AppendOnlyLedgerTests(unittest.TestCase):
    def test_standard_initialization_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = initialize_standard_ledgers(root)
            before = [(item.path.read_bytes(), item.seal_path.read_bytes()) for item in first]
            second = initialize_standard_ledgers(root)
            after = [(item.path.read_bytes(), item.seal_path.read_bytes()) for item in second]

            self.assertEqual(before, after)
            for ledger in second:
                ledger.validate()

    def test_append_creates_a_valid_hash_seal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = AppendOnlyJSONL(Path(temporary) / "ledger.jsonl")
            first = ledger.append({"event": "one"})
            second = ledger.append({"event": "two"})

            ledger.validate()
            self.assertEqual(1, first["_ledger"]["sequence"])
            self.assertEqual(2, second["_ledger"]["sequence"])
            self.assertEqual(first["_ledger"]["record_hash"], second["_ledger"]["previous_hash"])
            seal = json.loads(ledger.seal_path.read_text(encoding="utf-8"))
            self.assertEqual(len(ledger.path.read_bytes()), seal["bytes"])

    def test_tamper_and_truncation_are_detected(self) -> None:
        mutations: tuple[Callable[[bytes], bytes], ...] = (
            lambda data: data.replace(b"one", b"won"),
            lambda data: data[:-1],
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                ledger = AppendOnlyJSONL(Path(temporary) / "ledger.jsonl")
                ledger.append({"event": "one"})
                ledger.path.write_bytes(mutation(ledger.path.read_bytes()))

                with self.assertRaises(LedgerIntegrityError):
                    ledger.validate()

    def test_quarantine_recovery_restores_sealed_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            ledger = AppendOnlyJSONL(Path(temporary) / "ledger.jsonl")
            ledger.append({"event": "sealed"})
            sealed = ledger.path.read_bytes()
            corrupt = sealed + b'{"interrupted":'
            ledger.path.write_bytes(corrupt)

            quarantine = ledger.recover()

            self.assertEqual(corrupt, quarantine.read_bytes())
            self.assertEqual(sealed, ledger.path.read_bytes())
            ledger.validate()

    def test_legacy_prefix_is_preserved_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ledger.jsonl"
            legacy = b'{ "legacy": 1 }\r\n{"legacy":2}'
            path.write_bytes(legacy)
            ledger = AppendOnlyJSONL(path)

            ledger.initialize()
            self.assertEqual(legacy, path.read_bytes())
            ledger.initialize()
            self.assertEqual(legacy, path.read_bytes())
            ledger.append({"event": "new"})

            self.assertEqual(legacy + b"\n", path.read_bytes()[: len(legacy) + 1])
            ledger.validate()


if __name__ == "__main__":
    unittest.main()
