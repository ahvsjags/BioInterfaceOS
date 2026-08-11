# T021: Implement PubChem PUG-REST adapter

## Purpose

Provide a credential-free PubChem PUG-REST adapter with deterministic CID/name resolution, ambiguity preservation, structure identifiers, selected descriptors, local response caching, and bounded rate behavior.

## Preconditions

T016 is DONE, T021 is READY/current, the source adapter contract, policy engine, and allowlisted network client are available, and no locked-test payload needs to be accessed.

## Non-goals

This task does not invent name-to-CID mappings, collapse ambiguous compounds into one record, send high-frequency single requests, or download bulk archives during metadata discovery.

## Interfaces and invariants

Use the official PubChem PUG-REST base under pubchem.ncbi.nlm.nih.gov/rest/pug. Preserve CID, canonical/isomeric SMILES, InChI, InChIKey, molecular formula/weight, query term, response hash, and evidence URL. Cache canonical JSON responses atomically and enforce a bounded request interval. Unresolved or ambiguous names remain explicit outcomes.

## Implementation plan

1. Define canonical PUG-REST property and name-resolution URLs with bounded query settings.
2. Implement a byte-stable local cache with response hashes and no credential headers.
3. Add fixtures for a unique CID, an ambiguous name, a missing name, and selected compound properties.
4. Add rate-interval tests with a fake clock and verify cache hits avoid transport.
5. Run offline lock/sync, focused/full tests, compileall, state, lockbox, release, catalog, and diff checks.
6. Record append-only evidence, advance the task graph, and commit.

## Progress

- [ ] Read and pin the official PubChem PUG-REST endpoint contract.
- [ ] Implement and test the PubChem adapter.
- [ ] Run acceptance gates and record completion evidence.

## Validation

- uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_pubchem.py
- .venv/bin/python -m compileall -q src tests
- biointerfaceos lockbox self-test
- biointerfaceos release verify --fixture
- biointerfaceos catalog check
- biointerfaceos state validate
- git diff --check
- mock CID/name/property resolution, ambiguity, cache hit, response hash, and rate-interval assertions

## Failure recovery

If PUG-REST is transient or a name is ambiguous, retain the query and evidence response but leave CID/structure fields null; use local cache before retrying.

## Outputs

src/biointerfaceos/sources/pubchem.py, tests/sources/test_pubchem.py, tests/fixtures/sources/pubchem, this ExecPlan, reports/T021_pubchem.md, state advancement, and task-ledger evidence.
