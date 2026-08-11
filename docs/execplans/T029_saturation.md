# T029: Compute search saturation and coverage gaps

## Purpose

Measure diminishing returns and coverage gaps from the T027 seed registry plus T028 expansion graph, then propose targeted query blocks and explicit stopping criteria without claiming exhaustive coverage.

## Preconditions

T027 and T028 are DONE. The frozen query matrix, deduplicated candidate registry, and bounded expansion edge registry are available. The lockbox interval remains excluded.

## Non-goals

This task will not access lockbox payloads, tune queries against hidden outcomes, claim literature completeness, or download scientific binaries.

## Interfaces and invariants

Saturation is reported by batch and query axis using fixture-backed, provenance-tracked records. Novel eligible-study yield is separated from duplicate-family yield, quarantined records, and metadata-only targets. Coverage gaps must identify missing years, materials, endpoints, or source axes with evidence and proposed query additions. Stopping criteria must be explicit and reproducible.

## Implementation plan

1. Define saturation metrics over search receipts, candidates, and expansion edges.
2. Compute batch/axis yields, duplicate rates, policy outcomes, and coverage-gap flags from committed fixtures.
3. Generate an HTML report with gap query proposals and stopping criteria.
4. Add CLI command biointerfaceos search saturation and focused tests.
5. Run the full gate suite, validate all ledgers, and record completion evidence.

## Progress

- [ ] Define saturation and coverage-gap metrics.
- [ ] Implement fixture-backed saturation report and CLI.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos search saturation
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check
- append-only ledger validation and deterministic gap assertions

## Failure recovery

Preserve prior search and expansion ledgers. If a report build fails, repair only the derived report or fixture-backed metric code; do not rewrite candidate or edge records.

## Outputs

reports/search_saturation.html, gap query proposals, saturation fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
