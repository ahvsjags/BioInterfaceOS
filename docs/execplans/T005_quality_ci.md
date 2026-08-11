# T005: Add formatting, typing, tests, and CI

## Purpose

Establish one reproducible local and CI quality gate for the Python 3.11 foundation package.

## Preconditions

T000 through T004 are DONE, T005 is READY/current, the Git worktree is clean, and the T004 CLI and tests are present. `uv` 0.12.1 and CPython 3.11 are available locally.

## Non-goals

This task does not implement T006 or later functionality, download scientific data or models, add ML/GPU dependencies, or make network calls from tests.

## Interfaces and invariants

`make check` runs, in order, `ruff check`, `ruff format --check`, `mypy`, and `pytest` through the frozen uv environment. All development tools are exactly pinned. Tests use repository-local inputs and standard-library process/stream fixtures only. CI has read-only repository permissions and requires no secrets.

## Implementation plan

1. Add exact development dependency pins and tool configuration to `pyproject.toml`, then regenerate `uv.lock`.
2. Add the four-command `Makefile` quality gate and a Python 3.11 GitHub Actions workflow.
3. Adjust only existing CLI code/tests where the configured checks identify an issue.
4. Run the frozen check gate offline after environment synchronization and record exact evidence in `reports/T005_quality.md`.
5. Advance T005 to DONE, make T006 current/READY and T007 READY, append exactly one T005 DONE ledger object, update this plan, commit, and verify a clean worktree.

## Progress

- [x] 2026-08-11 — Read repository instructions, goal, planning standard, state, T005/T006/T007 task rows, and T005 input files.
- [x] 2026-08-11 — Added exact tool pins, project configuration, the local quality target, and secret-free CI workflow.
- [ ] 2026-08-11 — Lock, synchronize, run all acceptance checks, and record evidence.
- [ ] 2026-08-11 — Complete state, task, ledger, plan, report, commit, and clean-status verification.

## Discoveries

T004 intentionally left ruff, mypy, and pytest absent. Its three standard-library CLI tests are already pytest-discoverable and contain no network or external-data access. An initial repository-wide ruff probe found pre-existing T000/T002 script findings outside T005 scope, so the gate targets the Python package and its tests; those are the declared T005 input and the same paths checked by strict mypy.

## Decisions

Keep development tools in uv's `dev` dependency group so the runtime package remains dependency-free. Invoke tools via `uv run --frozen` so local and CI commands use lock-resolved executables and cannot silently change the lock.

## Validation

- `uv lock --check`
- `uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `git diff --check`
- `git status --short`

The lock check, sync, all four quality tools, and whitespace check must exit zero. Pytest must collect and pass the existing CLI tests without network, data, model, or GPU access.

## Failure recovery

Correct only T005 configuration or current CLI test compatibility, refresh the lock deliberately, and rerun the full gate. Do not update completion state or append the ledger until all acceptance checks pass.

## Outputs

Pinned development dependencies and tool configuration, `uv.lock`, `Makefile`, `.github/workflows/ci.yml`, this ExecPlan, `reports/T005_quality.md`, state/task transitions, one ledger object, and a focused commit.

## Completion note

Pending acceptance validation.
