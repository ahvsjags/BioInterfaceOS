# T083 Resolution and EvidenceAuditor agents

## Purpose

Implement typed resolution and evidence-audit agents that detect injected unit/entity/evidence conflicts, control false merges, preserve every original assertion, and quarantine unresolved records while retaining deterministic resolver behavior.

## Preconditions

T080 typed runtime, T039/T041–T044 resolution/evidence foundations, ontology adapters, and candidate record contracts are valid. Existing deterministic resolvers remain the reference fallback.

## Non-goals

This task will not silently merge conflicting entities, overwrite original evidence, infer units without evidence, or accept an unresolved conflict as a clean resolution.

## Interfaces and invariants

`biointerfaceos agent eval audit` will run unit/entity/evidence conflict cases, emit resolution decisions and audit findings, preserve original assertions, quarantine unresolved cases, and report false-merge rate against deterministic fallback.

## Implementation plan

1. Define typed resolution candidates, evidence assertions, conflict findings, and quarantine decisions.
2. Route unit, entity, and evidence cases through allowlisted deterministic resolver/auditor tools.
3. Inject known conflicts and verify they are detected without mutating original assertions.
4. Compare agent decisions with deterministic resolver baseline and apply false-merge acceptance gate.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent eval audit`
- injected unit/entity/evidence conflicts detected, original assertions preserved, false-merge rate controlled, unresolved records quarantined
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Quarantine unresolved records and use deterministic resolver outputs as fallback. Preserve all source assertions and record any agent disagreement in the failure ledger.

## Outputs

Versioned audit contracts, conflict fixture, resolution decisions, evidence findings, quarantine records, comparison metrics, focused tests, evidence report, and state/ledger advancement.
