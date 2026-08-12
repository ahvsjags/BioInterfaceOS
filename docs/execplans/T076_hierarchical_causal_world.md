# T076 Fit hierarchical causal world model

## Purpose

Implement an estimand-first M6 causal-world-model audit over the validated paired/modal/trajectory fixtures. The workflow must preregister the DAG and estimands, assess overlap and confounding sensitivity across alternative DAGs, and automatically prohibit causal wording when gates fail.

## Preconditions

T073 associational mediator, T074 compositions, T075 constrained trajectories, and T063 group keys are valid. Causal claims require explicit identification gates; otherwise retain predictive/associational outputs only.

## Non-goals

This task will not manufacture randomization, treat observational module links as interventions, access locked test data, or allow causal language after a failed gate.

## Interfaces and invariants

`biointerfaceos train m6 --config configs/models/m6.yaml` emits a preregistered DAG/estimand card, overlap/confounding sensitivity, alternative-DAG audit, posterior/predictive summaries, and an automated language policy. Failed identification gates set `causal_claim_permitted=false` and downgrade labels to associational/predictive.

## Implementation plan

1. Define M6 config, DAG card, estimands, and language policy.
2. Build paired observational design matrices with group-aware overlap and positivity checks.
3. Fit a bounded hierarchical predictive estimand model and run alternative DAG/confounding sensitivity.
4. Emit posterior-style intervals, overlap audit, sensitivity results, and automatic wording downgrade.
5. Add CLI, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos train m6 --config configs/models/m6.yaml`
- DAG/estimand preregistration, overlap, sensitivity, alternative DAG, and language policy assertions
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If overlap, confounding, or DAG consistency fails, retain predictive mediator estimates, mark causal estimands nonidentified, and prohibit causal wording automatically. Never override the language gate manually.

## Outputs

Versioned M6 config, DAG/estimand card, overlap/sensitivity/alternative-DAG audits, predictive summaries, language policy, focused tests, evidence report, and state/ledger advancement.
