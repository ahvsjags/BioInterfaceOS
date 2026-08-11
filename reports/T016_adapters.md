# T016 Source Adapter Contract Evidence

## Result

T016 is complete on the KAUST Ibex server. The project now has a typed four-method source-adapter contract, a policy gate shared by metadata/list/fetch operations, an in-memory adapter for offline contract tests, and an atomic fixture harness that removes volatile/private response fields. T017 through T025 are now READY; T017 is current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15 without real source access:

- uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 69 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_adapter_contract.py: exit 0; 4 tests passed.
- biointerfaceos lockbox self-test: exit 0.
- biointerfaceos release verify --fixture: exit 0.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- Repository state: STATE_VALID tasks=115; T017 is current and T017-T025 are dependency-ready.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- SourceAdapter requires search, metadata, list_assets, and fetch with stable typed signatures.
- Metadata, asset listing, and fetch operations require SourcePolicyEngine admission; credentialed/restricted candidates raise AdapterPolicyError before any transport.
- FixtureAdapter implements the full contract with atomic file fetch and digest verification without network.
- FixtureHarness recursively removes authorization/cookie/token/API-key/private and volatile keys, writes canonical JSON atomically, and produces byte-stable fixtures.
- No real endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/base.py
- src/biointerfaceos/sources/__init__.py
- tests/sources/test_adapter_contract.py
- docs/execplans/T016_adapter_contract.md
- reports/T016_adapters.md
- TASKS.tsv and PROJECT_STATE.yaml
- T016 sequence-11 record in reports/task_ledger.jsonl

## Commits

- c7df21687c4439af84c3ed57c38b882797c59dc2 ? T016 adapter contract, policy gate, fixture harness, and tests.
- The completion evidence commit follows this report and ledger update.
