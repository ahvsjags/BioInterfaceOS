# T028: Expand citations, datasets, supplementary links and code

## Purpose

Expand the T027 seed registry through public metadata citation links, dataset links, supplements, and code/repository pointers while preserving provenance and paper-family candidates.

## Preconditions

T027 and T024 are DONE. The seed registry, repository adapter, public article/source adapters, policy engine, and matrix receipt are available.

## Non-goals

This task will not download binaries, merge uncertain paper families, inspect lockbox content, or treat a citation/link as evidence of scientific validity without a source record.

## Interfaces and invariants

Every expansion edge records parent candidate, edge type, target source/accession/URL, discovery query/run, timestamp, response hash, access/license decision, and depth. Duplicates collapse only by stable source accession or normalized DOI/URL; uncertain family links remain separate review candidates. Expansion depth is bounded at two and has a declared stopping rule.

## Implementation plan

1. Add citation and linked-resource graph schemas with typed edge provenance.
2. Implement fixture-backed forward/backward citation and dataset/supplement/code link expansion.
3. Normalize DOI/accession/URL aliases without merging incompatible records.
4. Apply source/license policy to every linked target and preserve metadata-only/quarantine outcomes.
5. Produce reports/EXPANSION_VALIDATION.md, candidate graph fixtures, and bounded expansion receipts.
6. Run full gates and record the deduplicated graph before saturation analysis.

## Progress

- [x] Define expansion graph and edge receipts.
- [x] Implement bounded fixture-backed expansion.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos search expand --depth 2 --scope development
- biointerfaceos state validate
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- git diff --check

## Completion note

T028 completed with implementation commit 5cfec88. The fixture-backed depth-two run produced 44 raw edges, 17 unique normalized targets, 16 policy admissions, and one quarantine. Completion evidence is recorded in reports/T028_expand_links.md.

## Failure recovery

Persist completed edges and response hashes; resume only failed branches. Do not rewrite seed records or delete inaccessible links.

## Outputs

Citation/dataset/code graph, expansion receipts, fixtures/tests, reports/EXPANSION_VALIDATION.md, this ExecPlan, state advancement, and task-ledger evidence.
