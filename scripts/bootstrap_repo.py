#!/usr/bin/env python3
"""Create or validate the repository skeleton required by GOAL.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"

# Keep this list aligned with GOAL.md sections 5 and 28.5. ``workflows`` is an
# explicit T002 output even though it is not shown in the section 5 tree.
DIRECTORIES = (
    "config",
    "config/models",
    "src",
    "src/biointerfaceos",
    "src/biointerfaceos/registry",
    "src/biointerfaceos/sources",
    "src/biointerfaceos/literature",
    "src/biointerfaceos/extraction",
    "src/biointerfaceos/normalization",
    "src/biointerfaceos/proteomics",
    "src/biointerfaceos/transcriptomics",
    "src/biointerfaceos/evidence",
    "src/biointerfaceos/benchmark",
    "src/biointerfaceos/models",
    "src/biointerfaceos/causal",
    "src/biointerfaceos/uncertainty",
    "src/biointerfaceos/design",
    "src/biointerfaceos/agents",
    "src/biointerfaceos/reporting",
    "schemas",
    "registry",
    "data",
    "data/raw",
    "data/raw/literature",
    "data/raw/supplementary",
    "data/raw/pride",
    "data/raw/geo",
    "data/raw/external",
    "data/bronze",
    "data/silver",
    "data/gold_auto",
    "data/gold_consensus",
    "data/gold_expert",
    "data/features",
    "data/splits",
    "data/locked_test",
    "benchmarks",
    "benchmarks/tasks",
    "benchmarks/graders",
    "benchmarks/baselines",
    "benchmarks/releases",
    "models",
    "models/checkpoints",
    "models/releases",
    "models/model_cards",
    "agents",
    "agents/prompts",
    "agents/tools",
    "agents/policies",
    "experiments",
    "experiments/configs",
    "experiments/runs",
    "experiments/frozen",
    "docs",
    "docs/execplans",
    "docs/data_dictionary",
    "docs/methods",
    "docs/manuscript",
    "reports",
    "reports/source_audit",
    "reports/qc",
    "reports/benchmark",
    "reports/final",
    "release",
    "release/public",
    "release/public/manifests",
    "release/public/schemas",
    "release/public/redistributable_data",
    "release/public/benchmark",
    "release/public/graders",
    "release/public/model_cards",
    "release/public/reproduction",
    "release/analysis_only",
    "release/analysis_only/rebuild_instructions",
    "release/analysis_only/source_pointers",
    "release/manuscripts",
    "release/manuscripts/paper_a",
    "release/manuscripts/paper_b",
    "release/manuscripts/paper_c",
    "scripts",
    "slurm",
    "containers",
    "tests",
    "workflows",
)

README_TEXT = """# Placeholder

This directory is part of the BioInterfaceOS repository contract. Its contents
will be added by the task responsible for this area.
"""


def is_within(path: Path, parent: Path) -> bool:
    """Return whether *path* resolves to *parent* or one of its descendants."""
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def validate_target(relative: str) -> tuple[Path, str | None]:
    target = ROOT / relative
    if not is_within(target, ROOT):
        return target, f"path escapes repository root: {relative}"
    if relative == "data" or relative.startswith("data/"):
        if not is_within(target, DATA_ROOT):
            return target, f"data path escapes data root: {relative}"
    return target, None


def check() -> list[str]:
    errors: list[str] = []
    for relative in DIRECTORIES:
        target, error = validate_target(relative)
        if error:
            errors.append(error)
            continue
        if not target.is_dir():
            errors.append(f"missing directory: {relative}")
            continue
        readme = target / "README.md"
        if not is_within(readme, ROOT):
            errors.append(f"README escapes repository root: {relative}/README.md")
        elif not readme.is_file():
            errors.append(f"missing placeholder: {relative}/README.md")
    return errors


def create() -> list[str]:
    errors: list[str] = []
    for relative in DIRECTORIES:
        target, error = validate_target(relative)
        if error:
            errors.append(error)
            continue
        try:
            target.mkdir(parents=True, exist_ok=True)
            if not target.is_dir():
                errors.append(f"not a directory: {relative}")
                continue
            readme = target / "README.md"
            if not is_within(readme, ROOT):
                errors.append(f"README escapes repository root: {relative}/README.md")
            elif not readme.exists():
                readme.write_text(README_TEXT, encoding="utf-8")
            elif not readme.is_file():
                errors.append(f"placeholder is not a file: {relative}/README.md")
        except OSError as exc:
            errors.append(f"cannot create {relative}: {exc}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate the skeleton")
    mode.add_argument("--create", action="store_true", help="create missing skeleton paths")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = create() if args.create else check()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    action = "Created" if args.create else "Validated"
    print(f"{action} {len(DIRECTORIES)} repository directories and placeholders")
    print(f"Repository root: {ROOT}")
    print(f"Data root: {DATA_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
