# BioInterfaceOS — Codex Repository Instructions

## 1. Mission

Build **BioInterfaceOS**, an open-data, provenance-grounded AI-for-Science system for biomedical materials. The core scientific chain is:

`material physical identity → dynamic protein corona / biointerface → cellular or immune response → uptake, toxicity, coagulation, complement and biodistribution`.

The project must use only public data that can be accessed anonymously without application, registration, login, API key, data-use agreement or manual approval. Wet-lab experiments are outside scope.

## 2. Read order

Before modifying code, read in this order:

1. `AGENTS.md`
2. `GOAL.md`
3. `PLANS.md`
4. `PROJECT_STATE.yaml`
5. the active ExecPlan under `docs/execplans/`
6. files referenced by the active task in `TASKS.tsv`

Do not attempt to hold the entire project in conversational memory. Persist decisions and progress in repository files.

## 3. Autonomous execution rules

- Execute tasks in dependency order from `TASKS.tsv`.
- Work on one primary task at a time; independent download/indexing tasks may run concurrently.
- After every completed task: run its tests, update `PROJECT_STATE.yaml`, append to `reports/task_ledger.jsonl`, update the active ExecPlan, and create a focused git commit.
- Never mark a task complete because code exists. Mark it complete only when its declared artifacts and acceptance tests pass.
- Retry transient network or compute failures with bounded exponential backoff. After three materially different attempts, record the failure and continue with independent tasks.
- A source requiring login, registration, approval, credentials or payment is **REJECTED**, not a blocker. Record it in `registry/rejected_sources.parquet` and continue.
- Do not ask the user to solve routine package, path, download, parsing or modeling problems. Diagnose and implement a fallback.
- Do not delete raw data, overwrite a frozen release, rewrite git history, expose secrets, or modify files outside the project root.
- Never fabricate a human review, expert annotation, license, accession, experimental value, citation, test result or scientific conclusion.
- A value absent from evidence is `null`, never guessed.
- Preserve failed experiments and negative results.

## 4. Scientific integrity rules

- Every modeled numeric value must resolve to an evidence record with source identifier, exact location, raw string, normalized value, unit, extraction method and confidence.
- Do not use publication identity, journal, author, laboratory, file path, visual layout or accession as predictive features.
- Do not expose post-2024 locked-test content before model and analysis freeze.
- Do not interpret association as causation. Causal language requires the claim gate in `GOAL.md`.
- Do not optimize only an in-distribution validation score. Primary selection uses time, study, material-family and biological-environment OOD performance plus calibration.
- Do not claim exhaustive coverage of “the whole web.” Report reproducible search coverage and saturation diagnostics.
- `gold_expert` status requires a real signed review record. Codex may prepare review packets but may not self-assign that status.

## 5. Engineering standards

- Python 3.11 is the default runtime.
- Prefer small typed modules with explicit interfaces and deterministic behavior.
- Use `uv` when available; otherwise use a local virtual environment. Pin release dependencies.
- Required checks for changed Python code: `ruff check`, `ruff format --check`, `mypy`, `pytest` and relevant integration tests.
- Use Parquet for analytical tables, DuckDB for local queries, JSONL for append-only logs and YAML for human-maintained configuration.
- All network adapters need timeouts, rate limits, retry policy, checksums and mock-based tests.
- All stochastic experiments must record seeds, environment, git commit, data version and configuration hash.
- No notebook may be the sole implementation of a result. Move reusable logic into `src/biointerfaceos/` and test it.
- Generated reports must be reproducible from commands in `Makefile` or `justfile`.

## 6. Required state files

Keep these current:

- `PROJECT_STATE.yaml`: task status and active release state.
- `reports/task_ledger.jsonl`: append-only execution history.
- `reports/DECISIONS.md`: architectural and scientific decisions.
- `reports/BLOCKERS.md`: only genuine external blockers; rejected credentialed sources do not belong here.
- `registry/SOURCE_MANIFEST.parquet`: all admitted and rejected source assets.
- `registry/CLAIM_LEDGER.parquet`: candidate claims and gate results.
- `registry/EXPERIMENT_LEDGER.parquet`: every run, including failed runs.

## 7. Definition of done

The project is not complete until all mandatory gates in `GOAL.md` pass, the locked evaluation is executed once after freeze, the release can be reproduced in a clean environment, and every manuscript claim is linked to evidence and executable analysis.
