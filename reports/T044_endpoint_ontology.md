# T044 Endpoint and Measurement Ontology Evidence

## Result

T044 is complete on the KAUST Ibex server. Endpoint measurements are normalized with family, assay, basis, and time-aware strata:

- endpoints: 9
- normalized: 8
- endpoint families: 7
- strata: 7
- harmonized compatible strata: 1
- review-queue rows: 1

Uptake replicates with the same assay, basis, and timepoint harmonize to a mean fraction of 0.45. Viability remains separate because its basis is % control. Coagulation time converts 30 min to 1800 s. The delivery endpoint without a timepoint remains REVIEW_REQUIRED and is not assigned a stratum.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 178 tests passed; ruff, format, and mypy passed.
- biointerfaceos resolve endpoints --fixture: exit 0; endpoints=9 normalized=8 families=7 strata=7 harmonized_strata=1 review_items=1.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Nineteen append-only ledgers validate, including task, search, expansion, family-review, download, extraction review, consensus, evidence, unit, material, protein, protocol, and endpoint ledgers.
- Endpoint-family, assay/basis/time stratum, compatible harmonization, incompatible-basis separation, missing-time review, and review-queue idempotency assertions passed.

## Limitations

- Endpoint mappings are fixture-backed and use a bounded family/basis vocabulary.
- Cross-basis effects are intentionally not harmonized.
- Missing timepoints remain review-only.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/endpoint_resolution.py
- tests/endpoints/test_resolution.py
- tests/fixtures/endpoints/endpoint_resolution.json
- registry/endpoint_entities.json
- registry/endpoint_strata.json
- registry/endpoint_review_queue.jsonl and its seal/snapshot
- reports/endpoint_resolution.md
- docs/execplans/T044_endpoint_ontology.md
- TASKS.tsv and PROJECT_STATE.yaml
- T044 sequence-40 record in reports/task_ledger.jsonl

## Commit

- 353fbc0: normalize endpoint measurement strata.
