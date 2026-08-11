# T041 Material and Formulation Entity Resolution Evidence

## Result

T041 is complete on the KAUST Ibex server. Material mentions and formulation components are resolved with role, alias, structure, fraction, and locator provenance:

- mentions: 4
- resolved entities: 3
- ambiguous mentions: 1
- formulations: 2
- valid formulations: 1
- formulation graph edges: 2
- review-queue rows: 2

DSPC, PEG 2000, and an RGD ligand resolve to curated entity candidates with material classes and structure IDs where available. NanoCoat-X remains ambiguous with both trade-name candidates retained. The valid formulation has core/coating/ligand roles and mass fractions summing to 1.0. The invalid formulation is retained with its raw components and routed to review.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 169 tests passed; ruff, format, and mypy passed.
- biointerfaceos resolve materials --fixture: exit 0; mentions=4 resolved_entities=3 ambiguous_mentions=1 formulations=2 valid_formulations=1 graph_edges=2 review_items=2.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Sixteen append-only ledgers validate, including task, search, expansion, family-review, download, extraction review, consensus, evidence, unit, and material-review ledgers.
- Alias/structure mapping, material-class, role, exact-locator, fraction-sum, core/coating/ligand graph, ambiguity retention, and review-queue idempotency assertions passed.

## Limitations

- Resolution is fixture-backed and uses committed curated candidates; no unverified trade-name structure is invented.
- Fraction validation requires a common declared basis and a sum of 1.0.
- Ambiguous mentions remain unresolved and are not used as canonical graph nodes.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/material_resolution.py
- tests/materials/test_resolution.py
- tests/fixtures/materials/material_resolution.json
- registry/material_entities.json
- registry/formulation_graphs.json
- registry/material_review_queue.jsonl and its seal/snapshot
- reports/material_resolution.md
- docs/execplans/T041_material_resolution.md
- TASKS.tsv and PROJECT_STATE.yaml
- T041 sequence-37 record in reports/task_ledger.jsonl

## Commit

- 9bf8cf6: resolve material entities and formulations.
