# T081 SourceScout and LicenseGate agents

## Purpose

Implement typed SourceScout and LicenseGate agent workflows on top of T080. SourceScout must recover eligible anonymous sources; LicenseGate must reject restricted or credentialed cases, cite metadata evidence for every decision, and request no credentials.

## Preconditions

T080 typed runtime, T017–T020 source adapters/policy, T024 evidence, and T011 metadata foundations are valid. Deterministic adapters and policy fixtures are available for CI.

## Non-goals

This task will not contact credentialed endpoints, ask for API keys, bypass access controls, or treat source identity as evidence of license eligibility.

## Interfaces and invariants

`biointerfaceos agent eval source-license` will execute SourceScout and LicenseGate over a sanitized fixture, emit per-case metadata evidence locators, and report recovery/rejection metrics. Restricted, login, approval, payment, and unknown-license cases must be rejected or quarantined by policy.

## Implementation plan

1. Define typed source candidate, license evidence, scout decision, and gate decision schemas.
2. Implement deterministic source adapters and policy-backed LicenseGate decisions using no-network fixtures.
3. Add benchmark cases for eligible recovery and injected restricted/credentialed rejection.
4. Emit evidence-linked decisions, failure ledger, receipt, and manifest; measure agent value against deterministic fallback.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent eval source-license`
- every decision cites metadata evidence; eligible sources recover; restricted cases reject/quarantine; no credential requests
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Disable an unavailable adapter and use the deterministic policy fallback. Record agent value as zero if it does not improve the fallback, and preserve restricted cases in the rejection registry.

## Outputs

Versioned source-license schemas, SourceScout/LicenseGate implementation, benchmark fixture, evidence-linked decisions, rejection audit, focused tests, evidence report, and state/ledger advancement.
