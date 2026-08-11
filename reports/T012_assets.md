# T012 Content-Addressed Asset Store Evidence

## Result

T012 is complete on the KAUST Ibex server. Admitted assets can now be staged, SHA-256 verified, atomically promoted into a two-level CAS, indexed with provenance, and verified without accessing locked-test data. Identical bytes reuse one physical blob. Hash-mismatched bytes are preserved under data/quarantine and never promoted. T013 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15 without real source download:

- uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 14 packages checked.
- UV_OFFLINE=1 make check: exit 0; 53 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/assets: exit 0; 6 tests passed.
- biointerfaceos assets verify: ASSETS_VALID references=0 blobs=0 bytes=0.
- biointerfaceos source manifest validate: SOURCE_MANIFEST_VALID rows=0 unique_content_hashes=0 admitted=0 rejected=0 quarantined=0.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- AssetStore uses data/cas/sha256/<prefix>/<digest> and registry/ASSET_INDEX.parquet.
- Ingestion requires an admitted source-manifest record with matching non-null SHA-256 and size.
- Bytes are fsynced in staging and promoted with atomic replace only after digest verification.
- Repeated identical ingestion returns the existing reference and stores one physical blob.
- Wrong bytes are moved to data/quarantine as hash-mismatch partial evidence; no CAS blob or index row is created.
- Verification checks fixed index columns, canonical paths, file hashes/sizes, orphan CAS files, and source-manifest provenance.
- Repository and data/locked_test containment is enforced.

## Artifacts

- src/biointerfaceos/assets.py
- tests/assets/test_store.py
- registry/ASSET_INDEX.parquet
- data/cas/README.md
- data/quarantine/README.md
- src/biointerfaceos/cli.py
- docs/execplans/T012_asset_store.md
- reports/T012_assets.md
- TASKS.tsv and PROJECT_STATE.yaml
- T012 sequence-7 record in reports/task_ledger.jsonl

## Commits

- 4811f550a492ec434413b361370faea11066a579 ? T012 CAS implementation, Parquet index, CLI, tests, and namespaces.
- The completion evidence commit follows this report and ledger update.
