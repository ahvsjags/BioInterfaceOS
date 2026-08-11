# T023 Ontology Adapter Evidence

## Result

T023 is complete on the KAUST Ibex server. The repository now contains one policy-gated, anonymous metadata adapter covering UniProtKB, Gene Ontology/QuickGO, Reactome, NCBI Taxonomy, and Cellosaurus. It preserves stable identifiers, normalized labels/species, version/date fields, license signals, response SHA-256, obsolete/replaced-by state, and ambiguous label candidates. The adapter deliberately exposes no binary assets.

## Official endpoint contract

The implementation uses these public endpoint families:

- UniProtKB JSON: https://rest.uniprot.org/uniprotkb/{accession}.json
- QuickGO terms/search: https://www.ebi.ac.uk/QuickGO/services/ontology/go/
- Reactome ContentService: https://reactome.org/ContentService/data/query/{identifier}
- Cellosaurus API: https://api.cellosaurus.org/cell-line/{accession}?format=json
- NCBI Taxonomy E-utilities JSON: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=taxonomy&id={taxid}&retmode=json

All test traffic was intercepted by a fake opener. No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 105 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/sources/test_ontology.py: exit 0; 6 tests passed.
- .venv/bin/biointerfaceos ontology sync --dry-run: exit 0; five sources, five allowlisted hosts, network=false, binary_assets=0.
- .venv/bin/biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- .venv/bin/biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- .venv/bin/biointerfaceos catalog check: CATALOG_VALID.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validate, including task-ledger chain and seals.

## Implemented behavior

- Identifier queries resolve stable UniProt, GO, Reactome, Taxonomy, and Cellosaurus candidates through deterministic official URL templates.
- Metadata retains source identifier, label, organism/species, release/version/date, license signal, request URL, evidence location, raw normalized record, and response hash.
- Obsolete GO records preserve obsolete=true and replacement IDs instead of silently redirecting.
- Cellosaurus and GO label searches return bounded candidate sets without collapsing ambiguity; Taxonomy ESearch IDs remain explicit candidates.
- Missing record responses raise AdapterError; unknown sources, empty labels, malformed candidates, and zero/over-limit result settings are rejected.
- list_assets() is always empty and fetch() rejects binary access because this adapter is metadata-only.
- The CLI dry-run is network-free and makes the planned scope auditable.
- Sanitized fixtures cover all five sources, obsolete/replaced-by mappings, ambiguous HeLa matches, Taxonomy label resolution, missing records, and response hashing.

## Limitations

- The fixtures are sanitized JSON responses; live availability and release refresh are not asserted in CI.
- License values are preserved as source signals. NCBI Taxonomy uses a PUBLIC-DOMAIN signal with a submitter-specific restriction caveat; the adapter does not ingest submitted sequence assets.
- The task stores version/date metadata but does not yet materialize a large local ontology snapshot; later discovery/extraction tasks must pin a snapshot receipt before using mappings.
- Locked-test payloads were not accessed.

## Artifacts

- src/biointerfaceos/sources/ontology.py
- tests/sources/test_ontology.py
- tests/fixtures/sources/ontology
- src/biointerfaceos/cli.py
- tests/test_cli.py
- docs/execplans/T023_ontology.md
- reports/T023_ontology.md
- TASKS.tsv and PROJECT_STATE.yaml
- T023 sequence-18 record in reports/task_ledger.jsonl

## Commits

- 75677d58dbb6e301eb15f78ecd0b155dbfd99121: common ontology adapter, four-source fixtures, and focused tests.
- 11cb70a96614f252aa95f3aa49dba0382002883: ontology dry-run CLI and test.
- 73ccbf0d51ddd1e94634188b4121444fc5d208bd: NCBI Taxonomy mapping and tests.
- The completion evidence commit follows this report and ledger update.
