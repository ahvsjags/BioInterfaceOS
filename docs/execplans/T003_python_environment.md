# T003: Create reproducible Python environment

## Purpose

Create the smallest reproducible Python 3.11 environment that installs BioInterfaceOS and supports the version import smoke test required before the full CLI is implemented.

## Preconditions

T000, T001, and T002 are DONE. T003 is READY. `uv 0.12.1` and a local CPython 3.11.15 interpreter are available; the system `python` is Python 3.9.18 and must not be used for this environment.

## Non-goals

This task does not implement the T004 CLI or doctor command, install optional data/ML/GPU dependencies, download project data or models, or create later-task configuration and CI behavior.

## Interfaces and invariants

`make env` deterministically synchronizes the checked-in `uv.lock` into `.venv` using Python 3.11. After `source .venv/bin/activate`, `python -m biointerfaceos --version` prints only the package version and exits zero. Importing the core package has no third-party or undeclared system dependency.

## Implementation plan

1. Add minimal `pyproject.toml` package metadata with an exact Python 3.11 minor-series constraint and no runtime dependencies.
2. Add only `biointerfaceos.__version__` and a module version entry point under `src/biointerfaceos/`.
3. Generate and check in `uv.lock`; add a minimal `Makefile` `env` target that performs a frozen sync.
4. Record the observed interpreter, tool, lock, package, and dependency state in `reports/T003_environment.md`.
5. Validate a clean `.venv`, the declared acceptance command with documented activation, offline import after installation, and focused code checks that are actually available.
6. Only after validation, advance T003/T004 state, append one T003 completion ledger record, update this plan, and create one focused commit.

## Progress

- [x] 2026-08-11 — Read repository rules, goal, planning standard, current state, T003 contract, and prior state/ledger conventions.
- [x] 2026-08-11 — Confirmed `uv 0.12.1`, CPython 3.11.15, and system default Python 3.9.18 availability before editing.
- [x] 2026-08-11 — Added the minimal package, frozen environment target, Python 3.11 lockfile, and `reports/T003_environment.md`.
- [x] 2026-08-11 — Validated `make env`, activated version output `0.1.0`, Python 3.11.15, offline isolated import, compileall, lock consistency, and frozen offline sync, all with exit 0.
- [x] 2026-08-11 — Recorded that unittest found 0 tests and that pytest, ruff, and mypy are absent from the intentionally minimal environment; no quality-tool success was claimed.
- [x] 2026-08-11 — Advanced T003/T004 state and appended the single T003 DONE ledger record for the focused completion commit.

## Discoveries

The checkout's unactivated `python` resolves to Python 3.9.18. The required Python 3.11 is already installed at `/home/xup0a/.local/bin/python3.11`, so `uv` can use it without downloading another interpreter. Shell activation cannot persist from a Make recipe into its parent shell, so the acceptance command is run after the documented `.venv` activation.

The minimal lock contains only the editable BioInterfaceOS package. The project does not install pytest, ruff, or mypy at T003; their module invocations fail with `ModuleNotFoundError`, while standard-library unittest discovery exits zero with 0 tests. This is recorded as a limitation rather than a passed quality gate.

## Decisions

Use `uv` and constrain the project to `>=3.11,<3.12`. Keep runtime dependencies empty for the version-only core; the larger dependency families in GOAL.md belong to later capability tasks and are not installed early. Use the standard library only for the T003 entry point.

## Validation

- Remove only the ignored `.venv`, then run `make env`; expect exit 0 and a Python 3.11 environment synchronized from `uv.lock`.
- Run `source .venv/bin/activate && make env && python -m biointerfaceos --version`; expect exit 0 and the declared package version.
- Run `.venv/bin/python -I -c "import biointerfaceos; print(biointerfaceos.__version__)"`; expect exit 0 after installation without network access.
- Run `.venv/bin/python -m compileall -q src/biointerfaceos`; expect exit 0.
- Run available required quality tools and report unavailable tools or no-test collection exactly as observed.

## Failure recovery

If synchronization fails, retain the lockfile and diagnostic output, correct only environment metadata, and recreate the ignored `.venv`. Do not substitute Python 3.9 or install optional dependency groups. State files and the ledger remain unchanged until all acceptance checks pass.

## Outputs

`pyproject.toml`, `uv.lock`, `Makefile`, minimal package/version files, `reports/T003_environment.md`, this ExecPlan, task/state transitions, one append-only completion ledger record, and one focused commit.

## Completion note

T003 is complete. `uv 0.12.1` reproducibly synchronizes the existing `.venv` with CPython 3.11.15 from the checked-in lock; the editable zero-runtime-dependency package reports version `0.1.0`, imports in isolated offline mode, and compiles successfully. Lock consistency and offline frozen synchronization pass. The environment report records exact commands, versions, package state, activation, hashes, and the absence of optional quality tools. T004 remains unimplemented and is now READY.
