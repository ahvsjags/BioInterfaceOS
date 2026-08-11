# T030: Resolve paper families and study identities

## Purpose

Group preprint/article/correction/supplement and linked dataset records into explicit paper families and study identities while preserving conflicts, uncertain matches, and split-boundary constraints.

## Preconditions

T028 and T029 are DONE. The candidate registry, expansion edge registry, source policy decisions, and saturation report are available. The lockbox interval remains excluded.

## Non-goals

This task will not force ambiguous merges, infer scientific validity from identity similarity, access locked payloads, or download repository code.

## Interfaces and invariants

Every family member retains its source/accession, DOI/URL aliases, relationship type, evidence hash, and match rationale. Conflicting identifiers remain visible as review conflicts. A family cannot cross a declared train/validation split in the fixture contract. Uncertain links enter a manual-review queue rather than being silently merged.

## Implementation plan

1. Define normalized identity and paper-family schemas with typed relationships.
2. Implement deterministic DOI, PMID, accession, title, and author-year normalization.
3. Add fixture-backed family resolution for article, preprint, correction, supplement, and dataset links.
4. Preserve unresolved conflicts and emit a manual-review queue.
5. Add CLI command biointerfaceos resolve paper-families and focused tests.
6. Run the full gate suite, validate ledgers, and record completion evidence.

## Progress

- [x] Define family and study-identity schemas.
- [x] Implement fixture-backed family resolution and conflict queue.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos resolve paper-families
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check
- family fixture split-boundary and conflict assertions
- append-only ledger validation

## Completion note

T030 completed with implementation commit 7a29773. The resolver emitted five split-safe families, ten member rows, and two sealed manual-review records without forcing cross-split or uncertain links. Completion evidence is recorded in reports/T030_paper_families.md.

## Failure recovery

Preserve source, candidate, and expansion ledgers. Repair only derived family outputs or normalization code; never rewrite prior provenance records or force a disputed merge.

## Outputs

paper_families.parquet, study/lab identity keys, deduplication report, manual-review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
