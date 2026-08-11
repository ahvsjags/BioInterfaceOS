# T042: Implement protein identifier and orthology resolution

## Purpose

Resolve species-specific protein names and accessions into stable protein entities, gene maps, isoforms, obsolete identifiers, and orthology groups while preserving mapping confidence and one-to-many relationships.

## Preconditions

T023 and T039 are DONE. Ontology/source adapters and exact evidence locators are available.

## Non-goals

This task will not map proteins across species by name alone, collapse isoforms without evidence, or discard obsolete/ambiguous accessions.

## Interfaces and invariants

Every protein entity retains species, raw identifier/name, canonical accession when resolved, gene identifier, isoform status, source locator, resolution method, and confidence. Orthology groups preserve species-specific members and one-to-many edges. Obsolete identifiers and ambiguous names enter review.

## Implementation plan

1. Define protein entity, accession mapping, isoform, orthology group, edge, and review schemas.
2. Build fixtures for species-specific accessions, gene names, isoforms, obsolete IDs, and one-to-many orthology.
3. Implement deterministic species-aware accession/name resolution.
4. Preserve obsolete mappings and one-to-many orthology without collapsing members.
5. Quarantine cross-species name-only ambiguity and low-confidence mappings.
6. Add biointerfaceos resolve proteins --fixture, focused tests, and full acceptance gates.

## Progress

- [ ] Define protein and orthology schemas.
- [ ] Implement species-aware identifier mapping.
- [ ] Preserve isoform/obsolete ambiguity and one-to-many orthology.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos resolve proteins --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- species, accession, gene, isoform, obsolete, orthology, confidence, and ambiguity assertions

## Failure recovery

Preserve raw protein names/accessions and species. Keep ambiguous or obsolete mappings with candidate sets and do not collapse one-to-many orthology.

## Outputs

protein entity registry, accession/gene maps, orthology groups and edges, review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
