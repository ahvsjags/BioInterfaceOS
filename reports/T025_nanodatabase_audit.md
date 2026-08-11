# T025 Specialized Nanodatabase Admission Evidence

## Result

T025 is complete on the KAUST Ibex server. Six auditable candidate groups were assessed against anonymous access, official API/export evidence, license clarity, schema relevance, and provenance requirements:

- 2 ADMIT_PUBLIC_SUBSTITUTE: PubChem/ChEMBL and public Zenodo/Figshare/OSF release mirrors.
- 2 METADATA_ONLY: eNanoMapper and nanoPharos, pending per-record license and reproducible endpoint verification.
- 1 QUARANTINE: NBI Knowledgebase, because the audited public material does not establish a stable API/export and redistribution contract.
- 1 REJECT: NanoCommons KB, because the audited manual describes authenticated partner-restricted access.

The complete decision envelope is in tests/fixtures/nanodatabases/admission_decisions.json and the human-readable report is reports/NANODATABASE_ADMISSION.md.

## Evidence basis

The audit used official project/provider material:

- NanoCommons KB and access model: https://nanocommons.github.io/user-handbook/data-management/data-resources/NanoCommons-KB/ and https://nanocommons.github.io/user-handbook/data-management/data-resources/NanoCommons-KB-manual/
- eNanoMapper public data/API: https://www.enanomapper.net/data and https://www.enanomapper.net/documentation
- NBI Knowledgebase: https://nbi.nacse.org/
- nanoPharos: https://nanocommons.github.io/user-handbook/data-management/data-resources/NanoPharos/ and https://db.nanopharos.eu/
- PubChem PUG REST: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- ChEMBL Web Services: https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services
- Zenodo, Figshare, OSF public APIs: https://developers.zenodo.org/, https://docs.figshare.com/, https://developer.osf.io/

The audit did not request credentials, download specialized database payloads, or queue a restricted source for ingest. Browser research was used only to inspect public documentation; repository tests remain offline.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 117 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_nanodatabase_audit.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos source audit-specialized: NANODATABASE_AUDIT_VALID candidates=6 admitted_substitutes=2 metadata_only=2 quarantined=1 rejected=1.
- .venv/bin/biointerfaceos source policy self-test: SOURCE_POLICY_VALID fixtures=10 rejected_or_quarantined=7 registry_rows=7.
- .venv/bin/biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- .venv/bin/biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- .venv/bin/biointerfaceos catalog check: CATALOG_VALID.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validate, including task-ledger chain and seals.

## Decision invariants

- Every candidate has an official URL, evidence URL list, access classification, API/export assessment, license signal, schema relevance, policy status, decision code, and next step.
- Unsupported or record-level-unclear licenses are never promoted to public binary ingest.
- Scientific relevance does not override access or redistribution policy.
- PubChem/ChEMBL are explicitly substitutes for chemical identity/structure fields, not replacements for protein corona, protocol, or endpoint data.
- DOI/release mirrors are preferred for supplementary files because the T024 adapter captures release, license, and checksum evidence.

## Limitations

- This is an admission audit, not a claim of database completeness or long-term availability.
- Dynamic sites and API behavior require later fixture-based verification before direct adapters are queued.
- The decision is at candidate-group level; a future data ingest must re-evaluate each record's license and access fields.
- No private/credentialed source was accessed and no locked-test payload was accessed.

## Artifacts

- reports/NANODATABASE_ADMISSION.md
- tests/fixtures/nanodatabases/admission_decisions.json
- tests/test_nanodatabase_audit.py
- src/biointerfaceos/nanodatabase_audit.py
- src/biointerfaceos/cli.py
- docs/execplans/T025_nanodatabase_audit.md
- reports/T025_nanodatabase_audit.md
- TASKS.tsv and PROJECT_STATE.yaml
- T025 sequence-20 record in reports/task_ledger.jsonl

## Commits

- d7d5d3f8a5e5df4bf582c377985b78cab8d138bf: audit schema, sanitized decisions, validation tests, CLI, and admission report.
- The completion evidence commit follows this report and ledger update.
