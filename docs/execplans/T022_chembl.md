# T022: Implement ChEMBL Web Services adapter

## Purpose

Provide an anonymous ChEMBL adapter for molecule IDs, structures, selected public properties, duplicate-salt handling, pagination, and response provenance.

## Preconditions

T016 is DONE, T022 is READY/current, the source adapter contract, policy engine, and allowlisted network client are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not invent mappings across salts, silently collapse parent/child relationships, fetch proprietary assay data, or ignore ChEMBL API version fields.

## Interfaces and invariants

Use the official ChEMBL API under www.ebi.ac.uk/chembl/api/data. Preserve API version, molecule ID, canonical/isomeric SMILES, InChIKey, preferred name, max phase when present, query URL, pagination links, and response SHA-256. Duplicate salts remain separate records unless an explicit parent relation is supplied.

## Implementation plan

1. Define canonical molecule lookup/search URLs and bounded page-size pagination.
2. Implement typed molecule projection with explicit nulls for missing structures and response provenance.
3. Add fixtures for a molecule, a duplicate salt/parent pair, an ambiguous search page, and a next-page response.
4. Test pagination, version capture, duplicate preservation, and policy gates with a fake opener.
5. Run offline lock/sync, focused/full tests, compileall, state, lockbox, release, catalog, and diff checks.
6. Record append-only evidence, advance the task graph, and commit.

## Progress

- [ ] Read and pin the official ChEMBL API endpoint contract.
- [ ] Implement and test the ChEMBL adapter.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_chembl.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- mock molecule lookup, version capture, pagination, duplicate salt preservation, and null structure assertions

## Failure recovery

If the ChEMBL service is transient, retain the query and response evidence, preserve page cursors, and leave unavailable structure fields null.

## Outputs

src/biointerfaceos/sources/chembl.py, tests/sources/test_chembl.py, tests/fixtures/sources/chembl, this ExecPlan, reports/T022_chembl.md, state advancement, and task-ledger evidence.
