# T023: Implement protein/pathway/cell-line ontology adapters

## Purpose

Provide versioned, anonymous ontology adapters for protein identifiers, pathways, species, and cell lines with explicit mappings, obsolete-ID tracking, licenses, and ambiguity preservation.

## Preconditions

T016 is DONE, T023 is READY/current, the source adapter contract, policy engine, and allowlisted network client are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not infer mappings from names alone, silently replace obsolete identifiers, or combine ontology releases without recording source/version evidence.

## Interfaces and invariants

Use official public resources and stable identifiers: UniProt, Gene Ontology, Reactome, NCBI Taxonomy, and Cellosaurus. Each mapping preserves source, identifier, label, version/date, license signal, evidence URL, obsolete/replaced-by state, and response hash. Ambiguous name matches remain multiple candidates or unresolved.

## Implementation plan

1. Define deterministic endpoint templates and version metadata for each ontology source.
2. Implement typed mapping records and source-specific adapters with a common query interface.
3. Add sanitized fixtures for valid protein/pathway/species/cell-line mappings, obsolete IDs, ambiguous labels, and a missing identifier.
4. Add dry-run snapshot registry output with version/date/license and byte-stable fixture assertions.
5. Run offline lock/sync, focused/full tests, compileall, state, lockbox, release, catalog, and diff checks.
6. Record append-only evidence, advance the task graph, and commit.

## Progress

- [ ] Read and pin official ontology endpoint contracts.
- [ ] Implement and test the ontology adapters.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/ontology
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- mock valid/obsolete/ambiguous/missing ontology mappings and versioned dry-run assertions

## Failure recovery

If a source endpoint is transient, retain the last verified versioned local snapshot and mark refresh unavailable; never promote an unverified replacement.

## Outputs

src/biointerfaceos/sources/ontology.py, tests/sources/test_ontology.py, tests/fixtures/sources/ontology, this ExecPlan, reports/T023_ontology.md, state advancement, and task-ledger evidence.
