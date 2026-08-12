# T085 ModelBuilder and Statistician agents

## Purpose

Implement typed ModelBuilder and Statistician agents that produce executable analysis plans, generated tests, and preregistration records inside a sandbox while rejecting metric hacking and preserving the frozen data splits.

## Preconditions

T080 typed runtime, T068 benchmark grading, T071 mixed-effects diagnostics, T078 calibrated uncertainty, the frozen split ledgers, and the T084 exploratory hypothesis contracts are valid.

## Non-goals

This task will not modify train/validation/test assignments, tune on held-out targets, optimize a metric after inspecting evaluation results, write outside the execution sandbox, or treat an agent-generated plan as an accepted analysis.

## Interfaces and invariants

`biointerfaceos agent eval modeling` will emit typed model and statistician plans, generated test cases, preregistration fields, sandbox execution receipts, metric-hacking findings, and split-integrity checks. Plans must compile/run in the sandbox, tests and preregistration must be present, metric-hacking traps must be rejected, and the original split hashes must remain unchanged.

## Implementation plan

1. Define versioned schemas for model plans, statistical checks, preregistration, sandbox commands, and rejection findings.
2. Route fixture task specifications and allowlisted model APIs through the typed runtime with explicit budgets.
3. Generate one valid plan and adversarial plans that attempt post-hoc metric selection, split modification, or held-out tuning.
4. Execute only the valid plan in a temporary sandbox; compile generated tests and verify preregistration completeness.
5. Compare before/after split hashes, persist rejection and execution ledgers, add CLI/tests/report, and advance state.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent eval modeling`
- generated valid plan compiles/runs inside sandbox
- tests and preregistration are generated
- metric-hacking traps are rejected and split hashes are unchanged
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Return proposal-only plans to the deterministic CI gate when sandbox execution or schema validation fails. Reject any plan that changes split files, uses held-out targets, or selects metrics after evaluation; preserve the plan and rejection reason for review.

## Outputs

Versioned modeling contracts, task fixture, valid and rejected plans, generated tests, preregistration, sandbox receipt, split-integrity audit, focused tests, evidence report, and state/ledger advancement.
