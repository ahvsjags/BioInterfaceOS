# T024 Public Repository Adapter Evidence

## Result

T024 is complete on the KAUST Ibex server. The repository now contains a common anonymous adapter for Zenodo, Figshare, OSF, and public GitHub releases. It preserves DOI or release identifier, title, version/date, commit or tag, license signal, response hashes, download URLs, asset IDs, sizes, and provider provenance. It never clones or executes repository code.

## Official endpoint contract

The implementation follows the public provider interfaces documented at:

- Zenodo REST API: https://developers.zenodo.org/
- Figshare API v2: https://docs.figshare.com/
- OSF API v2: https://developer.osf.io/
- GitHub REST releases API: https://docs.github.com/en/rest/releases/releases

All test traffic was intercepted by a fake opener. No provider endpoint, credential, repository payload, or locked-test payload was accessed.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 15 packages checked.
- UV_OFFLINE=1 make check: exit 0; 113 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/sources/test_repositories.py: exit 0; 7 tests passed.
- .venv/bin/biointerfaceos repository sync --dry-run: exit 0; four providers, four API hosts, network=false, binary_assets=0.
- .venv/bin/biointerfaceos lockbox self-test: LOCKBOX_VALID blocked_read=True field_detected=True hash_detected=True.
- .venv/bin/biointerfaceos release verify --fixture: RELEASE_VALID; 6 release input files verified.
- .venv/bin/biointerfaceos catalog check: CATALOG_VALID.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validate, including the task-ledger chain and seals.

## Implemented behavior

- Provider-qualified queries resolve direct releases: Zenodo record IDs/DOIs, Figshare article IDs, OSF node IDs, and GitHub owner/repository releases or tags.
- Zenodo bounded search follows pages and deduplicates repeated record IDs.
- Metadata retains DOI, title, version/date, commit/tag, license identifier/text, provider URL, response SHA-256, and raw normalized record.
- Release files retain provider asset IDs, stable download URLs, content type, size, optional SHA-256, and source linkage; duplicate URLs remain separate assets.
- Assets without a verifiable SHA-256 remain pointers and are rejected by fetch rather than downloaded without integrity evidence.
- The network client retries a transient 429 response without reading credentials; provider access remains anonymous.
- Missing or unsupported licenses are quarantined by the policy engine before metadata/assets access.
- The CLI dry-run is network-free and explicitly reports four providers and zero binary assets.
- No repository code is cloned, imported, or executed.

## Limitations

- The fixtures are sanitized provider JSON responses; live provider availability and API schema drift are not asserted in CI.
- GitHub release metadata obtains the license from the public repository metadata endpoint; a release with no repository license is retained only as a quarantined metadata pointer.
- OSF file listing follows the public JSON-API relationship URL; private or permissioned storage is not admitted.
- Provider-specific licenses outside the configured allowlist are conservatively quarantined rather than inferred.
- Locked-test payloads were not accessed.

## Artifacts

- src/biointerfaceos/sources/repositories.py
- tests/sources/test_repositories.py
- tests/fixtures/sources/repositories
- src/biointerfaceos/cli.py
- tests/test_cli.py
- docs/execplans/T024_repositories.md
- reports/T024_repositories.md
- TASKS.tsv and PROJECT_STATE.yaml
- T024 sequence-19 record in reports/task_ledger.jsonl

## Commits

- 4a438421d4de44fc68acf07e08cfa0e94b6ec2fc: common repository adapter, provider fixtures/tests, and dry-run CLI.
- The completion evidence commit follows this report and ledger update.
