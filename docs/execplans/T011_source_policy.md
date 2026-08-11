# T011: Implement source and license policy engine

## Purpose

Enforce BioInterfaceOS anonymous-access and licensing constraints before any source acquisition. Every candidate receives a deterministic admit, analysis-only, quarantine, or rejection decision with explicit evidence.

## Preconditions

T010 is DONE, T011 is READY/current, the manifest and Parquet runtime validate, and no real source or locked-test payload needs to be accessed.

## Non-goals

This task does not search the web, download source assets, infer missing licenses, bypass access controls, or make scientific inclusion claims.

## Interfaces and invariants

PolicyConfig is loaded from configs/source_policy.yaml with default-deny rules. SourceCandidate records access prerequisites, license text/identifier, and evidence location. License classification uses exact configured identifiers and conservative text patterns only. Any login, registration, API key, application, approval, institution, data-use agreement, or payment requirement is rejected as REJECTED_CREDENTIALLED. Unclear or unsupported redistribution is QUARANTINE. Explicit restricted rights are REJECTED_RESTRICTED_LICENSE. CC0 and CC BY are public-redistributable; CC BY-NC is analysis-only. Every rejection or quarantine is appended to a fixed-schema registry/rejected_sources.parquet atomically.

## Implementation plan

1. Add configs/source_policy.yaml with explicit default-deny access and license rules.
2. Implement typed candidate parsing, exact license classification, policy decisions, and an atomic Parquet rejection registry.
3. Add source policy self-test CLI and fixture set covering all required rejection/admission cases.
4. Run focused/full offline checks, CLI/schema/state/ledger validation, and ensure no real network access.
5. Record evidence, advance T011/T012 state, append one task-ledger record, and commit.

## Progress

- [x] 2026-08-12 ? Read GOAL access/license constraints, T011 contract, T010 manifest API, and selected conservative default-deny policy.
- [ ] Implement and test the policy engine.
- [ ] Run acceptance gates and record completion evidence.

## Discoveries

The source manifest runtime already provides PyArrow 17.0.0 and atomic Parquet writing patterns. The project uses lower-case manifest statuses while GOAL policy decisions use explicit uppercase decision codes; the policy layer will preserve both without conflating them.

## Decisions

Use exact normalized license identifiers and a small reviewed phrase table. Unknown text never becomes an admission. Access prerequisites are evaluated before license classification so credentialed sources are rejected even when their license text looks permissive.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_policy.py
- .venv/bin/biointerfaceos source policy self-test
- .venv/bin/biointerfaceos source manifest validate
- .venv/bin/python -m compileall -q src tests
- git diff --check
- rejection-registry Parquet round-trip and no-network assertions

## Failure recovery

Policy decisions are pure and deterministic; a failed fixture does not contact a source. Rejection registry writes use same-directory temporary files and atomic replacement. Preserve prior registry bytes and ledger history if validation fails.

## Outputs

configs/source_policy.yaml, src/biointerfaceos/policy.py, registry/rejected_sources.parquet, tests/fixtures/policy, tests/test_policy.py, source policy CLI, this ExecPlan, reports/T011_policy.md, state advancement, and task-ledger evidence.

## Completion note

Pending implementation and acceptance validation.
