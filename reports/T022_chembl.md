# T022 ChEMBL Web Services Adapter Evidence

## Result

T022 is complete on the KAUST Ibex server. The repository now contains an anonymous ChEMBL molecule adapter using the official JSON molecule/status services, bounded page_meta pagination, explicit structure nulls, ChEMBL DB/API version capture, duplicate parent/salt preservation, and response hashes. T023 is now current; T024 and T025 remain dependency-ready.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 98 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/sources/test_chembl.py: exit 0; 4 tests passed.
- biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- biointerfaceos catalog check: CATALOG_VALID.
- biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Implemented behavior

- Molecule ID queries use the official ChEMBL molecule endpoint; preferred-name queries follow page_meta.next with a bounded page count.
- Molecule metadata preserves ChEMBL ID, preferred name, parent relation, canonical/isomeric structure fields, InChI/InChIKey, selected properties, max phase, and ChEMBL DB/API versions.
- Parent and salt records remain separate candidate IDs; duplicate IDs repeated across pages are de-duplicated without collapsing distinct salts.
- Missing molecule structures remain null rather than being substituted with unrelated fields.
- Response and status hashes are captured for reproducibility.
- Sanitized fixtures cover two pages, a parent/salt pair, a duplicate cross-page record, a missing-structure molecule, and version metadata.
- No live endpoint, credential, scientific asset, or locked-test payload was accessed.

## Artifacts

- src/biointerfaceos/sources/chembl.py
- tests/sources/test_chembl.py
- tests/fixtures/sources/chembl
- docs/execplans/T022_chembl.md
- reports/T022_chembl.md
- TASKS.tsv and PROJECT_STATE.yaml
- T022 sequence-17 record in reports/task_ledger.jsonl

## Commits

- 7d80261e3aee08203cb34f06366f565e95402640 ? T022 adapter, fixtures, and tests.
- The completion evidence commit follows this report and ledger update.
