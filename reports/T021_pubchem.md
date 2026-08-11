# T021 PubChem PUG-REST Adapter Evidence

## Result

T021 is complete on the KAUST Ibex server. The repository now contains an anonymous PubChem PUG-REST adapter with deterministic CID/name resolution, explicit ambiguity and no-hit outcomes, selected structure descriptors, response-hash provenance, atomic local JSON caching, and a minimum 0.2-second request interval. T022 is now current; T023 through T025 remain dependency-ready.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 94 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_pubchem.py: exit 0; 5 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- biointerfaceos catalog check: CATALOG_VALID.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- Name queries use the official PubChem PUG-REST compound/name/cids endpoint; direct CID queries bypass name resolution.
- Property metadata uses a canonical property table URL for canonical/isomeric SMILES, InChI, InChIKey, formula, and molecular weight.
- Name resolution returns all bounded CIDs, preserving ambiguous and unresolved outcomes rather than collapsing them.
- Raw JSON responses are cached under data/cache/pubchem with atomic writes and response SHA-256; cache hits avoid transport.
- Anonymous requests use the fixed project User-Agent and a minimum 0.2-second interval, matching the documented five-requests-per-second ceiling.
- Sanitized fixtures cover unique, ambiguous, missing, and property responses plus cache and fake-clock tests.
- No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/pubchem.py
- tests/sources/test_pubchem.py
- tests/fixtures/sources/pubchem
- docs/execplans/T021_pubchem.md
- reports/T021_pubchem.md
- TASKS.tsv and PROJECT_STATE.yaml
- T021 sequence-16 record in reports/task_ledger.jsonl

## Commits

- cefc3fbd69ab3f82ec9b0d9f7850c33d4c668ee9 ? T021 adapter, cache, fixtures, and tests.
- The completion evidence commit follows this report and ledger update.
