# T016: Create source adapter interface and fixture harness

## Purpose

Define one auditable contract for anonymous public-source adapters and a deterministic fixture recorder that strips volatile/private response fields before tests or evidence are committed.

## Preconditions

T011 and T015 are DONE, T016 is READY/current, the anonymous network client and policy engine exist, and no real source endpoint is needed.

## Non-goals

This task does not implement a live provider, perform source discovery, download scientific assets, or read locked-test payloads.

## Interfaces and invariants

SourceAdapter requires search, metadata, list_assets, and fetch methods. Adapter methods must call policy admission before network-bearing fetches and return typed metadata/assets. FixtureHarness canonicalizes JSON-like payloads, removes configured volatile/private keys, rejects credential-bearing fields, writes stable JSON fixtures atomically, and can reload them. A contract test must run fully offline.

## Implementation plan

1. Add typed adapter protocol, policy gate, asset descriptor, and fixture recorder.
2. Add an in-memory fixture adapter for contract tests.
3. Add mock-only adapter contract tests covering all four methods, policy rejection, deterministic fixtures, and private-field stripping.
4. Run offline lock/sync, full/focused tests, state/schema/lockbox/release checks, compileall, and diff checks.
5. Record evidence, advance T016/T017/T018/T019/T020/T024 state as dependencies allow, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read T016 contract, source-adapter requirements, policy engine, network client, and fixture protections.
- [x] 2026-08-12 ? Implemented four-method adapter contract, policy gate, fixture adapter, redaction harness, and 4 tests.
- [x] 2026-08-12 ? Offline lock/sync, full check (69 passed), focused tests (4 passed), lockbox/release/state, compileall, and diff gates passed.

## Discoveries

The project already has separate NetworkConfig/AnonymousHttpClient and SourcePolicyEngine components. The adapter contract can require both by composition without duplicating transport or licensing logic.

## Decisions

Use an abstract base class with explicit four-method signatures and a policy gate helper. Keep fixture recording independent of any provider and redact private keys recursively before writing.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_adapter_contract.py
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- .venv/bin/python -m compileall -q src tests
- git diff --check
- contract, policy, redaction, and deterministic fixture assertions

## Failure recovery

A fixture write uses a same-directory temporary file and atomic replace. If a contract test fails, keep the failing payload in a temporary directory and do not contact any real source. Adapters that bypass policy remain rejected.

## Outputs

src/biointerfaceos/sources/base.py, src/biointerfaceos/sources/__init__.py, tests/sources/test_adapter_contract.py, tests/fixtures/sources, this ExecPlan, reports/T016_adapters.md, state advancement, and task-ledger evidence.

## Completion note

T016 is complete. Implementation commit c7df21687c4439af84c3ed57c38b882797c59dc2 and evidence report reports/T016_adapters.md are recorded with the sequence-11 task ledger entry. T017-T025 are READY; T017 is current. No source or locked-test payload was accessed.
