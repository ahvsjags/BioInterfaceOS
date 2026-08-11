"""Standard-library command-line interface for the BioInterfaceOS foundation."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from biointerfaceos import __version__

FUTURE_COMMANDS = (
    "data",
    "source",
    "extract",
    "split",
    "benchmark",
    "train",
    "agent",
    "claim",
    "release",
)

REQUIRED_FILES = (
    "AGENTS.md",
    "GOAL.md",
    "PLANS.md",
    "PROJECT_STATE.yaml",
    "TASKS.tsv",
    "pyproject.toml",
    "uv.lock",
)

SKELETON_DIRECTORIES = (
    "agents",
    "benchmarks",
    "config",
    "containers",
    "data",
    "docs",
    "experiments",
    "models",
    "registry",
    "release",
    "reports",
    "schemas",
    "scripts",
    "slurm",
    "src",
    "tests",
    "workflows",
)


@dataclass(frozen=True)
class Check:
    """One deterministic doctor result."""

    status: str
    name: str
    detail: str
    mandatory: bool = False


def find_repository_root(start: Path | None = None) -> Path | None:
    """Find the nearest repository root using foundation marker files."""
    origin = (start or Path.cwd()).resolve()
    candidates = (origin, *origin.parents)
    for candidate in candidates:
        if (candidate / "AGENTS.md").is_file() and (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def foundation_checks(root: Path | None) -> list[Check]:
    """Return foundation checks without mutating the repository."""
    checks = [
        Check(
            "PASS" if sys.version_info[:2] == (3, 11) else "FAIL",
            "python",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            mandatory=True,
        )
    ]
    if root is None:
        checks.append(Check("FAIL", "repository", "repository root not found", mandatory=True))
    else:
        checks.append(Check("PASS", "repository", str(root), mandatory=True))
        for relative in REQUIRED_FILES:
            exists = (root / relative).is_file()
            checks.append(
                Check(
                    "PASS" if exists else "FAIL",
                    f"file:{relative}",
                    "present" if exists else "missing",
                    mandatory=True,
                )
            )
        missing_dirs = [name for name in SKELETON_DIRECTORIES if not (root / name).is_dir()]
        checks.append(
            Check(
                "PASS" if not missing_dirs else "FAIL",
                "skeleton",
                "17 top-level directories present"
                if not missing_dirs
                else f"missing: {', '.join(missing_dirs)}",
                mandatory=True,
            )
        )

    package_spec = importlib.util.find_spec("biointerfaceos")
    checks.append(
        Check(
            "PASS" if package_spec is not None and bool(__version__) else "FAIL",
            "package-import",
            f"biointerfaceos {__version__}" if package_spec is not None else "not importable",
            mandatory=True,
        )
    )
    for tool in ("pytest", "ruff", "mypy"):
        available = importlib.util.find_spec(tool) is not None
        checks.append(
            Check(
                "PASS" if available else "WARN",
                f"optional:{tool}",
                "available" if available else "not installed",
            )
        )
    for command in FUTURE_COMMANDS:
        checks.append(Check("NOT_IMPLEMENTED", f"command:{command}", "future task"))
    return checks


def doctor(strict: bool) -> int:
    """Print deterministic foundation diagnostics and return their status."""
    checks = foundation_checks(find_repository_root())
    for check in checks:
        print(f"{check.status} {check.name}: {check.detail}")
    failures = sum(check.mandatory and check.status != "PASS" for check in checks)
    mode = "strict" if strict else "standard"
    print(f"SUMMARY mode={mode} mandatory_failures={failures}")
    return 1 if failures else 0


def not_implemented(command: str) -> int:
    """Fail explicitly for command families owned by future tasks."""
    print(f"NOT_IMPLEMENTED: '{command}' is reserved for a future task.", file=sys.stderr)
    return 2


def build_parser(prog: str = "biointerfaceos") -> argparse.ArgumentParser:
    """Build the public argument parser."""
    parser = argparse.ArgumentParser(prog=prog, description="BioInterfaceOS command line")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser("doctor", help="check foundation prerequisites")
    doctor_parser.add_argument("--strict", action="store_true", help="enforce mandatory checks")

    state_parser = subparsers.add_parser("state", help="validate and inspect project state")
    state_subparsers = state_parser.add_subparsers(dest="state_command")
    state_subparsers.add_parser("validate", help="validate PROJECT_STATE.yaml and TASKS.tsv")
    state_subparsers.add_parser("next", help="print the next dependency-satisfied READY task")

    schema_parser = subparsers.add_parser("schema", help="validate versioned schemas")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command")
    schema_subparsers.add_parser("validate-all", help="validate all schemas and fixtures")

    storage_parser = subparsers.add_parser("storage", help="audit repository storage")
    storage_subparsers = storage_parser.add_subparsers(dest="storage_command")
    storage_audit_parser = storage_subparsers.add_parser("audit", help="audit storage usage")
    storage_audit_parser.add_argument("--strict", action="store_true", help="fail over budget")

    for command in FUTURE_COMMANDS:
        subparsers.add_parser(command, help="reserved; not implemented")
    return parser


def main(argv: Sequence[str] | None = None, *, prog: str = "biointerfaceos") -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor(args.strict)
    if args.command == "state":
        from biointerfaceos.state import (
            StateValidationError,
            next_ready_task,
            validate_repository_state,
        )

        if args.state_command is None:
            parser.parse_args(["state", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("STATE_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            _, tasks = validate_repository_state(root)
        except StateValidationError as exc:
            print(f"STATE_INVALID: {exc}", file=sys.stderr)
            return 1
        if args.state_command == "validate":
            print(f"STATE_VALID tasks={len(tasks)}")
            return 0
        task = next_ready_task(tasks)
        if task is None:
            print("NO_READY_TASK")
            return 1
        print(task.id)
        return 0
    if args.command == "schema":
        if args.schema_command is None:
            parser.parse_args(["schema", "--help"])
            return 0
        from biointerfaceos.schema import SchemaError, validate_all

        root = find_repository_root()
        if root is None:
            print("SCHEMA_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            configs = validate_all(root)
        except SchemaError as exc:
            print(f"SCHEMA_INVALID: {exc}", file=sys.stderr)
            return 1
        print(f"SCHEMA_VALID schemas={len(configs)} fixtures={len(configs)}")
        return 0
    if args.command == "storage":
        if args.storage_command is None:
            parser.parse_args(["storage", "--help"])
            return 0
        from biointerfaceos.storage import (
            StorageConfig,
            StorageError,
            audit_storage,
            write_json_report,
        )

        root = find_repository_root()
        if root is None:
            print("STORAGE_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            report = audit_storage(root, StorageConfig.from_yaml(root))
            write_json_report(report, root / "reports/storage_usage.json")
        except (OSError, StorageError) as exc:
            print(f"STORAGE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"STORAGE_VALID bytes={report.total_bytes} files={report.total_files} "
            f"budget_bytes={report.budget_bytes} duplicates={len(report.duplicates)}"
        )
        return 1 if args.strict and not report.within_budget else 0
    if args.command in FUTURE_COMMANDS:
        return not_implemented(args.command)
    parser.print_help()
    return 0
