# T084 Mechanism and hypothesis agents

## Purpose

Implement an exploratory Mechanism and hypothesis agent workflow that proposes formal, evidence-linked, falsifiable mechanisms from training-only evidence and model residuals without accepting any claim automatically.

## Preconditions

T080 typed runtime, T062 model residual outputs, T076 hierarchical causal-world artifacts, the lockbox policy, and the T083 resolution/evidence audit contracts are valid. Curated seed hypotheses are the only fixture inputs.

## Non-goals

This task will not treat an agent proposal as a scientific conclusion, train on validation or test evidence, read locked development payloads, silently duplicate hypotheses, or infer unsupported causal claims.

## Interfaces and invariants

`biointerfaceos agent eval hypothesis` will emit typed hypothesis proposals, mechanism links, falsifiability tests, evidence locators, duplicate checks, residual summaries, and a rejection ledger. Every proposal must be exploratory, evidence-linked, formally structured, and explicitly marked as unaccepted. The lockbox scan must report zero contamination and the deterministic fallback must remain available.

## Implementation plan

1. Define versioned schemas for mechanism proposals, evidence links, falsifiability criteria, and acceptance status.
2. Route curated seed hypotheses and training-only residual summaries through allowlisted typed runtime tools.
3. Generate deliberately overlapping and unsupported candidates, then reject duplicates and unsupported claims deterministically.
4. Verify evidence links, formalization, falsifiability, split provenance, lockbox isolation, and no-automatic-acceptance invariants.
5. Add CLI, focused tests, evidence artifacts, report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent eval hypothesis`
- proposals are nonduplicate, falsifiable, formalized, evidence-linked, and exploratory
- lockbox contamination scan is zero and no claim is automatically accepted
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Reject or quarantine proposals with missing evidence, unsupported mechanisms, duplicate normalized forms, or non-training provenance. Preserve every candidate and rejection reason, and fall back to the deterministic hypothesis baseline when the agent metric does not improve.

## Outputs

Versioned hypothesis contracts, curated seed fixture, proposal and rejection artifacts, falsifiability and provenance checks, lockbox scan, focused tests, evidence report, and state/ledger advancement.
