# T015: Implement lockbox firewall and contamination scanner

## Purpose

Prevent development commands from reading locked-test payloads and detect forbidden fields or known locked hashes in candidate artifacts before they can enter a release.

## Preconditions

T006 and T014 are DONE, T015 is READY/current, the fixture release verifies, and no locked-test payload needs to be opened.

## Non-goals

This task does not unlock, inspect, summarize, or hash any real locked-test payload. It does not evaluate the locked test or alter frozen releases.

## Interfaces and invariants

LockboxFirewall rejects all development reads under data/locked_test and permits only an explicit metadata filename whitelist through a separate method. ContaminationScanner scans caller-provided, repository-contained development artifacts for configured forbidden field tokens and exact forbidden SHA-256 values, while rejecting locked-test paths. A self-test produces an audit receipt without reading real locked content.

## Implementation plan

1. Add config/lockbox.yaml with the path, metadata whitelist, and forbidden field policy.
2. Implement path firewall, metadata-only access, byte/hash scanner, deterministic findings, and audit receipt.
3. Add lockbox self-test CLI and local clean/contaminated fixtures.
4. Run offline lock/sync, full/focused tests, self-test, state/schema/ledger checks, compileall, and diff checks.
5. Record evidence, advance T015/T016 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read T015 contract, GOAL lockbox rules, current locked-test placeholder state, and release firewall constraints.
- [x] 2026-08-12 ? Implemented path firewall, metadata whitelist, forbidden field/hash scanner, CLI, receipt, and 4 tests.
- [x] 2026-08-12 ? Offline lock/sync, full check (65 passed), focused tests (4 passed), lockbox self-test, state, compileall, and diff gates passed.

## Discoveries

The committed data/locked_test directory contains only its placeholder README. Development tests can exercise the firewall against temporary lockbox paths without touching this protected project path.

## Decisions

Use an explicit metadata method and filename allowlist rather than a general read exception. Scan only caller-provided development artifacts, not the whole repository, because GOAL and policy documentation intentionally contain words that describe forbidden fields.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_lockbox.py
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos state validate
- .venv/bin/python -m compileall -q src tests
- git diff --check
- firewall, metadata whitelist, forbidden-field/hash, and no-locked-read assertions

## Failure recovery

A blocked path access returns an auditable error without opening the path. Contamination findings are preserved in the audit receipt; quarantine or rebuild the affected development artifact rather than deleting locked data. Never relax the whitelist to make a test pass.

## Outputs

config/lockbox.yaml, src/biointerfaceos/lockbox.py, tests/test_lockbox.py, tests/fixtures/lockbox, reports/lockbox_audit.json, lockbox self-test CLI, this ExecPlan, reports/T015_lockbox.md, state advancement, and task-ledger evidence.

## Completion note

T015 is complete. Implementation commit 2a735946ee999b8d9ce169c13042b1027e5a91a6 and evidence report reports/T015_lockbox.md are recorded with the sequence-10 task ledger entry. T016 is READY/current. No locked-test payload was accessed.
