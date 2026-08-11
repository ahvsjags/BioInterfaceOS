# T041: Implement material and formulation entity resolution

## Purpose

Resolve material strings and structures into provenance-grounded material entities and formulation graphs, covering lipids, polymers, ligands, core/coating relationships, mixture fractions, and alias candidates without forcing ambiguous trade names.

## Preconditions

T021, T022, and T039 are DONE. Material names, structure identifiers, formulation text, and evidence locators are available.

## Non-goals

This task will not silently map ambiguous trade names, invent structures, or normalize mixture fractions without a declared basis. Unresolved entities retain candidate sets and provenance.

## Interfaces and invariants

Every material entity retains raw mention, canonical label/structure when available, role, source locator, resolution method, confidence, and candidate aliases. Formulation graphs retain core/coating/ligand edges and validated fractions summing to one when a complete basis is reported. Ambiguities remain unresolved.

## Implementation plan

1. Define material entity, alias candidate, formulation edge, fraction, and review schemas.
2. Build fixtures for lipids, polymers, ligands, core/coating pairs, mixtures, and ambiguous trade names.
3. Implement deterministic alias/structure resolution using the committed source adapters and evidence locators.
4. Build formulation graphs with role constraints and fraction-sum validation.
5. Quarantine unresolved trade names, missing structures, and invalid fraction bases.
6. Add biointerfaceos resolve materials --fixture, focused tests, and full acceptance gates.

## Progress

- [ ] Define material/formulation entity and graph schemas.
- [ ] Implement alias resolution and role-aware formulation graphs.
- [ ] Preserve ambiguity and validate mixture fractions.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos resolve materials --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- alias, structure, role, fraction, provenance, and ambiguity assertions

## Failure recovery

Preserve raw mentions and all candidate mappings. Keep unresolved entities with candidate sets and route invalid mixture fractions to review.

## Outputs

material entity registry, formulation graphs, alias/review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.
