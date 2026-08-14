"""Typed project-state and task-graph validation."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

TASK_FIELDS = (
    "id",
    "phase",
    "title",
    "depends_on",
    "status",
    "priority",
    "inputs",
    "outputs",
    "command",
    "acceptance",
    "failure_policy",
)
ALLOWED_STATUSES = frozenset({"READY", "BLOCKED", "IN_PROGRESS", "DONE", "FAILED_RETRYABLE", "FAILED_FINAL", "WAIVED"})
SATISFIED_STATUSES = frozenset({"DONE", "WAIVED"})
TRANSITIONS: Mapping[str, frozenset[str]] = {
    "READY": frozenset({"IN_PROGRESS", "BLOCKED", "WAIVED"}),
    "BLOCKED": frozenset({"READY", "IN_PROGRESS", "WAIVED", "FAILED_FINAL"}),
    "IN_PROGRESS": frozenset({"DONE", "BLOCKED", "FAILED_RETRYABLE", "FAILED_FINAL"}),
    "FAILED_RETRYABLE": frozenset({"READY", "IN_PROGRESS", "FAILED_FINAL", "WAIVED"}),
    "FAILED_FINAL": frozenset({"WAIVED"}),
    "DONE": frozenset(),
    "WAIVED": frozenset(),
}


class StateValidationError(ValueError):
    """Raised when project state or the task graph violates its contract."""


class TransitionValidationError(StateValidationError):
    """Raised when a requested task transition is not permitted."""


@dataclass(frozen=True)
class Task:
    """One normalized TASKS.tsv row."""

    id: str
    phase: str
    title: str
    depends_on: tuple[str, ...]
    status: str
    priority: str
    inputs: str
    outputs: str
    command: str
    acceptance: str
    failure_policy: str


@dataclass(frozen=True)
class ProjectState:
    """Validated fields used from PROJECT_STATE.yaml."""

    task_count: int
    current_task: str | None
    ready_tasks: tuple[str, ...]
    completed_tasks: tuple[str, ...]
    failed_tasks: tuple[str, ...]
    waived_tasks: tuple[str, ...]
    blocked_tasks: tuple[str, ...]
    raw: Mapping[str, Any]


def _string_list(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise StateValidationError(f"PROJECT_STATE.yaml {key} must be a list of task IDs")
    return tuple(value)


def load_project_state(path: Path) -> ProjectState:
    """Parse a project-state YAML file with the safe loader."""
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StateValidationError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StateValidationError("PROJECT_STATE.yaml must contain a mapping")
    task_count = value.get("task_count")
    current_task = value.get("current_task")
    if not isinstance(task_count, int) or task_count < 0:
        raise StateValidationError("PROJECT_STATE.yaml task_count must be a non-negative integer")
    if current_task is not None and not isinstance(current_task, str):
        raise StateValidationError("PROJECT_STATE.yaml current_task must be a task ID or null")
    return ProjectState(
        task_count=task_count,
        current_task=current_task,
        ready_tasks=_string_list(value, "ready_tasks"),
        completed_tasks=_string_list(value, "completed_tasks"),
        failed_tasks=_string_list(value, "failed_tasks"),
        waived_tasks=_string_list(value, "waived_tasks"),
        blocked_tasks=_string_list(value, "blocked_tasks"),
        raw=value,
    )


def load_tasks(path: Path) -> tuple[Task, ...]:
    """Parse and normalize TASKS.tsv using :class:`csv.DictReader`."""
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if tuple(reader.fieldnames or ()) != TASK_FIELDS:
                raise StateValidationError(f"TASKS.tsv fields must be {', '.join(TASK_FIELDS)}")
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        raise StateValidationError(f"cannot parse {path}: {exc}") from exc
    tasks: list[Task] = []
    for line, row in enumerate(rows, 2):
        missing = [field for field in TASK_FIELDS if row.get(field) is None]
        if missing:
            detail = ", ".join(missing)
            raise StateValidationError(f"TASKS.tsv line {line} missing fields: {detail}")
        assert all(row[field] is not None for field in TASK_FIELDS)
        tasks.append(
            Task(
                id=row["id"],
                phase=row["phase"],
                title=row["title"],
                depends_on=tuple(part.strip() for part in row["depends_on"].split(",") if part.strip()),
                status=row["status"],
                priority=row["priority"],
                inputs=row["inputs"],
                outputs=row["outputs"],
                command=row["command"],
                acceptance=row["acceptance"],
                failure_policy=row["failure_policy"],
            )
        )
    return tuple(tasks)


def validate_tasks(tasks: Sequence[Task]) -> None:
    """Validate required values, IDs, statuses, dependencies, and the DAG."""
    ids = [task.id for task in tasks]
    duplicates = sorted(task_id for task_id, count in Counter(ids).items() if count > 1)
    errors: list[str] = []
    if duplicates:
        errors.append(f"duplicate task IDs: {', '.join(duplicates)}")
    known = set(ids)
    by_id = {task.id: task for task in tasks}
    for task in tasks:
        if not re.fullmatch(r"T\d{3}", task.id):
            errors.append(f"invalid task ID: {task.id}")
        if task.status not in ALLOWED_STATUSES:
            errors.append(f"{task.id}: invalid status {task.status}")
        for field in ("phase", "title", "priority", "command", "acceptance", "failure_policy"):
            if not getattr(task, field).strip():
                errors.append(f"{task.id}: {field} cannot be empty")
        for dependency in task.depends_on:
            if dependency not in known:
                errors.append(f"{task.id}: unknown dependency {dependency}")
            elif dependency == task.id:
                errors.append(f"{task.id}: self dependency")
        if task.status in {"READY", "IN_PROGRESS", "DONE"}:
            unsatisfied = [
                dependency
                for dependency in task.depends_on
                if dependency in by_id and by_id[dependency].status not in SATISFIED_STATUSES
            ]
            if unsatisfied:
                detail = ", ".join(unsatisfied)
                errors.append(f"{task.id}: {task.status} with unsatisfied dependencies: {detail}")

    indegree = {task.id: len(task.depends_on) for task in tasks}
    children: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for dependency in task.depends_on:
            if dependency in known:
                children[dependency].append(task.id)
    queue = deque(sorted(task_id for task_id, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        task_id = queue.popleft()
        visited += 1
        for child in sorted(children[task_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(tasks):
        errors.append("TASKS.tsv contains a dependency cycle")
    if errors:
        raise StateValidationError("; ".join(errors))


def validate_project_state(state: ProjectState, tasks: Sequence[Task]) -> None:
    """Require state summary lists to agree exactly with TASKS.tsv."""
    validate_tasks(tasks)
    by_id = {task.id: task for task in tasks}
    if state.task_count != len(tasks):
        raise StateValidationError(f"task_count={state.task_count}, actual={len(tasks)}")
    if state.current_task is not None and state.current_task not in by_id:
        raise StateValidationError(f"unknown current_task: {state.current_task}")
    if state.current_task is not None and by_id[state.current_task].status not in {
        "READY",
        "IN_PROGRESS",
    }:
        raise StateValidationError("current_task must have READY or IN_PROGRESS status")
    expected = {
        "ready_tasks": tuple(task.id for task in tasks if task.status == "READY"),
        "completed_tasks": tuple(task.id for task in tasks if task.status == "DONE"),
        "failed_tasks": tuple(task.id for task in tasks if task.status.startswith("FAILED_")),
        "waived_tasks": tuple(task.id for task in tasks if task.status == "WAIVED"),
        "blocked_tasks": tuple(task.id for task in tasks if task.status == "BLOCKED"),
    }
    for name, wanted in expected.items():
        actual = getattr(state, name)
        if actual != wanted:
            raise StateValidationError(f"{name}={list(actual)!r}, expected={list(wanted)!r}")


def validate_repository_state(root: Path) -> tuple[ProjectState, tuple[Task, ...]]:
    """Load and validate the repository's state files."""
    state = load_project_state(root / "PROJECT_STATE.yaml")
    tasks = load_tasks(root / "TASKS.tsv")
    validate_project_state(state, tasks)
    return state, tasks


def next_ready_task(tasks: Sequence[Task]) -> Task | None:
    """Return the first file-ordered READY task with satisfied dependencies."""
    by_id = {task.id: task for task in tasks}
    return next(
        (
            task
            for task in tasks
            if task.status == "READY"
            and all(by_id[dependency].status in SATISFIED_STATUSES for dependency in task.depends_on)
        ),
        None,
    )


def validate_transition(
    task: Task,
    new_status: str,
    tasks: Sequence[Task],
    *,
    prior_status: str | None = None,
    acceptance_evidence: Mapping[str, Any] | None = None,
) -> None:
    """Validate a task status transition, including the strict DONE gate."""
    old_status = prior_status or task.status
    if new_status not in ALLOWED_STATUSES:
        raise TransitionValidationError(f"invalid target status: {new_status}")
    if new_status not in TRANSITIONS.get(old_status, frozenset()):
        raise TransitionValidationError(f"transition {old_status} -> {new_status} is not allowed")
    if new_status == "DONE":
        if old_status != "IN_PROGRESS":
            raise TransitionValidationError("DONE requires prior IN_PROGRESS status")
        by_id = {item.id: item for item in tasks}
        unsatisfied = [
            dependency
            for dependency in task.depends_on
            if dependency not in by_id or by_id[dependency].status not in SATISFIED_STATUSES
        ]
        if unsatisfied:
            detail = ", ".join(unsatisfied)
            raise TransitionValidationError(f"DONE has unsatisfied dependencies: {detail}")
        if not acceptance_evidence or not all(
            value is not None and value is not False for value in acceptance_evidence.values()
        ):
            raise TransitionValidationError("DONE requires non-empty acceptance evidence")
