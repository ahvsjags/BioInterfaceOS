# T006 State and Ledger Evidence

## Result

T006 is complete on the KAUST Ibex server. The project state manager validates the 115-task DAG and YAML/TSV summary, rejects invalid status transitions, selects the next dependency-satisfied task deterministically, and supports safe append-only JSONL ledger recovery. T007 is now READY and current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- uv lock --check: exit 0; lock contains pinned pyyaml==6.0.2.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; ruff 0.12.12, mypy 1.17.1, pytest 8.4.2.
- pytest: 11 passed.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/biointerfaceos state next: T007.
- .venv/bin/python -m unittest -v tests.test_state_ledgers: 8 tests passed.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.

## Implemented artifacts

- src/biointerfaceos/state.py: typed YAML/TSV parsing, task DAG/status validation, READY/IN_PROGRESS current-task support, deterministic next-task selection, and strict DONE transition checks.
- src/biointerfaceos/ledgers.py: canonical JSONL appends, per-record sequence/hash metadata, atomic seal/snapshot files, tamper/truncation detection, unique quarantine recovery, and idempotent standard-ledger initialization.
- src/biointerfaceos/cli.py: real state validate and state next commands; other future command families remain explicit nonzero stubs.
- tests/test_state_ledgers.py: state, transition, initialization, hash-chain, tamper, truncation, quarantine, and legacy-prefix tests.
- reports/decision_ledger.jsonl, reports/blocker_ledger.jsonl, and registry/experiment_ledger.jsonl, each initialized idempotently with a seal and snapshot.
- reports/task_ledger.jsonl: historical prefix preserved and T006 completion appended with integrity metadata.

## Recovery invariant

Existing ledger bytes are never rewritten during initialization. A corrupt ledger is copied to a unique .corrupt.<uuid> quarantine path, then restored from the last sealed byte-exact snapshot; the quarantine artifact is retained.

## Commits

- b40f735d66de354ab26bf72ce965ff4a275a9bc7 ? T006 implementation.
- 408c12395a1b7fe52ee2f33df52739d9cd2973df ? allow READY as the current next task state.

## Limitations

No public scientific data, models, or locked-test payloads were accessed. T007 schema/configuration work remains pending.
