# T009 Network Client Evidence

## Result

T009 is complete on the KAUST Ibex server. The repository now has a credential-free, standard-library HTTP client with fixed User-Agent policy, host allowlisting, bounded retries, Retry-After handling, pacing, deterministic pagination, resumable downloads, SHA-256 verification, and atomic promotion. T010 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15 without real network access:

- uv lock --check: exit 0; lock unchanged.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 33 tests passed, ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/network: exit 0; 8 tests passed.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- All four append-only ledgers validated successfully, including the task-ledger hash chain and seals.

## Implemented behavior

- NetworkConfig rejects non-positive or unbounded policy values, credential-bearing/custom headers, non-fixed User-Agent values, malformed allowlists, and URL credentials.
- AnonymousHttpClient emits only GET requests with the fixed project User-Agent and an internal Range header for resume. Timeout, URL, 429, and 5xx failures use bounded deterministic retries; other 4xx responses do not retry.
- Rate pacing and injectable opener/sleep/clock functions make behavior deterministic and fully mockable.
- Pagination follows absolute or relative next URLs with cycle and page-count guards.
- Downloads use a sibling .part file, honor compatible 206 responses, restart safely when a server ignores Range, retain failed partials, verify expected SHA-256, and atomically replace only after verification.
- Destination and partial paths are repository-contained. No scientific source, model, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/network.py
- tests/network/test_client.py
- docs/execplans/T009_network_client.md
- reports/T009_network.md
- TASKS.tsv and PROJECT_STATE.yaml
- T009 sequence-4 record in reports/task_ledger.jsonl

## Commits

- 688520342c07322aa79495bb9ccb6e030a094dd4 ? T009 implementation and focused mock tests.
- The completion evidence commit follows this report and ledger update.
