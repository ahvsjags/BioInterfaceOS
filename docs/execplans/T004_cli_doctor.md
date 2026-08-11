# T004: Implement CLI and doctor command

## Purpose

Provide a dependency-light command-line entry point that can verify the repository foundation before later data, modeling, agent, claim, and release capabilities are implemented.

## Preconditions

T000 through T003 are DONE, T004 is READY, the repository is clean, and the Python 3.11 environment and T002 skeleton already exist.

## Non-goals

This task does not implement state management, storage, data acquisition, extraction, splitting, benchmarks, training, agents, claim gates, or releases. It does not install optional quality or scientific packages, download data or models, or inspect locked-test content.

## Interfaces and invariants

`biointerfaceos doctor --strict` checks only mandatory foundation facts and exits nonzero if any fail. Output uses `PASS`, `WARN`, and `NOT_IMPLEMENTED` labels and never represents future commands as functional. The commands `state`, `data`, `source`, `extract`, `split`, `benchmark`, `train`, `agent`, `claim`, `release`, and `storage` are discoverable and always exit nonzero with `NOT_IMPLEMENTED`. `python -m biointerfaceos --version` remains supported.

## Implementation plan

1. Add `src/biointerfaceos/cli.py`, route the module entry point through it, and register the console script in `pyproject.toml`.
2. Add standard-library unit tests for strict doctor success, help discovery, and explicit future-command failure.
3. Refresh `uv.lock`, synchronize the environment, and run all T004 acceptance checks.
4. Record exact validation evidence in `reports/T004_doctor.md`.
5. After every acceptance check passes, advance T004/T005 state, append one T004 DONE ledger record, verify staged containment, and commit focused changes.

## Progress

- [x] 2026-08-11 — Read the repository contract, goal, planning rules, state, T004 task row, T003 plan, package skeleton, and ledger conventions.
- [x] 2026-08-11 — Implemented the stdlib CLI, strict doctor, explicit future-command stubs, console entry point, and three unittest cases.
- [x] 2026-08-11 — Passed lock consistency, frozen environment sync, installed strict doctor, both version paths, unittest, compileall, and diff checks; recorded optional tool absence.
- [ ] 2026-08-11 — Record validation and advance task state.

## Discoveries

The T003 environment intentionally contains no runtime dependencies and does not install pytest, ruff, or mypy. T004 therefore uses `argparse`, `importlib`, `pathlib`, and `unittest` from the standard library.

## Decisions

Doctor validates the stable top-level T002 skeleton rather than importing the bootstrap script or claiming every future subsystem is usable. Optional quality-tool availability is informational and cannot turn a mandatory foundation failure into success.

## Validation

- `uv lock --check`
- `make env`
- `.venv/bin/biointerfaceos doctor --strict`
- `.venv/bin/biointerfaceos --version`
- `.venv/bin/python -m biointerfaceos --version`
- `.venv/bin/python -m unittest -v tests.test_cli`
- `.venv/bin/python -m compileall -q src/biointerfaceos tests/test_cli.py`
- Probe pytest, ruff, and mypy and report absence honestly.

All first seven commands must exit zero. Every future command tested by unittest must emit `NOT_IMPLEMENTED` and exit nonzero.

## Failure recovery

Correct only T004 files and rerun validation. Do not update state or append the completion ledger until all mandatory acceptance checks pass. The ledger receives exactly one T004 DONE record.

## Outputs

CLI modules, console-script metadata and lock refresh, `tests/test_cli.py`, `reports/T004_doctor.md`, this ExecPlan, task/state transitions, one ledger record, and focused commits if completion evidence requires a follow-up.

## Completion note

The T004 implementation and acceptance checks are complete. The strict doctor validates only the mandatory foundation and exits zero with no failures; all future command families remain explicit nonzero stubs. Completion state and the single ledger record are recorded after the focused implementation commit so their evidence can reference an existing commit.
