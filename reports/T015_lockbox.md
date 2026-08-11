# T015 Lockbox Firewall Evidence

## Result

T015 is complete on the KAUST Ibex server. Development reads under data/locked_test are denied, metadata access is separated behind an explicit filename whitelist, and selected development artifacts are scanned for forbidden field tokens and exact forbidden hashes. T016 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15 without reading locked-test payloads:

- uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 65 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_lockbox.py: exit 0; 4 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: exit 0.
- biointerfaceos catalog check: exit 0.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- LockboxFirewall rejects normal development reads under data/locked_test before opening a path, including nonexistent payload paths.
- read_metadata permits only one-level filenames in the configured metadata whitelist and parses JSON objects conservatively.
- ContaminationScanner scans only caller-selected, repository-contained development artifacts, detects configured forbidden fields and exact SHA-256 matches, and rejects lockbox paths.
- lockbox self-test exercises a clean fixture, a contaminated fixture, blocked lockbox access, and writes reports/lockbox_audit.json.
- No actual lockbox payload was opened, hashed, summarized, or copied.

## Artifacts

- config/lockbox.yaml
- src/biointerfaceos/lockbox.py
- tests/test_lockbox.py
- tests/fixtures/lockbox
- reports/lockbox_audit.json
- src/biointerfaceos/cli.py
- docs/execplans/T015_lockbox_firewall.md
- reports/T015_lockbox.md
- TASKS.tsv and PROJECT_STATE.yaml
- T015 sequence-10 record in reports/task_ledger.jsonl

## Commits

- 2a735946ee999b8d9ce169c13042b1027e5a91a6 ? T015 firewall, scanner, fixtures, CLI, and audit receipt.
- The completion evidence commit follows this report and ledger update.
