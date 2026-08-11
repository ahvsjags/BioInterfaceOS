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
    "state",
    "data",
    "source",
    "extract",
    "split",
    "benchmark",
    "train",
    "agent",
    "claim",
    "release",
    "storage",
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

    for command in FUTURE_COMMANDS:
        subparsers.add_parser(command, help="reserved; not implemented")
    return parser


def main(argv: Sequence[str] | None = None, *, prog: str = "biointerfaceos") -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor(args.strict)
    if args.command in FUTURE_COMMANDS:
        return not_implemented(args.command)
    parser.print_help()
    return 0
