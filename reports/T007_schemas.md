# T007 Schema and Configuration Evidence

## Result

T007 is complete on the KAUST Ibex server. Nine version-one JSON Schema contracts, a deterministic validator, strict YAML configuration loading, repository containment checks, offline fixtures, and the schema validate-all CLI are implemented. T008 and T009 are now READY; T008 is current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- uv lock --check: exit 0; no dependency change was needed.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; ruff 0.12.12, mypy 1.17.1, pytest 8.4.2.
- pytest: 20 passed across CLI, T006, and T007 tests.
- .venv/bin/biointerfaceos schema validate-all: SCHEMA_VALID schemas=9 fixtures=9.
- .venv/bin/python -m pytest -q tests/test_schema_config.py: 9 passed.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/biointerfaceos state next: T007 before completion; T008 after completion state transition.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.

## Implemented artifacts

- src/biointerfaceos/schema.py: versioned schema discovery, definition checks, recursive type/enum/bounds/required/closed-object validation, field-path errors, safe YAML loading, and containment.
- schemas/*.v1.json: material, bioenvironment, protocol, evidence, corona, response, source, agent, and claim contracts.
- tests/fixtures/schema/*.v1.yaml: one valid offline envelope per contract.
- src/biointerfaceos/cli.py: schema validate-all command.
- tests/test_schema_config.py: success, invalid path, unknown field, enum/type, version, containment, invalid schema, and bool-vs-integer checks.
- reports/T007_schemas.md: this evidence report.

## Design constraints

The subsystem uses only the already pinned PyYAML runtime dependency and the standard library. JSON Schema artifacts are draft 2020-12 documents; the validator deliberately supports the closed subset required by T007. JSON booleans are rejected where integers or numbers are required.

## Commits

- a8710fc2e6646388f8f6c8e14c9dac7abf9cb915 ? T007 implementation.
- The final state, report, task-ledger, and evidence commit follows after this verified implementation.

## Limitations

No public scientific data or models were accessed. Locked-test payloads were not accessed. T008/T009 execution remains pending.
