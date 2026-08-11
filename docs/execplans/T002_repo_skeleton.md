# T002: Create repository directory skeleton

## Purpose

Create the version-controlled directory boundary required by GOAL.md so later tasks have stable, documented locations for code, data tiers, registries, experiments, reports, and releases.

## Preconditions

T000 and T001 are DONE. The repository root is `/ibex/user/xup0a/BioInterfaceOS`, and T002 is READY. This task uses no downloaded data or third-party Python packages.

## Non-goals

This task does not create the Python environment, configuration files, schemas, registry tables, datasets, models, or any T003-or-later implementation.

## Interfaces and invariants

`python scripts/bootstrap_repo.py --create` creates missing contract directories and `README.md` placeholders without changing existing files. `python scripts/bootstrap_repo.py --check` performs read-only validation. The flags are mutually exclusive. Every resolved target remains inside the repository root, and every `data/` target also remains inside the repository data root.

## Implementation plan

1. Encode the GOAL.md section 5 and section 28.5 directory contracts, plus the T002-required `workflows/` directory, in `scripts/bootstrap_repo.py`.
2. Add placeholder tracking exceptions for protected data/model artifact trees.
3. Run create twice and compare placeholder checksums to demonstrate idempotency.
4. Run the declared acceptance command and independent containment validation.
5. Update task/state records and append the T002 ledger entry only after validation passes.

## Progress

- [x] 2026-08-11 — Read the execution contract, state, and T002 task definition.
- [x] 2026-08-11 — Implemented `--create` and `--check` behavior for 84 contract directories.
- [x] 2026-08-11 — Created the directories and placeholder READMEs without overwriting existing files.
- [x] 2026-08-11 — Repeated `--create`; placeholder checksum manifests were identical.
- [x] 2026-08-11 — Acceptance and containment checks passed; implementation committed as `748a185d1786c1a08652ce98cbe0e8c66e296dab`.
- [x] 2026-08-11 — Advanced task/state records to T003 and appended the truthful T002 ledger entry.

## Discoveries

GOAL.md uses `config/` (singular), while the T002 output summary uses the category word “configs.” The canonical GOAL.md path is used. The detailed release tree is specified separately in GOAL.md section 28.5 and is included. Existing ignore rules protected `data/raw/`, `models/`, and experiment run artifacts, so narrow exceptions were required to track only skeleton README placeholders.

## Decisions

Each declared directory receives a README placeholder, including non-empty pre-existing directories. Existing README files are never overwritten. No future-task files such as `pyproject.toml`, configuration YAML, package modules, or Parquet ledgers are created.

## Validation

- `python scripts/bootstrap_repo.py --create` exits 0.
- A second create run exits 0 and leaves README checksums unchanged.
- `python scripts/bootstrap_repo.py --check` exits 0 and reports 84 validated directories and placeholders.
- An independent Python assertion confirms all declared paths resolve under the repository root and data paths under the data root.
- `python -m compileall -q scripts/bootstrap_repo.py` exited 0.
- Ruff and mypy were unavailable. Pytest was available but collected no tests and exited 5; none of these results are claimed as passes.

## Failure recovery

Fix the script and rerun it. Never delete existing user files. Only generated empty paths may be rolled back, although retained placeholders are harmless and idempotent.

## Outputs

`scripts/bootstrap_repo.py`, the required directory tree and README placeholders, this ExecPlan, task/state updates, one append-only ledger record, and a focused T002 commit.

## Completion note

T002 created and validated 84 in-repository directories with idempotent README placeholders. The declared acceptance command, repeat-create checksum comparison, bytecode compilation, and independent containment assertion passed. No data were downloaded and no T003 implementation was started. The implementation commit is `748a185d1786c1a08652ce98cbe0e8c66e296dab`; the completion evidence is in the T002 record in `reports/task_ledger.jsonl`.
