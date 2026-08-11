# T026 Versioned Search Matrix Evidence

## Result

T026 is complete on the KAUST Ibex server. configs/search_queries.yaml is a versioned, byte-hashed discovery matrix with 22 deterministic query definitions spanning seven required axes, nine approved source types, and train/validation scopes. The validator enforces exact schema fields, source/axis/cursor allowlists, duplicate detection, ISO date ranges, the 2025-01-01 lockbox firewall, and fixed 2023/2024 scope boundaries.

The accepted matrix receipt is:

- matrix_version: 2026.08.12-dev.1
- queries: 22
- axes: material, corona, endpoint, protocol, species, assay, data_code
- sources: europe_pmc, pmc_oa, pride, geo, pubchem, chembl, zenodo, figshare, osf
- scopes: train, validation
- sha256: 70c767c0d38cf3a87a196bfa8dc107d8110630264d034ae4a745a5820491800d

No discovery search was run and no lockbox content was accessed in T026.

## Date firewall

- train: 2000-01-01 through 2023-12-31
- validation: 2024-01-01 through 2024-12-31
- lockbox: 2025-01-01 through 2026-08-11, forbidden to the development search matrix

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 121 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_search_matrix.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos search validate-queries: SEARCH_QUERIES_VALID queries=22 axes=7 sources=9 scopes=train,validation with the SHA-256 above.
- .venv/bin/biointerfaceos source policy self-test: SOURCE_POLICY_VALID fixtures=10 rejected_or_quarantined=7 registry_rows=7.
- .venv/bin/biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- .venv/bin/biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- .venv/bin/biointerfaceos catalog check: CATALOG_VALID.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validate, including task-ledger chain and seals.

## Implemented behavior

- Europe PMC/PMC OA queries cover frozen material families, corona/protein terms, endpoints, protocols, species/biofluids, assays, and data/code discovery.
- PRIDE, GEO/SRA, Zenodo, Figshare, OSF, PubChem and ChEMBL entries use provider-appropriate cursor strategies or explicit accession seeds.
- Training and validation date ranges are explicit on every row; no query can overlap the locked interval.
- Duplicate semantic definitions are rejected even when their IDs differ.
- The matrix requires all seven axes and both scopes, and its exact serialized bytes produce a reproducible hash.
- The CLI validates the checked-in matrix without contacting any source.

## Limitations

- T026 creates the query plan but does not execute searches; T027 owns retrieval, cursors, hit registries and saturation receipts.
- GEO/SRA uses accession seeds because the current adapter intentionally avoids broad server-side scraping.
- Query syntax is validated structurally and by source/cursor allowlists; endpoint-level live semantics will be checked during T027 fixture and bounded-run work.
- No lockbox title, abstract, figure, supplement, or associated data was accessed.

## Artifacts

- configs/search_queries.yaml
- src/biointerfaceos/search_matrix.py
- tests/fixtures/search_queries
- tests/test_search_matrix.py
- src/biointerfaceos/cli.py
- tests/test_cli.py
- docs/execplans/T026_query_matrix.md
- reports/T026_query_matrix.md
- TASKS.tsv and PROJECT_STATE.yaml
- T026 sequence-21 record in reports/task_ledger.jsonl

## Commits

- 2fadbfe3e669c6abd83813e155b653ac1ecf202a: query matrix, validator, fixtures, tests, and CLI.
- The completion evidence commit follows this report and ledger update.
