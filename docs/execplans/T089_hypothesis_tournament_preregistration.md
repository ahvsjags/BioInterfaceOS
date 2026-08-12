# T089 Hypothesis tournament and preregistration rules

## Purpose

Freeze the exploratory hypothesis tournament configuration and preregistration rules before primary analyses, including ranking weights, primary outcomes, exclusions, minimum effects, duplicate removal, and lockbox isolation.

## Preconditions

T065 frozen development splits, T084 exploratory hypotheses, T085 modeling/preregistration contracts, T086 red-team gates, T087 reproducibility/lockbox evaluator, and T088 benchmark evidence are valid.

## Non-goals

This task will not rank hypotheses using validation/test targets, silently alter weights after seeing outcomes, retain normalized duplicates, accept an exploratory proposal as a scientific claim, or read locked payloads.

## Interfaces and invariants

`biointerfaceos claim preregister --dev` will emit a versioned tournament config, preregistration receipt, candidate ranking, duplicate exclusion ledger, and lockbox scan. K, weights, primary outcomes, exclusion rules, minimum effects, and tests are frozen before the primary ranking. Every selected item remains exploratory until downstream evidence gates pass.

## Implementation plan

1. Define schemas for tournament configuration, candidate claims, ranking outcomes, exclusions, and preregistration hash receipts.
2. Load only T084 training-only proposals, T085 preregistration fields, and frozen split metadata.
3. Remove normalized duplicate hypotheses and reject candidates missing formalization, evidence, or falsifiability.
4. Freeze K, weights, outcomes, exclusions, minimum effects, and tests before ranking; scan lockbox paths and assert zero contamination.
5. Add CLI, focused tests, evidence artifacts, report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos claim preregister --dev`
- configuration hash is captured before ranking
- duplicates removed, lockbox scan clean, and exploratory status retained
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Mark any post-hoc change as exploratory version N+1 and never overwrite a frozen receipt. Reject candidates with duplicate keys or incomplete evidence and preserve the exclusion reason.

## Outputs

Versioned tournament schema/config, preregistration receipt, ranking and exclusion ledgers, lockbox scan, focused tests, evidence report, and state/ledger advancement.
