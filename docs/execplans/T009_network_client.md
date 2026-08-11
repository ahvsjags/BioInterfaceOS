# T009: Implement resilient anonymous network client

## Purpose

Provide a deterministic, credential-free HTTP client for official anonymous sources before source registry and acquisition work begins.

## Preconditions

T003 and T005 are DONE, T009 is READY/current, the Git worktree is clean, and no network access is needed for validation.

## Non-goals

This task does not access scientific sources, download data, implement source policy or manifests, add dependencies, or inspect locked-test content.

## Interfaces and invariants

`NetworkConfig` validates timeouts, bounded retry and pacing values, exposes one fixed project User-Agent, and optionally restricts hosts. `AnonymousHttpClient` accepts injected opener, sleep, and monotonic clock functions. It emits only GET requests with the fixed User-Agent plus an internal Range header for resume. Credential headers are rejected and environment credentials are never read. Downloads stay within the repository, retain `.part` files on failure, and replace destinations only after SHA-256 verification.

## Implementation plan

1. Add a typed stdlib-only network module with retry, rate limiting, JSON, pagination, and resumable checksum-verified download behavior.
2. Add fully mocked focused tests under `tests/network/`.
3. Run focused and repository-wide offline validation.
4. Record evidence, advance T009/T010 state, append one sealed ledger record, and commit.

## Progress

- [x] 2026-08-12 — Read the execution contract, current state, task row, and T008 plan/evidence; created this ExecPlan.
- [x] 2026-08-12 ? Implemented stdlib-only client, deterministic pagination, resumable downloads, and 8 fully mocked tests.
- [x] 2026-08-12 ? Offline lock, sync, full check (33 passed), focused tests (8 passed), compileall, state, ledger, and containment gates passed.

## Discoveries

No active ExecPlan existed before T009. Existing foundation code targets Python 3.11 and already supplies an append-only hash-sealed task ledger.

## Decisions

Use `urllib.request` and related standard-library exceptions. Treat only integer Retry-After delta-seconds in a conservative bounded range as safe; otherwise use deterministic exponential backoff. Use SHA-256 as the completion authority for downloads.

## Validation

- `uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `UV_OFFLINE=1 .venv/bin/pytest -q tests/network`
- `.venv/bin/python -m compileall -q src tests`
- `git diff --check`
- repository containment assertions over changed and staged paths

## Failure recovery

Mock failures leave no destination promotion. Interrupted or checksum-failed downloads retain `<destination>.part` for diagnosis/resume. Correct the module or fixture and rerun offline; do not remove raw data or ledger history.

## Outputs

`src/biointerfaceos/network.py`, `tests/network/test_client.py`, this ExecPlan, `reports/T009_network.md`, task/state advancement, one T009 ledger record, and a focused commit.

## Completion note

T009 is complete. The anonymous client and fully mocked network tests passed all acceptance gates. The implementation commit is 688520342c07322aa79495bb9ccb6e030a094dd4 and the completion evidence is in reports/T009_network.md and the sequence-4 task ledger record. T010 is READY/current. No public scientific data, models, credentials, or locked-test payloads were accessed.
