# T042 Protein Identifier and Orthology Resolution Evidence

## Result

T042 is complete on the KAUST Ibex server. Species-aware protein mappings preserve accession, gene, isoform, obsolete, confidence, and orthology provenance:

- protein mentions: 5
- resolved: 3
- isoform/other ambiguous: 1
- obsolete review: 1
- orthology groups: 1
- one-to-many orthology edges: 2
- review-queue rows: 2

Human, mouse, and zebrafish TP53-like proteins resolve to species-specific accessions and gene IDs. The human isoform mention retains both candidate mappings. An obsolete accession retains its replacement accession and is not silently promoted. The orthology group retains all three species members and two explicit one-to-many edges.

## Quality gate

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 172 tests passed; ruff, format, and mypy passed.
- biointerfaceos resolve proteins --fixture: exit 0; mentions=5 resolved=3 ambiguous=1 obsolete_review=1 orthology_groups=1 orthology_edges=2 review_items=2.
- biointerfaceos assets verify: references=2 blobs=2 bytes=61.
- biointerfaceos lockbox self-test: passed.
- biointerfaceos catalog check: source_rows=4 asset_rows=2 rejection_rows=9 join_rows=2.
- biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290: passed.
- biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Seventeen append-only ledgers validate, including task, search, expansion, family-review, download, extraction review, consensus, evidence, unit, material, and protein-review ledgers.
- Species-specific accession/gene mapping, isoform ambiguity, obsolete replacement retention, orthology member multiplicity, confidence, and review-queue idempotency assertions passed.

## Limitations

- Protein resolution is fixture-backed and does not map across species by name alone.
- Isoform and obsolete mappings remain review states until corroborated.
- No live endpoints, binaries, credentials, repository code, locked-test payloads, or network data were accessed.

## Artifacts

- src/biointerfaceos/protein_resolution.py
- tests/proteins/test_resolution.py
- tests/fixtures/proteins/protein_resolution.json
- registry/protein_entities.json
- registry/orthology_groups.json
- registry/protein_review_queue.jsonl and its seal/snapshot
- reports/protein_resolution.md
- docs/execplans/T042_protein_orthology.md
- TASKS.tsv and PROJECT_STATE.yaml
- T042 sequence-38 record in reports/task_ledger.jsonl

## Commit

- f24eeab: resolve species proteins and orthology.
