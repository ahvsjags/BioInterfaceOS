# T011 Source Policy Evidence

## Result

T011 is complete on the KAUST Ibex server. The project now applies a default-deny anonymous-access and license policy with explicit public redistribution, analysis-only, quarantine, and rejection outcomes. Rejected and quarantined candidates are preserved in registry/rejected_sources.parquet. T012 is now READY/current.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15 without real source access:

- uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0; 14 packages checked.
- UV_OFFLINE=1 make check: exit 0; 47 tests passed; ruff, format, and mypy passed.
- UV_OFFLINE=1 .venv/bin/pytest -q tests/test_policy.py: exit 0; 7 tests passed.
- .venv/bin/biointerfaceos source policy self-test: SOURCE_POLICY_VALID fixtures=10 rejected_or_quarantined=7 registry_rows=7.
- .venv/bin/biointerfaceos source manifest validate: SOURCE_MANIFEST_VALID rows=0 unique_content_hashes=0 admitted=0 rejected=0 quarantined=0.
- .venv/bin/biointerfaceos schema validate-all: exit 0; 9 schemas and fixtures valid.
- .venv/bin/biointerfaceos state validate: STATE_VALID tasks=115.
- .venv/bin/python -m compileall -q src tests: exit 0.
- git diff --check: exit 0.
- All four append-only ledgers validated, including task-ledger hash chain and seals.

## Policy coverage

- CC0 and CC-BY fixtures produce ADMIT_PUBLIC_REDISTRIBUTABLE.
- CC-BY-NC produces ADMIT_ANALYSIS_ONLY.
- Login, registration, API key, approval, and payment fixtures produce REJECT with REJECTED_CREDENTIALLED.
- Explicit All Rights Reserved produces REJECT with REJECTED_RESTRICTED_LICENSE.
- Unclear license text produces QUARANTINE with LICENSE_UNCLEAR.
- Candidate URLs with credentials and non-HTTP schemes are rejected.
- The engine never reads credential environment variables or contacts a network source.

## Artifacts

- configs/source_policy.yaml
- src/biointerfaceos/policy.py
- tests/test_policy.py
- tests/fixtures/policy
- registry/rejected_sources.parquet
- src/biointerfaceos/cli.py
- docs/execplans/T011_source_policy.md
- reports/T011_policy.md
- TASKS.tsv and PROJECT_STATE.yaml
- T011 sequence-6 record in reports/task_ledger.jsonl

## Commits

- a7dbcf41ece2811f1f5b915acaabf645ec5cbff7 ? T011 policy engine, fixtures, CLI, and rejection registry.
- The completion evidence commit follows this report and ledger update.
