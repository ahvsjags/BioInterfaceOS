# T029 Search Saturation and Coverage-Gap Evidence

## Result

T029 is complete on the KAUST Ibex server. The committed search and expansion ledgers were analyzed with a deterministic fixture-backed saturation runner:

- development search batches: 13
- raw search hits: 17
- unique candidates: 14
- policy-admitted candidates: 13
- quarantined candidates: 1
- raw expansion edges: 44
- unique expansion targets: 17
- policy-admitted expansion targets: 16
- open coverage gaps: 9
- gap query proposals: 8
- stopping decision: CONTINUE

Novel eligible-study yield is reported per batch and per axis in reports/search_saturation.html. The current evidence does not support a stopping claim: the 2024 validation scope has no receipts, several declared material and endpoint families are absent from the matrix vocabulary, and the diminishing-return thresholds have not been reached.

## Coverage gaps

The report identifies:

- year/scope gap: the frozen 2024 validation interval is defined but not executed;
- material gaps: polymeric, silica, gold, and protein-based families;
- endpoint gaps: biodistribution, hemolysis, and endosomal escape;
- provider gap: validation provider blocks have no validation receipts.

Each gap has a targeted query proposal. The gap detector audits material-axis and endpoint/assay-axis vocabulary separately, so a corona term does not silently satisfy material coverage.

## Saturation criteria

The declared stopping rule requires both at least two consecutive zero-yield batches and at least two consecutive low-yield batches below 0.1 novel-eligible/raw-hit ratio, complete validation execution, and no open coverage gaps. Observed maxima are one zero-yield batch and one low-yield batch; validation is incomplete and nine gaps remain. The reproducible decision is therefore CONTINUE.

## Acceptance evidence

All commands ran in /ibex/user/xup0a/BioInterfaceOS on CPython 3.11.15:

- UV_OFFLINE=1 uv lock --check: exit 0.
- UV_OFFLINE=1 uv sync --frozen --python 3.11: exit 0.
- UV_OFFLINE=1 make check: exit 0; 130 tests passed; ruff, format, and mypy passed.
- .venv/bin/pytest -q tests/test_saturation.py: exit 0; 3 tests passed.
- .venv/bin/biointerfaceos search validate-queries: matrix valid; 22 queries and 7 axes.
- .venv/bin/biointerfaceos search saturation: raw_hits=17 unique_candidates=14 raw_edges=44 unique_targets=17 open_gaps=9 decision=CONTINUE.
- .venv/bin/biointerfaceos source policy self-test: passed.
- .venv/bin/biointerfaceos lockbox self-test: passed.
- .venv/bin/biointerfaceos release verify --fixture: passed.
- .venv/bin/biointerfaceos catalog check: passed.
- .venv/bin/biointerfaceos state validate: passed.
- compileall and git diff --check: passed.
- Eight append-only ledgers validate.
- Deterministic assertions for 9 gaps, 8 proposals, and CONTINUE decision: passed.

## Limitations

- All metrics are derived from committed sanitized fixtures and do not represent live literature counts.
- Candidate records do not yet carry publication-year fields; the year finding is the absence of executed 2024 validation receipts, not a claim that no 2024 studies exist.
- Missing material and endpoint families are coverage proposals, not evidence that those studies do not exist.
- No live endpoint, binary asset, repository code, credential, or locked-test payload was accessed.
- T030 owns paper-family and study-identity resolution.

## Artifacts

- reports/search_saturation.html
- src/biointerfaceos/saturation.py
- tests/fixtures/search/saturation_expectations.json
- tests/test_saturation.py
- src/biointerfaceos/cli.py
- docs/execplans/T029_saturation.md
- reports/T029_search_saturation.md
- TASKS.tsv and PROJECT_STATE.yaml
- T029 sequence-25 record in reports/task_ledger.jsonl

## Commits

- 39e1e33: saturation analyzer, coverage-gap proposals, HTML report, fixture, tests, and CLI integration.
- The completion evidence commit follows this report, plan, ledger, and state update.
