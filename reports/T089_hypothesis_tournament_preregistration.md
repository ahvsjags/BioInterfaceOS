# T089 Hypothesis tournament and preregistration evidence

Date: 2026-08-12  
Task: Freeze hypothesis tournament and preregistration rules  
Implementation commit: `3706aeb` (`feat: add hypothesis tournament preregistration`)

## Scope

The tournament consumes only T084 exploratory proposals, T085 preregistration metadata, and frozen development split metadata. It freezes K, weights, primary outcome, direction, minimum effect, exclusion rules, and falsifiability tests before ranking. Normalized duplicates are excluded, lockbox contamination is scanned, and ranked items remain exploratory with no automatic claim acceptance.

## Acceptance results

Command:

```text
biointerfaceos claim preregister --dev
```

Observed stable run:

```text
CLAIM_PREREGISTER_VALID candidates=3 ranked=2 duplicates_removed=1 exclusions=1 config_frozen=true lockbox_clean=true claims_auto_accepted=false selected_pipeline=preregistered_tournament resumed=1
```

Three training-only candidate records produced two ranked exploratory hypotheses after one normalized duplicate was removed. The preregistration hash receipt captures configuration and ranking hashes, the lockbox scan is clean, and neither ranked hypothesis is marked as an accepted claim.

## Determinism and artifacts

Outputs:

- `agents/claims/tournament.v1.json`
- `tests/fixtures/agents/tournament_fixture.json`
- `reports/claims/tournament/tournament_config.json`
- `reports/claims/tournament/hypothesis_ranking.json`
- `reports/claims/tournament/exclusion_ledger.json`
- `reports/claims/tournament/lockbox_scan.json`
- `reports/claims/tournament/tournament_comparison.json`
- `reports/claims/tournament/preregistration_hash_receipt.json`
- `reports/claims/tournament/preregistration_receipt.json`
- `reports/claims/tournament/tournament_manifest.json`
- `tests/agents/test_hypothesis_tournament_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 310 passed; ruff, format, and mypy passed.
- `biointerfaceos claim preregister --dev`: passed with resumable output.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked; tournament scan was clean.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, credential request, or locked test payload was used.

## Handoff

T089 is complete. T090 is next: discover stable protein-corona functional axes with alternative decompositions, bootstrap/leave-study stability, random-module controls, and uncertainty.
