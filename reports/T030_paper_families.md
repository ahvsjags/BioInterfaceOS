# T030 Paper Family and Study Identity Evidence

## Result

T030 is complete on the KAUST Ibex server. The fixture-backed resolver grouped linked article, preprint, correction, supplement, dataset, and duplicate records while preserving uncertain and cross-split conflicts:

- resolved families: 5
- resolved member rows: 10
- manual-review records: 2
- split-safe families: true
- family output: registry/paper_families.parquet

FAMILY-001 contains the six train-split article-family members, including preprint, correction, supplement, dataset, and PMC duplicate relationships. The train article and validation record sharing the same DOI were not merged; they remain separate families and produce a SPLIT_BOUNDARY_CONFLICT review item. An uncertain possible-duplicate pair remains a separate UNCERTAIN_RELATIONSHIP review item.

Each Parquet member row preserves source/accession, DOI and normalized DOI, title and normalized title, year, split, relationship, stable record hash, study key, and lab key. The review queue is append-only and sealed.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 133 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_family_resolution.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos resolve paper-families: families=5 member_rows=10 manual_review=2 split_safe=True.
- .venv/bin/biointerfaceos search validate-queries and search saturation: passed.
- .venv/bin/biointerfaceos source policy self-test: passed.
- .venv/bin/biointerfaceos lockbox self-test: passed.
- .venv/bin/biointerfaceos release verify --fixture: passed.
- .venv/bin/biointerfaceos catalog check: passed.
- .venv/bin/biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Nine append-only ledgers validate, including the family manual-review queue.
- Parquet schema, five-family count, ten-member count, two review reasons, and split-boundary assertions: passed.
- Re-running the resolver does not append duplicate review records.

## Limitations

- The resolver is fixture-backed and does not represent live provider identity quality.
- Identity evidence is metadata-level; it does not establish scientific equivalence.
- Cross-split and uncertain links remain manual review and are not forced into a family.
- No live endpoints, binary assets, repository code, credentials, or locked-test payloads were accessed.
- T031 owns policy-gated asset downloading.

## Artifacts

- registry/paper_families.parquet
- registry/family_manual_review.jsonl and sealed snapshot
- tests/fixtures/families/paper_family_records.json
- src/biointerfaceos/family_resolution.py
- tests/test_family_resolution.py
- src/biointerfaceos/cli.py
- reports/paper_family_dedup.md
- docs/execplans/T030_paper_families.md
- reports/T030_paper_families.md
- TASKS.tsv and PROJECT_STATE.yaml
- T030 sequence-26 record in reports/task_ledger.jsonl

## Commits

- 7a29773: split-safe family resolver, Parquet output, sealed manual-review queue, fixture, tests, CLI, and test-isolation repair.
- The completion evidence commit follows this report, plan, ledger, and state update.
