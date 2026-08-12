# T091 Estimate material-corona-outcome mediation laws

## Objective

Implement a deterministic, fixture-backed mediation discovery workflow for the paired material/intervention → protein-corona functional-axis → outcome chain. The workflow must keep estimands, DAG assumptions, study clustering, alternative mediators, and replication status explicit. It must never convert an observational or nonidentified decomposition into a causal mediation claim.

## Scope and constraints

- Use the validated paired chain and the T090 functional-axis outputs without changing frozen splits or release assets.
- Preregister the estimands, mediator set, outcome, treatment/intervention contrast, study clusters, and language policy before calculating estimates.
- Compare the primary functional-axis mediator with at least one alternative mediator and a random/permuted mediator control.
- Report direct, indirect, total, and mediated-fraction estimates with study-clustered uncertainty and sensitivity to alternative DAGs.
- Attempt an independent development replication using a held-out study/fixture stratum; do not tune the primary result on that replication.
- Preserve adverse or nonidentified results. A failed overlap, temporal-order, confounding, or replication gate must produce an association-only result and block mediation language.
- Keep all execution offline and fixture-backed; no network, credential, raw download, locked payload, or public target access.

## Planned implementation

1. Add a versioned schema under `agents/discovery/mediation.v1.json` for preregistration, estimates, uncertainty, DAG sensitivity, controls, replication, language gate, and trace/resume metadata.
2. Add a sanitized fixture under `tests/fixtures/omics/mediation_fixture.json` containing paired material/intervention, T090 axis scores, outcomes, study IDs, alternative mediator values, and a held-out replication stratum.
3. Implement `src/biointerfaceos/mediation_workflow.py` with deterministic validation, estimand-first calculation, study-clustered bootstrap intervals, alternative-DAG sensitivity, random mediator control, independent replication, and a hard claim-language gate.
4. Expose `biointerfaceos discover mediation --fixture` in the CLI and write a manifest, preregistration, estimate table, sensitivity table, replication receipt, uncertainty report, and lockbox scan under `reports/omics/mediation/`.
5. Add focused tests for paired-row integrity, frozen estimands, cluster-aware uncertainty, alternative mediator/DAG handling, replication isolation, resume determinism, and causal-wording prohibition.
6. Run the focused tests, `UV_OFFLINE=1 make check`, and the complete release/state gate. Record T091 evidence and advance the append-only task ledger only after all gates pass.

## Acceptance criteria

- `MEDIATION_VALID` receipt reports preregistered estimands and explicit study clusters.
- Primary and alternative mediator estimates include uncertainty intervals and sensitivity results.
- Random/permuted mediator control is evaluated and cannot be silently omitted.
- Independent development replication is attempted and its result is kept separate from primary fitting.
- Claim wording is `MEDIATION_PERMITTED` only when all identification gates pass; otherwise it is `ASSOCIATION_ONLY` and mediation wording is rejected.
- Resume output is byte-stable and lockbox scan is clean.
- Full repository checks, immutable release verification, and state validation pass.

## Failure fallback

If any identification or replication gate fails, retain the estimates as descriptive/associational evidence, emit the failed gate and sensitivity bounds, and prohibit causal mediation wording. Do not repair the result by changing splits, selecting a favorable mediator after inspection, or accessing hidden targets.
