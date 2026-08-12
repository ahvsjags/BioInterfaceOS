# T086 RedTeam agent suite

## Purpose

Implement a deterministic RedTeam agent suite that executes mandatory leakage, unit-error, negative-control, and adversarial attacks against the model and claim contracts, records severity/remediation, and preserves adverse results.

## Preconditions

T066 split-audit findings, T078 uncertainty/OOD policies, T080 typed runtime, T083 resolution audit, T084 hypothesis gates, and T085 sandboxed modeling contracts are valid.

## Non-goals

This task will not delete adverse findings, repair contaminated outputs silently, weaken a critical severity, or accept a release with an unresolved critical attack. The suite will not read locked test payloads.

## Interfaces and invariants

`biointerfaceos agent red-team --all` will execute the mandatory attack matrix, including injected leakage, unit mismatch, negative control, and adversarial claim cases. Each finding will contain attack ID, severity, evidence locator, detection status, remediation, and preserved adverse output. Critical findings block release; noncritical findings remain in the ledger.

## Implementation plan

1. Define versioned attack, finding, remediation, and severity schemas.
2. Load only development fixtures and the existing split/model/uncertainty receipts through an allowlisted typed runtime.
3. Execute mandatory attacks, including a deliberately injected leak and unit error, and compare detector outputs with expected findings.
4. Apply the critical-finding release gate, preserve raw adverse results, and seal a hash-chained attack trace.
5. Add CLI, focused tests, evidence artifacts, report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent red-team --all`
- all mandatory attacks execute; injected leakage and unit error are detected
- severity and remediation are logged; adverse results are preserved
- critical release gate, assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Block the release when a critical attack is missed or unresolved. Preserve the failing artifact and continue unrelated fixture checks; do not overwrite a prior adverse result.

## Outputs

Versioned red-team schemas, attack fixture, finding/remediation ledger, preserved adverse outputs, release gate, trace receipt, focused tests, evidence report, and state/ledger advancement.
