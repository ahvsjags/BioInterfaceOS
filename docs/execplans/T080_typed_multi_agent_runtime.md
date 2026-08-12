# T080 Typed multi-agent runtime

## Purpose

Implement the typed multi-agent runtime declared in GOAL.md, with schema-validated agent contracts, explicit tool allowlists, budgets, deterministic replay, retries, and append-only traces. CI must use mock/rule backends and require no provider key.

## Preconditions

T004/T006/T007 contract and orchestration foundations plus T068 benchmark grading are valid. Runtime events must be serializable, replayable, and auditable without network access.

## Non-goals

This task will not invoke live providers in CI, accept undeclared tools, exceed per-agent budgets, or rewrite append-only traces during retry or replay.

## Interfaces and invariants

`biointerfaceos agent self-test` will validate agent/task/event schemas, tool allowlists, budget exhaustion, deterministic replay, retry behavior, and append-only trace seals. A mock/rule backend remains the required fallback when any optional backend is unavailable.

## Implementation plan

1. Define typed agent, task, tool-call, result, retry, and trace schemas.
2. Implement allowlist and budget enforcement around a deterministic mock/rule backend.
3. Add retry and replay semantics with stable event IDs and append-only trace hashing.
4. Add CLI self-test, fixtures, focused tests, logs, and failure ledger.
5. Add evidence report and state/ledger advancement after all repository gates pass.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent self-test`
- schema validation, tool allowlist, budget, replay, retry, trace seal, and no-provider-key assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Disable a failing optional backend and keep the mock/rule runtime active. Reject undeclared tool calls, stop at budget exhaustion, and preserve the original trace when retries or replay diverge.

## Outputs

Versioned runtime schemas, typed runtime implementation, mock/rule fixtures, self-test CLI, append-only traces, focused tests, evidence report, and state/ledger advancement.
