# T052: Triage PRIDE projects and freeze sample plans

## Purpose

Create auditable PRIDE project cards and sample maps for development-scope omics candidates, then decide which projects are eligible for later split construction without accessing locked projects or raw payloads.

## Preconditions

T019, T030, and T051 are complete. PRIDE search candidates, paper-family identities, coverage gaps, and missingness warnings are available.

## Non-goals

This task will not download raw proteomics files, infer sample assignments from ambiguous labels, or treat metadata-only projects as measured observations. Locked projects remain metadata-only.

## Interfaces and invariants

Every project card will preserve official project date, accession, file inventory, raw/search availability, material arms, biofluid, replicate counts, outcomes, evidence locators, and an explicit split decision. Ambiguous sample maps are rejected or parked for review; no pseudo-replicates are created.

## Implementation plan

1. Define a fixture-backed PRIDE project-card and sample-map schema.
2. Join PRIDE candidates to paper-family records without collapsing unresolved identities.
3. Validate project metadata, file availability, sample arms, biofluid, replicates, and outcomes.
4. Emit split-eligibility decisions and a review queue for unclear maps.
5. Add `biointerfaceos omics pride triage --scope development` and focused tests.
6. Run the full offline gate, immutable release checks, and append evidence.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics pride triage --scope development`
- `biointerfaceos assets verify`
- `biointerfaceos lockbox self-test`
- `biointerfaceos state validate`
- `git diff --check`
- project-card, sample-map, metadata-only, and no-raw-download assertions

## Failure recovery

Reject or park projects with unclear sample maps, preserve their metadata and evidence locators, and search additional public projects only through the existing source-policy gates.

## Outputs

PRIDE project cards, sample maps, split-eligibility manifest, review queue, focused tests, this ExecPlan, state advancement, and task-ledger evidence.

## Completion evidence

T052 completed on 2026-08-12 in `/ibex/user/xup0a/BioInterfaceOS`. The implementation commit is `e490394`. The development fixture yields 3 project cards: 1 split-eligible project with a balanced 3+3 sample map, 1 project parked for restricted RAW access and unresolved arms/replicates, and 1 locked metadata-only project. No raw file was downloaded and no locked payload was accessed.

The full offline gate passed with 200 tests, coverage and data-release checks, review export, assets, catalog, lockbox, immutable release verification, state validation, compileall, 23 append-only ledger validations, and `git diff --check`. The evidence record is sequence 48 in `reports/task_ledger.jsonl`; T053 is now the active task.
